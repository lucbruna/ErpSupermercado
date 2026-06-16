from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.models import Filial, Produto, TransferenciaEstoque, TransferenciaItem, MovimentacaoEstoque
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

bp = Blueprint('transferencias', __name__, url_prefix='/estoque/transferencias')

STATUS = {'01': 'Pendente', '02': 'Concluída', '99': 'Cancelada'}


@bp.context_processor
def inject_status():
    return dict(transf_status=STATUS)


def _proximo_numero():
    ultimo = TransferenciaEstoque.query.order_by(TransferenciaEstoque.numero.desc()).first()
    return (ultimo.numero + 1) if ultimo else 1


@bp.route('/')
@login_required
def lista():
    transfs = TransferenciaEstoque.query.order_by(TransferenciaEstoque.numero.desc()).all()
    return render_template('estoque_transferencias_lista.html', transfs=transfs)


@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    filiais = Filial.query.filter_by(ativo=True).order_by(Filial.nome).all()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        origem_id = request.form.get('filial_origem_id', type=int)
        destino_id = request.form.get('filial_destino_id', type=int)
        if not origem_id or not destino_id:
            flash('Selecione origem e destino.', 'warning')
            return render_template('estoque_transferencias_form.html', filiais=filiais, produtos=produtos, hoje=date.today())
        if origem_id == destino_id:
            flash('Origem e destino devem ser diferentes.', 'warning')
            return render_template('estoque_transferencias_form.html', filiais=filiais, produtos=produtos, hoje=date.today())

        t = TransferenciaEstoque(
            numero=_proximo_numero(),
            filial_origem_id=origem_id,
            filial_destino_id=destino_id,
            data_transferencia=datetime.strptime(request.form['data_transferencia'], '%Y-%m-%d').date() if request.form.get('data_transferencia') else date.today(),
            observacao=request.form.get('observacao'),
            usuario_id=current_user.id,
        )
        db.session.add(t)
        db.session.flush()

        produto_ids = request.form.getlist('produto_id')
        quantidades = request.form.getlist('quantidade')
        for pid, qtd in zip(produto_ids, quantidades):
            if pid and qtd:
                q = Decimal(qtd)
                if q <= 0:
                    continue
                ti = TransferenciaItem(transferencia_id=t.id, produto_id=int(pid), quantidade=q)
                db.session.add(ti)

        db.session.commit()
        log_auditoria(f'Nova transferência #{t.numero}', 'TransferenciaEstoque', t.id)
        flash(f'Transferência #{t.numero} criada!', 'success')
        return redirect(url_for('transferencias.lista'))
    return render_template('estoque_transferencias_form.html', filiais=filiais, produtos=produtos, hoje=date.today())


@bp.route('/<int:id>/concluir', methods=['POST'])
@login_required
def concluir(id):
    t = TransferenciaEstoque.query.get_or_404(id)
    if t.status != '01':
        flash('Transferência já concluída ou cancelada.', 'warning')
        return redirect(url_for('transferencias.lista'))

    for item in t.itens.all():
        p = item.produto
        qtd = item.quantidade
        if p.estoque_atual < qtd:
            flash(f'Estoque insuficiente de {p.nome} na origem! Disponível: {p.estoque_atual}', 'danger')
            return redirect(url_for('transferencias.lista'))

    for item in t.itens.all():
        p = item.produto
        qtd = item.quantidade
        p.estoque_atual -= qtd
        mov_saida = MovimentacaoEstoque(
            tipo='S', produto_id=p.id, quantidade=qtd,
            motivo=f'Transferência #{t.numero} para filial {t.filial_destino.nome}',
            documento=f'TRANSF-{t.numero}', usuario_id=current_user.id,
        )
        db.session.add(mov_saida)
        p.estoque_atual += qtd
        mov_entrada = MovimentacaoEstoque(
            tipo='E', produto_id=p.id, quantidade=qtd,
            motivo=f'Transferência #{t.numero} da filial {t.filial_origem.nome}',
            documento=f'TRANSF-{t.numero}', usuario_id=current_user.id,
        )
        db.session.add(mov_entrada)

    t.status = '02'
    db.session.commit()
    log_auditoria(f'Concluiu transferência #{t.numero}', 'TransferenciaEstoque', t.id)
    flash(f'Transferência #{t.numero} concluída!', 'success')
    return redirect(url_for('transferencias.lista'))


@bp.route('/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar(id):
    t = TransferenciaEstoque.query.get_or_404(id)
    if t.status != '01':
        flash('Transferência já concluída ou cancelada.', 'warning')
        return redirect(url_for('transferencias.lista'))
    t.status = '99'
    db.session.commit()
    log_auditoria(f'Cancelou transferência #{t.numero}', 'TransferenciaEstoque', t.id)
    flash('Transferência cancelada.', 'warning')
    return redirect(url_for('transferencias.lista'))


# ── CRUD Filiais ─────────────────────────────────────────────────

@bp.route('/filiais')
@login_required
def lista_filiais():
    filiais = Filial.query.order_by(Filial.nome).all()
    return render_template('estoque_filiais_lista.html', filiais=filiais)


@bp.route('/filiais/novo', methods=['GET', 'POST'])
@login_required
def nova_filial():
    if request.method == 'POST':
        f = Filial(
            nome=request.form['nome'],
            cnpj=request.form.get('cnpj'),
            cep=request.form.get('cep'),
            endereco=request.form.get('endereco'),
            numero=request.form.get('numero'),
            bairro=request.form.get('bairro'),
            cidade=request.form.get('cidade'),
            uf=request.form.get('uf'),
            telefone=request.form.get('telefone'),
            email=request.form.get('email'),
        )
        db.session.add(f)
        db.session.commit()
        log_auditoria(f'Criou filial: {f.nome}', 'Filial', f.id)
        flash('Filial criada!', 'success')
        return redirect(url_for('transferencias.lista_filiais'))
    return render_template('estoque_filiais_form.html', filial=None)