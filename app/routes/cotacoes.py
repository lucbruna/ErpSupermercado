from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.models import Fornecedor, Produto, Cotacao, CotacaoFornecedor, CotacaoItem, CotacaoResposta, CompraPedido, CompraItem, ConfigGeral
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

bp = Blueprint('cotacoes', __name__, url_prefix='/compras/cotacoes')

STATUS = {'01': 'Aberta', '02': 'Enviada', '03': 'Fechada', '99': 'Cancelada'}
STATUS_FORN = {'01': 'Pendente', '02': 'Respondida', '03': 'Não Enviado'}


@bp.context_processor
def inject_status():
    return dict(cotacao_status=STATUS, cotacao_forn_status=STATUS_FORN)


def _proximo_numero():
    ultimo = Cotacao.query.order_by(Cotacao.numero.desc()).first()
    return (ultimo.numero + 1) if ultimo else 1


@bp.route('/')
@login_required
def lista():
    cotacoes = Cotacao.query.order_by(Cotacao.numero.desc()).all()
    return render_template('compras_cotacoes_lista.html', cotacoes=cotacoes)


@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova():
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.nome).all()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        fornecedores_ids = request.form.getlist('fornecedores')
        if not fornecedores_ids:
            flash('Selecione ao menos um fornecedor.', 'warning')
            return render_template('compras_cotacoes_form.html', cotacao=None,
                                   fornecedores=fornecedores, produtos=produtos)
        c = Cotacao(
            numero=_proximo_numero(),
            data_validade=datetime.strptime(request.form['data_validade'], '%Y-%m-%d').date() if request.form.get('data_validade') else None,
            observacao=request.form.get('observacao'),
            usuario_id=current_user.id,
        )
        db.session.add(c)
        db.session.flush()

        for fid in fornecedores_ids:
            cf = CotacaoFornecedor(cotacao_id=c.id, fornecedor_id=int(fid))
            db.session.add(cf)

        produto_ids = request.form.getlist('produto_id')
        quantidades = request.form.getlist('quantidade')
        for pid, qtd in zip(produto_ids, quantidades):
            if pid and qtd:
                ci = CotacaoItem(cotacao_id=c.id, produto_id=int(pid), quantidade=Decimal(qtd))
                db.session.add(ci)

        db.session.commit()
        log_auditoria(f'Nova cotação #{c.numero}', 'Cotacao', c.id)
        flash(f'Cotação #{c.numero} criada!', 'success')
        return redirect(url_for('cotacoes.lista'))
    return render_template('compras_cotacoes_form.html', cotacao=None,
                           fornecedores=fornecedores, produtos=produtos)


@bp.route('/<int:id>')
@login_required
def visualizar(id):
    c = Cotacao.query.get_or_404(id)
    return render_template('compras_cotacoes_view.html', cotacao=c)


@bp.route('/<int:id>/enviar', methods=['POST'])
@login_required
def enviar(id):
    """Envia email para cada fornecedor com os itens da cotação."""
    c = Cotacao.query.get_or_404(id)
    from app.utils.mail import send_email
    from app.models.models import Empresa
    empresa = Empresa.query.first()
    empresa_nome = empresa.nome_fantasia or empresa.razao_social if empresa else 'ERP Supermercado'

    for cf in c.fornecedores.filter(CotacaoFornecedor.status == '01').all():
        if not cf.fornecedor.email:
            cf.status = '03'
            continue
        itens_html = ''.join(
            f'<tr><td>{ci.produto.nome}</td><td>{ci.quantidade}</td><td>{ci.produto.unidade}</td></tr>'
            for ci in c.itens.all()
        )
        html = f'''
        <h2>Cotação #{c.numero}</h2>
        <p>Prezado(a) {cf.fornecedor.nome},</p>
        <p>Solicitamos cotação para os seguintes itens:</p>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
        <tr style="background:#eee"><th>Produto</th><th>Quantidade</th><th>Unidade</th></tr>
        {itens_html}
        </table>
        <p>Prazo para resposta: {c.data_validade.strftime("%d/%m/%Y") if c.data_validade else "a combinar"}</p>
        <hr><small>Enviado por {empresa_nome}</small>'''
        ok, msg = send_email(cf.fornecedor.email, f'Cotação #{c.numero} - {empresa_nome}', html)
        if ok:
            cf.status = '01'
        else:
            flash(f'Falha ao enviar para {cf.fornecedor.nome}: {msg}', 'warning')

    c.status = '02'
    db.session.commit()
    log_auditoria(f'Enviou cotação #{c.numero}', 'Cotacao', c.id)
    flash('Cotações enviadas!', 'success')
    return redirect(url_for('cotacoes.visualizar', id=id))


