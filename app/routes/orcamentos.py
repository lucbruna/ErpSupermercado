from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.models import Orcamento, OrcamentoItem, Cliente, Produto, Venda, ItemVenda, MovimentacaoEstoque, Caixa
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

bp = Blueprint('orcamentos', __name__, url_prefix='/orcamentos')

STATUS_ORC = {'01': 'Rascunho', '02': 'Aprovado', '03': 'Convertido', '99': 'Cancelado'}


@bp.context_processor
def inject_status():
    return dict(orc_status=STATUS_ORC)


def proximo_numero():
    ultimo = Orcamento.query.order_by(Orcamento.numero.desc()).first()
    return (ultimo.numero + 1) if ultimo else 1


@bp.route('/')
@login_required
def lista():
    orcamentos = Orcamento.query.order_by(Orcamento.created_at.desc()).all()
    return render_template('orcamentos_lista.html', orcamentos=orcamentos)


@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id') or None
        data_validade = request.form.get('data_validade')
        observacao = request.form.get('observacao')
        orc = Orcamento(
            numero=proximo_numero(),
            cliente_id=cliente_id, usuario_id=current_user.id,
            data_validade=datetime.strptime(data_validade, '%Y-%m-%d').date() if data_validade else None,
            observacao=observacao, status='01'
        )
        db.session.add(orc)
        db.session.flush()
        produtos_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade[]')
        precos = request.form.getlist('preco[]')
        subtotal_orc = Decimal('0')
        for pid, qtd, preco in zip(produtos_ids, quantidades, precos):
            if not pid:
                continue
            q = Decimal(qtd or '1')
            p = Decimal(preco or '0')
            st = q * p
            item = OrcamentoItem(
                orcamento_id=orc.id, produto_id=int(pid),
                quantidade=q, preco_unitario=p,
                subtotal=st, desconto=Decimal('0'), total=st
            )
            db.session.add(item)
            subtotal_orc += st
        orc.subtotal = subtotal_orc
        orc.total = subtotal_orc
        db.session.commit()
        log_auditoria(f'Criou orçamento #{orc.numero}', 'Orcamento', orc.id)
        flash(f'Orçamento #{orc.numero} criado!', 'success')
        return redirect(url_for('orcamentos.lista'))
    produtos_json = [{'id': p.id, 'nome': p.nome, 'preco': float(p.preco_venda)} for p in produtos]
    return render_template('orcamentos_form.html', orc=None, clientes=clientes, produtos=produtos, produtos_json=produtos_json)


@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    orc = Orcamento.query.get_or_404(id)
    if orc.status not in ('01',):
        flash('Orçamento não pode ser alterado!', 'danger')
        return redirect(url_for('orcamentos.lista'))
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        orc.cliente_id = request.form.get('cliente_id') or None
        orc.data_validade = datetime.strptime(request.form.get('data_validade'), '%Y-%m-%d').date() if request.form.get('data_validade') else None
        orc.observacao = request.form.get('observacao')
        OrcamentoItem.query.filter_by(orcamento_id=orc.id).delete()
        db.session.flush()
        produtos_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade[]')
        precos = request.form.getlist('preco[]')
        subtotal_orc = Decimal('0')
        for pid, qtd, preco in zip(produtos_ids, quantidades, precos):
            if not pid:
                continue
            q = Decimal(qtd or '1')
            p = Decimal(preco or '0')
            st = q * p
            item = OrcamentoItem(
                orcamento_id=orc.id, produto_id=int(pid),
                quantidade=q, preco_unitario=p,
                subtotal=st, desconto=Decimal('0'), total=st
            )
            db.session.add(item)
            subtotal_orc += st
        orc.subtotal = subtotal_orc
        orc.total = subtotal_orc
        db.session.commit()
        log_auditoria(f'Editou orçamento #{orc.numero}', 'Orcamento', orc.id)
        flash(f'Orçamento #{orc.numero} atualizado!', 'success')
        return redirect(url_for('orcamentos.lista'))
    produtos_json = [{'id': p.id, 'nome': p.nome, 'preco': float(p.preco_venda)} for p in produtos]
    return render_template('orcamentos_form.html', orc=orc, clientes=clientes, produtos=produtos, produtos_json=produtos_json)


@bp.route('/visualizar/<int:id>')
@login_required
def visualizar(id):
    orc = Orcamento.query.get_or_404(id)
    return render_template('orcamentos_view.html', orc=orc)


@bp.route('/aprovar/<int:id>')
@login_required
def aprovar(id):
    orc = Orcamento.query.get_or_404(id)
    if orc.status == '01':
        orc.status = '02'
        db.session.commit()
        log_auditoria(f'Aprovou orçamento #{orc.numero}', 'Orcamento', orc.id)
        flash(f'Orçamento #{orc.numero} aprovado!', 'success')
    return redirect(url_for('orcamentos.visualizar', id=id))


@bp.route('/cancelar/<int:id>')
@login_required
def cancelar(id):
    orc = Orcamento.query.get_or_404(id)
    if orc.status in ('01', '02'):
        orc.status = '99'
        db.session.commit()
        log_auditoria(f'Cancelou orçamento #{orc.numero}', 'Orcamento', orc.id)
        flash(f'Orçamento #{orc.numero} cancelado!', 'warning')
    return redirect(url_for('orcamentos.visualizar', id=id))


@bp.route('/converter_venda/<int:id>')
@login_required
def converter_venda(id):
    orc = Orcamento.query.get_or_404(id)
    if orc.status != '02':
        flash('Apenas orçamentos aprovados podem ser convertidos!', 'danger')
        return redirect(url_for('orcamentos.visualizar', id=id))

    if orc.venda_id:
        flash('Orçamento já convertido em venda!', 'warning')
        return redirect(url_for('orcamentos.visualizar', id=id))

    caixa = Caixa.query.filter_by(usuario_id=current_user.id, status='A').first()
    if not caixa:
        flash('Você precisa abrir um caixa no PDV para converter!', 'danger')
        return redirect(url_for('pdv.index'))

    ultimo = Venda.query.order_by(Venda.id.desc()).first()
    numero = (ultimo.numero + 1) if ultimo else 1

    venda = Venda(
        numero=numero, caixa_id=caixa.id,
        cliente_id=orc.cliente_id, usuario_id=current_user.id,
        subtotal=orc.subtotal, desconto=orc.desconto, total=orc.total,
        status='F'
    )
    db.session.add(venda)
    db.session.flush()

    for item in orc.itens:
        iv = ItemVenda(
            venda_id=venda.id, produto_id=item.produto_id,
            quantidade=item.quantidade, preco_unitario=item.preco_unitario,
            subtotal=item.subtotal, desconto=item.desconto
        )
        db.session.add(iv)
        produto = Produto.query.get(item.produto_id)
        produto.estoque_atual -= item.quantidade
        mov = MovimentacaoEstoque(
            tipo='S', produto_id=item.produto_id, quantidade=item.quantidade,
            preco_unitario=item.preco_unitario, motivo=f'Orçamento #{orc.numero} convertido',
            documento=f'ORC-{orc.numero}', usuario_id=current_user.id
        )
        db.session.add(mov)

    orc.status = '03'
    orc.venda_id = venda.id
    db.session.commit()
    log_auditoria(f'Converteu orçamento #{orc.numero} em venda #{numero}', 'Orcamento', orc.id)
    flash(f'Orçamento #{orc.numero} convertido na venda #{numero}!', 'success')
    return redirect(url_for('pdv.venda_detalhe', venda_id=venda.id))
