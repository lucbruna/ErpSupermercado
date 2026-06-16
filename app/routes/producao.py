from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import OrdemProducao, OrdemProducaoItem, Produto
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

STATUS = {'01': 'Aberta', '02': 'Produzindo', '03': 'Concluída', '99': 'Cancelada'}

bp = Blueprint('producao', __name__, url_prefix='/estoque/producao')


@bp.route('/')
@login_required
def lista():
    ordens = OrdemProducao.query.order_by(OrdemProducao.id.desc()).all()
    return render_template('producao_lista.html', ordens=ordens, status=STATUS)


@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    if request.method == 'POST':
        numero = OrdemProducao.query.count() + 1
        ordem = OrdemProducao(
            numero=numero,
            setor=request.form['setor'],
            data_producao=datetime.strptime(request.form['data_producao'], '%Y-%m-%d').date(),
            status='01',
            observacao=request.form.get('observacao'),
            usuario_id=current_user.id,
        )
        db.session.add(ordem)
        db.session.flush()

        produtos_ids = request.form.getlist('produto_id')
        quantidades = request.form.getlist('quantidade_prevista')
        for pid, qtd in zip(produtos_ids, quantidades):
            if pid and qtd:
                item = OrdemProducaoItem(
                    ordem_id=ordem.id,
                    produto_id=int(pid),
                    quantidade_prevista=Decimal(qtd),
                )
                db.session.add(item)

        db.session.commit()
        log_auditoria(f'Criou ordem de produção #{ordem.numero}', 'OrdemProducao', ordem.id)
        flash(f'Ordem #{ordem.numero} criada!', 'success')
        return redirect(url_for('producao.lista'))

    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    return render_template('producao_form.html', ordem=None, produtos=produtos)


@bp.route('/<int:id>')
@login_required
def view(id):
    ordem = OrdemProducao.query.get_or_404(id)
    return render_template('producao_view.html', ordem=ordem, status=STATUS)


@bp.route('/<int:id>/iniciar', methods=['POST'])
@login_required
def iniciar(id):
    ordem = OrdemProducao.query.get_or_404(id)
    ordem.status = '02'
    db.session.commit()
    log_auditoria(f'Iniciou produção #{ordem.numero}', 'OrdemProducao', ordem.id)
    flash('Produção iniciada!', 'success')
    return redirect(url_for('producao.view', id=ordem.id))


@bp.route('/<int:id>/concluir', methods=['POST'])
@login_required
def concluir(id):
    ordem = OrdemProducao.query.get_or_404(id)
    ordem.status = '03'
    for item in ordem.itens:
        qtd = request.form.get(f'qtd_produzida_{item.id}')
        if qtd:
            item.quantidade_produzida = Decimal(qtd)
    db.session.commit()
    log_auditoria(f'Concluiu produção #{ordem.numero}', 'OrdemProducao', ordem.id)
    flash('Produção concluída!', 'success')
    return redirect(url_for('producao.view', id=ordem.id))


@bp.route('/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar(id):
    ordem = OrdemProducao.query.get_or_404(id)
    ordem.status = '99'
    db.session.commit()
    log_auditoria(f'Cancelou ordem #{ordem.numero}', 'OrdemProducao', ordem.id)
    flash('Ordem cancelada!', 'success')
    return redirect(url_for('producao.lista'))