@bp.route('/<int:id>/responder/<int:cf_id>', methods=['GET', 'POST'])
@login_required
def responder(id, cf_id):
    c = Cotacao.query.get_or_404(id)
    cf = CotacaoFornecedor.query.get_or_404(cf_id)
    if cf.cotacao_id != c.id:
        flash('Fornecedor não pertence a esta cotação.', 'danger')
        return redirect(url_for('cotacoes.visualizar', id=id))

    itens = c.itens.all()
    if request.method == 'POST':
        for item in itens:
            preco = request.form.get(f'preco_{item.id}', type=float)
            if preco is not None:
                resp = CotacaoResposta(
                    cotacao_fornecedor_id=cf.id,
                    cotacao_item_id=item.id,
                    preco_unitario=Decimal(str(preco)),
                    subtotal=Decimal(str(preco)) * item.quantidade,
                )
                db.session.add(resp)
        cf.status = '02'
        if request.form.get('prazo_entrega'):
            cf.prazo_entrega = int(request.form['prazo_entrega'])
        cf.observacao = request.form.get('observacao', '')
        db.session.commit()
        log_auditoria(f'Resposta cotação #{c.numero} - {cf.fornecedor.nome}', 'Cotacao', c.id)
        flash(f'Resposta de {cf.fornecedor.nome} registrada!', 'success')
        return redirect(url_for('cotacoes.visualizar', id=id))

    return render_template('compras_cotacoes_responder.html', cotacao=c, cf=cf, itens=itens)


@bp.route('/<int:id>/fechar', methods=['POST'])
@login_required
def fechar(id):
    """Fecha cotação: escolhe melhor fornecedor e gera pedido de compra."""
    c = Cotacao.query.get_or_404(id)
    melhor_forn = request.form.get('melhor_fornecedor', type=int)
    if not melhor_forn:
        flash('Selecione o fornecedor vencedor.', 'warning')
        return redirect(url_for('cotacoes.visualizar', id=id))

    cf = CotacaoFornecedor.query.get_or_404(melhor_forn)
    if cf.cotacao_id != c.id:
        flash('Fornecedor inválido.', 'danger')
        return redirect(url_for('cotacoes.visualizar', id=id))

    from app.routes.compras import proximo_numero
    pedido = CompraPedido(
        numero=proximo_numero(),
        fornecedor_id=cf.fornecedor_id,
        usuario_id=current_user.id,
        data_prevista=c.data_validade,
        status='04',
        observacao=f'Gerado da Cotação #{c.numero}',
    )
    db.session.add(pedido)
    db.session.flush()

    total_pedido = 0
    itens = c.itens.all()
    for item in itens:
        resp = CotacaoResposta.query.filter_by(
            cotacao_fornecedor_id=cf.id, cotacao_item_id=item.id
        ).first()
        preco = float(resp.preco_unitario) if resp and resp.preco_unitario else float(item.produto.preco_custo or 0)
        qtd = float(item.quantidade)
        subtotal = preco * qtd
        total_pedido += subtotal
        ci = CompraItem(
            pedido_id=pedido.id, produto_id=item.produto_id,
            quantidade=qtd, preco_unitario=preco,
            subtotal=subtotal, total=subtotal,
        )
        db.session.add(ci)

    pedido.subtotal = total_pedido
    pedido.total = total_pedido
    c.status = '03'
    c.compra_pedido_id = pedido.id
    db.session.commit()
    log_auditoria(f'Fechou cotação #{c.numero} -> pedido #{pedido.numero}', 'Cotacao', c.id)
    flash(f'Cotação fechada! Pedido #{pedido.numero} gerado.', 'success')
    return redirect(url_for('compras.visualizar', id=pedido.id))


@bp.route('/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar(id):
    c = Cotacao.query.get_or_404(id)
    c.status = '99'
    db.session.commit()
    log_auditoria(f'Cancelou cotação #{c.numero}', 'Cotacao', c.id)
    flash('Cotação cancelada.', 'warning')
    return redirect(url_for('cotacoes.lista'))