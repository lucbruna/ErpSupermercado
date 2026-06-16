from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import Mesa, ComandaItem, Produto, Venda, ItemVenda, Usuario
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

STATUS_MESA = {'01': 'Livre', '02': 'Ocupada', '03': 'Reservada'}
STATUS_COMANDA = {'01': 'Pendente', '02': 'Entregue', '99': 'Cancelado'}

bp = Blueprint('mesas', __name__, url_prefix='/pdv/mesas')


@bp.route('/')
@login_required
def lista():
    mesas = Mesa.query.order_by(Mesa.numero).all()
    return render_template('pdv_mesas_lista.html', mesas=mesas, status=STATUS_MESA)


@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    if request.method == 'POST':
        mesa = Mesa(
            numero=int(request.form['numero']),
            descricao=request.form.get('descricao'),
            capacidade=int(request.form.get('capacidade', 4)),
            status='01',
        )
        db.session.add(mesa)
        db.session.commit()
        log_auditoria(f'Criou mesa #{mesa.numero}', 'Mesa', mesa.id)
        flash(f'Mesa #{mesa.numero} criada!', 'success')
        return redirect(url_for('mesas.lista'))
    return render_template('pdv_mesas_form.html', mesa=None)


@bp.route('/<int:id>')
@login_required
def view(id):
    mesa = Mesa.query.get_or_404(id)
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    total = sum(float(i.preco * i.quantidade) for i in mesa.comanda_itens if i.status != '99')
    return render_template('pdv_mesas_view.html', mesa=mesa, status_mesa=STATUS_MESA,
                           status_comanda=STATUS_COMANDA, total=total, produtos=produtos)


@bp.route('/<int:id>/abrir', methods=['POST'])
@login_required
def abrir(id):
    mesa = Mesa.query.get_or_404(id)
    if mesa.status != '01':
        flash('Mesa não está livre!', 'warning')
        return redirect(url_for('mesas.view', id=mesa.id))

    ultima_venda = Venda.query.order_by(Venda.id.desc()).first()
    numero_venda = str(int(ultima_venda.numero) + 1) if ultima_venda else '1'

    venda = Venda(
        numero=numero_venda,
        caixa_id=1,
        usuario_id=current_user.id,
        subtotal=0,
        total=0,
        status='A',
    )
    db.session.add(venda)
    db.session.flush()

    mesa.status = '02'
    mesa.venda_id = venda.id
    db.session.commit()
    log_auditoria(f'Abriu mesa #{mesa.numero}', 'Mesa', mesa.id)
    flash(f'Mesa #{mesa.numero} aberta!', 'success')
    return redirect(url_for('mesas.view', id=mesa.id))


@bp.route('/<int:id>/adicionar', methods=['POST'])
@login_required
def adicionar(id):
    mesa = Mesa.query.get_or_404(id)
    produto_id = int(request.form['produto_id'])
    quantidade = Decimal(request.form['quantidade'])

    produto = Produto.query.get_or_404(produto_id)
    item = ComandaItem(
        mesa_id=mesa.id,
        produto_id=produto.id,
        quantidade=quantidade,
        preco=produto.preco_venda,
        usuario_id=current_user.id,
    )
    db.session.add(item)
    db.session.commit()
    log_auditoria(f'Adicionou {produto.nome} à mesa #{mesa.numero}', 'ComandaItem', item.id)
    flash('Item adicionado!', 'success')
    return redirect(url_for('mesas.view', id=mesa.id))


@bp.route('/<int:id>/entregar/<int:item_id>', methods=['POST'])
@login_required
def entregar(id, item_id):
    item = ComandaItem.query.get_or_404(item_id)
    item.status = '02'
    db.session.commit()
    log_auditoria(f'Entregou item #{item.id} da mesa #{id}', 'ComandaItem', item.id)
    flash('Item entregue!', 'success')
    return redirect(url_for('mesas.view', id=id))


@bp.route('/<int:id>/fechar', methods=['POST'])
@login_required
def fechar(id):
    mesa = Mesa.query.get_or_404(id)
    if not mesa.venda_id:
        flash('Mesa sem venda vinculada!', 'warning')
        return redirect(url_for('mesas.view', id=mesa.id))

    itens_abertos = ComandaItem.query.filter_by(mesa_id=mesa.id).filter(ComandaItem.status != '99').all()
    for ci in itens_abertos:
        iv = ItemVenda(
            venda_id=mesa.venda_id,
            produto_id=ci.produto_id,
            quantidade=ci.quantidade,
            preco_unitario=ci.preco,
            subtotal=ci.preco * ci.quantidade,
        )
        db.session.add(iv)

    venda = Venda.query.get(mesa.venda_id)
    total = sum(float(i.preco * i.quantidade) for i in itens_abertos)
    venda.subtotal = total
    venda.total = total
    venda.status = 'F'
    mesa.status = '01'
    mesa.venda_id = None
    db.session.commit()
    log_auditoria(f'Fechou mesa #{mesa.numero}', 'Mesa', mesa.id)
    flash('Mesa fechada! Finalize o pagamento.', 'success')
    return redirect(url_for('pdv.index'))


@bp.route('/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar(id):
    mesa = Mesa.query.get_or_404(id)
    itens = ComandaItem.query.filter_by(mesa_id=mesa.id).all()
    for i in itens:
        i.status = '99'
    mesa.status = '01'
    if mesa.venda_id:
        venda = Venda.query.get(mesa.venda_id)
        if venda:
            venda.status = 'C'
        mesa.venda_id = None
    db.session.commit()
    log_auditoria(f'Cancelou mesa #{mesa.numero}', 'Mesa', mesa.id)
    flash('Mesa cancelada!', 'success')
    return redirect(url_for('mesas.lista'))
