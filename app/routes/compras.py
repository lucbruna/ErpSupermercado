from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import CompraPedido, CompraItem, Produto, Fornecedor
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

bp = Blueprint('compras', __name__)

STATUS = {'01': 'Rascunho', '02': 'Cotação', '03': 'Enviado', '04': 'Confirmado', '05': 'Recebido', '99': 'Cancelado'}

@bp.context_processor
def inject_status():
    return dict(compra_status=STATUS)

def proximo_numero():
    ultimo = CompraPedido.query.order_by(CompraPedido.numero.desc()).first()
    return (ultimo.numero + 1) if ultimo else 1

@bp.route('/compras')
@login_required
def lista():
    pedidos = CompraPedido.query.order_by(CompraPedido.numero.desc()).all()
    return render_template('compras_lista.html', pedidos=pedidos)

@bp.route('/compras/novo', methods=['GET', 'POST'])
@login_required
def novo():
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.nome).all()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        fornecedor_id = request.form.get('fornecedor_id')
        data_prevista = request.form.get('data_prevista')
        observacao = request.form.get('observacao')
        pedido = CompraPedido(
            numero=proximo_numero(),
            fornecedor_id=fornecedor_id,
            usuario_id=current_user.id,
            data_prevista=datetime.strptime(data_prevista, '%Y-%m-%d').date() if data_prevista else None,
            observacao=observacao,
            status='01'
        )
        db.session.add(pedido)
        db.session.flush()
        produtos_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade[]')
        precos = request.form.getlist('preco[]')
        subtotal_pedido = Decimal('0')
        for pid, qtd, preco in zip(produtos_ids, quantidades, precos):
            if not pid:
                continue
            q = Decimal(qtd or '1')
            p = Decimal(preco or '0')
            st = q * p
            item = CompraItem(
                pedido_id=pedido.id, produto_id=int(pid),
                quantidade=q, preco_unitario=p,
                subtotal=st, desconto=Decimal('0'), total=st
            )
            db.session.add(item)
            subtotal_pedido += st
        pedido.subtotal = subtotal_pedido
        pedido.total = subtotal_pedido
        db.session.commit()
        log_auditoria(f'Criou pedido de compra #{pedido.numero}', 'CompraPedido', pedido.id)
        flash(f'Pedido #{pedido.numero} criado!', 'success')
        return redirect(url_for('compras.lista'))
    produtos_json = [{'id': p.id, 'nome': p.nome} for p in produtos]
    return render_template('compras_form.html', pedido=None, fornecedores=fornecedores, produtos=produtos, produtos_json=produtos_json)

@bp.route('/compras/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    pedido = CompraPedido.query.get_or_404(id)
    if pedido.status not in ('01', '02'):
        flash('Pedido não pode ser alterado!', 'danger')
        return redirect(url_for('compras.lista'))
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.nome).all()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        pedido.fornecedor_id = request.form.get('fornecedor_id')
        pedido.data_prevista = datetime.strptime(request.form.get('data_prevista'), '%Y-%m-%d').date() if request.form.get('data_prevista') else None
        pedido.observacao = request.form.get('observacao')
        CompraItem.query.filter_by(pedido_id=pedido.id).delete()
        db.session.flush()
        produtos_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade[]')
        precos = request.form.getlist('preco[]')
        subtotal_pedido = Decimal('0')
        for pid, qtd, preco in zip(produtos_ids, quantidades, precos):
            if not pid:
                continue
            q = Decimal(qtd or '1')
            p = Decimal(preco or '0')
            st = q * p
            item = CompraItem(
                pedido_id=pedido.id, produto_id=int(pid),
                quantidade=q, preco_unitario=p,
                subtotal=st, desconto=Decimal('0'), total=st
            )
            db.session.add(item)
            subtotal_pedido += st
        pedido.subtotal = subtotal_pedido
        pedido.total = subtotal_pedido
        db.session.commit()
        log_auditoria(f'Editou pedido de compra #{pedido.numero}', 'CompraPedido', pedido.id)
        flash(f'Pedido #{pedido.numero} atualizado!', 'success')
        return redirect(url_for('compras.lista'))
    produtos_json = [{'id': p.id, 'nome': p.nome} for p in produtos]
    return render_template('compras_form.html', pedido=pedido, fornecedores=fornecedores, produtos=produtos, produtos_json=produtos_json)

@bp.route('/compras/visualizar/<int:id>')
@login_required
def visualizar(id):
    pedido = CompraPedido.query.get_or_404(id)
    return render_template('compras_view.html', pedido=pedido, status_map=STATUS)

@bp.route('/compras/confirmar/<int:id>')
@login_required
def confirmar(id):
    pedido = CompraPedido.query.get_or_404(id)
    if pedido.status in ('01', '02', '03'):
        pedido.status = '04'
        db.session.commit()
        log_auditoria(f'Confirmou pedido #{pedido.numero}', 'CompraPedido', pedido.id)
        flash(f'Pedido #{pedido.numero} confirmado!', 'success')
    return redirect(url_for('compras.visualizar', id=id))

@bp.route('/compras/cancelar/<int:id>')
@login_required
def cancelar(id):
    pedido = CompraPedido.query.get_or_404(id)
    if pedido.status not in ('05', '99'):
        pedido.status = '99'
        db.session.commit()
        log_auditoria(f'Cancelou pedido #{pedido.numero}', 'CompraPedido', pedido.id)
        flash(f'Pedido #{pedido.numero} cancelado!', 'warning')
    return redirect(url_for('compras.visualizar', id=id))

@bp.route('/compras/receber/<int:id>')
@login_required
def receber(id):
    pedido = CompraPedido.query.get_or_404(id)
    if pedido.status != '04':
        flash('Apenas pedidos confirmados podem ser recebidos!', 'danger')
        return redirect(url_for('compras.visualizar', id=id))
    from app.models.models import MovimentacaoEstoque
    pedido.status = '05'
    pedido.data_recebimento = date.today()
    for item in pedido.itens:
        mov = MovimentacaoEstoque(
            tipo='E', produto_id=item.produto_id,
            quantidade=item.quantidade, preco_unitario=item.preco_unitario,
            fornecedor_id=pedido.fornecedor_id, motivo=f'Recebimento Pedido #{pedido.numero}',
            documento=f'PC-{pedido.numero}', usuario_id=current_user.id
        )
        db.session.add(mov)
        item.produto.estoque_atual = item.produto.estoque_atual + item.quantidade
    db.session.commit()
    log_auditoria(f'Recebeu pedido #{pedido.numero}', 'CompraPedido', pedido.id)
    flash(f'Pedido #{pedido.numero} recebido! Estoque atualizado.', 'success')
    return redirect(url_for('compras.visualizar', id=id))
