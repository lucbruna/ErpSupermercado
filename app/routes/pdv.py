import unicodedata
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db, modulo_required
from app.models.models import Produto, Cliente, Caixa, Venda, ItemVenda, PagamentoVenda, MovimentacaoEstoque, Sangria
from datetime import datetime, date
from decimal import Decimal
from app.audit import log_auditoria
from app.models.models import BalancaConfig, Promocao, PromocaoItem

bp = Blueprint('pdv', __name__)

@bp.route('/pdv')
@login_required
@modulo_required('PDV')
def index():
    caixa = Caixa.query.filter_by(usuario_id=current_user.id, status='A').first()
    return render_template('pdv.html', caixa=caixa)

@bp.route('/pdv/caixa/abrir', methods=['POST'])
@login_required
@modulo_required('PDV')
def abrir_caixa():
    ja_aberto = Caixa.query.filter_by(usuario_id=current_user.id, status='A').first()
    if ja_aberto:
        flash('Você já tem um caixa aberto!', 'warning')
        return redirect(url_for('pdv.index'))
    valor = Decimal(request.form.get('valor_abertura', '0'))
    ultimo = Caixa.query.order_by(Caixa.id.desc()).first()
    numero = str(int(ultimo.numero) + 1) if ultimo else '1'
    caixa = Caixa(numero=numero, usuario_id=current_user.id, valor_abertura=valor)
    db.session.add(caixa)
    db.session.commit()
    log_auditoria(f'Abriu caixa #{numero}', 'Caixa', caixa.id)
    flash(f'Caixa #{numero} aberto com R$ {valor:.2f}', 'success')
    return redirect(url_for('pdv.index'))

def _buscar_promocao(produto_id, quantidade=1):
    """Retorna preço promocional se houver promoção ativa"""
    from datetime import date
    hoje = date.today()
    item = PromocaoItem.query.join(Promocao).filter(
        PromocaoItem.produto_id == produto_id,
        Promocao.ativo == True,
        Promocao.data_inicio <= hoje,
        Promocao.data_fim >= hoje,
        PromocaoItem.quantidade_minima <= quantidade,
    ).order_by(PromocaoItem.desconto_percentual.desc()).first()
    if item:
        if item.preco_promocional:
            return {'promocao': True, 'preco': float(item.preco_promocional), 'nome': item.promocao.nome}
        if item.desconto_percentual > 0:
            return {'promocao': True, 'preco': None, 'desconto': float(item.desconto_percentual), 'nome': item.promocao.nome}
    return None


@bp.route('/pdv/buscar_produto')
@login_required
@modulo_required('PDV')
def buscar_produto():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify(None)
    q_norm = unicodedata.normalize('NFKD', q).encode('ascii', 'ignore').decode('ascii')
    try:
        p = Produto.query.filter_by(ativo=True).filter(
            (Produto.codigo_barras == q) |
            (Produto.nome.ilike(f'%{q}%')) |
            (func.unaccent(Produto.nome).ilike(f'%{q_norm}%'))
        ).first()
    except Exception:
        db.session.rollback()
        p = Produto.query.filter_by(ativo=True).filter(
            (Produto.codigo_barras == q) |
            (Produto.nome.ilike(f'%{q}%'))
        ).first()
    if p:
        promo = _buscar_promocao(p.id)
        preco_final = float(p.preco_venda)
        promocao_nome = None
        if promo:
            if promo.get('preco'):
                preco_final = promo['preco']
            elif promo.get('desconto'):
                preco_final = preco_final * (1 - promo['desconto'] / 100)
            promocao_nome = promo['nome']

        # Alerta de validade vencida/próxima
        alerta_validade = None
        if p.controla_lote and p.lotes:
            from datetime import date
            hoje = date.today()
            for lote in p.lotes:
                if lote.ativo and lote.quantidade > 0:
                    dias = (lote.data_validade - hoje).days if lote.data_validade else 999
                    if dias < 0:
                        alerta_validade = f'Lote {lote.codigo} VENCIDO em {lote.data_validade.strftime("%d/%m/%Y")}!'
                        break
                    elif dias <= 7:
                        alerta_validade = f'Lote {lote.codigo} vence em {dias} dias ({lote.data_validade.strftime("%d/%m/%Y")})'
                        break

        return jsonify({
            'id': p.id, 'nome': p.nome, 'preco': preco_final,
            'preco_original': float(p.preco_venda),
            'estoque': float(p.estoque_atual), 'unidade': p.unidade,
            'promocao': promocao_nome, 'balanca': p.peso_balanca,
            'alerta_validade': alerta_validade,
        })
    return jsonify(None)

@bp.route('/pdv/sugerir_produtos')
@login_required
@modulo_required('PDV')
def sugerir_produtos():
    q = request.args.get('q', '').strip()
    if len(q) < 1:
        return jsonify([])
    q_norm = unicodedata.normalize('NFKD', q).encode('ascii', 'ignore').decode('ascii')
    try:
        produtos = Produto.query.filter_by(ativo=True).filter(
            (Produto.codigo_barras.ilike(f'{q}%')) |
            (Produto.nome.ilike(f'%{q}%')) |
            (func.unaccent(Produto.nome).ilike(f'%{q_norm}%'))
        ).order_by(Produto.nome).limit(10).all()
    except Exception:
        db.session.rollback()
        produtos = Produto.query.filter_by(ativo=True).filter(
            (Produto.codigo_barras.ilike(f'{q}%')) |
            (Produto.nome.ilike(f'%{q}%'))
        ).order_by(Produto.nome).limit(10).all()
    result = []
    for p in produtos:
        promo = _buscar_promocao(p.id)
        preco_final = float(p.preco_venda)
        promocao_nome = None
        if promo:
            if promo.get('preco'):
                preco_final = promo['preco']
            elif promo.get('desconto'):
                preco_final = preco_final * (1 - promo['desconto'] / 100)
            promocao_nome = promo['nome']
        result.append({
            'id': p.id, 'nome': p.nome, 'preco': preco_final,
            'preco_original': float(p.preco_venda),
            'estoque': float(p.estoque_atual), 'unidade': p.unidade,
            'promocao': promocao_nome, 'balanca': p.peso_balanca,
        })
    return jsonify(result)

@bp.route('/pdv/salvar_venda', methods=['POST'])
@login_required
@modulo_required('PDV')
def salvar_venda():
    caixa = Caixa.query.filter_by(usuario_id=current_user.id, status='A').first()
    if not caixa:
        return jsonify({'erro': 'Nenhum caixa aberto'}), 400
    data = request.get_json()
    itens = data.get('itens', [])
    desconto_total = Decimal(str(data.get('desconto', 0)))
    cliente_id = data.get('cliente_id')
    if not itens:
        return jsonify({'erro': 'Carrinho vazio'}), 400

    ultimo = Venda.query.order_by(Venda.id.desc()).first()
    numero = (ultimo.numero + 1) if ultimo else 1

    subtotal = Decimal('0')
    desconto_itens = Decimal('0')

    for item in itens:
        qtd = Decimal(str(item['quantidade']))
        preco = Decimal(str(item['preco']))
        desc_item = Decimal(str(item.get('desconto_item', 0)))
        subtotal += preco * qtd
        desconto_itens += desc_item

    total = subtotal - desconto_itens - desconto_total

    venda = Venda(
        numero=numero, caixa_id=caixa.id, cliente_id=cliente_id,
        usuario_id=current_user.id, subtotal=subtotal, desconto=desconto_itens + desconto_total, total=total
    )
    db.session.add(venda)
    db.session.flush()

    for item in itens:
        produto = Produto.query.get(item['id'])
        qtd = Decimal(str(item['quantidade']))
        preco = Decimal(str(item['preco']))
        desc_item = Decimal(str(item.get('desconto_item', 0)))
        subtotal_item = qtd * preco
        iv = ItemVenda(
            venda_id=venda.id, produto_id=produto.id,
            quantidade=qtd, preco_unitario=preco,
            subtotal=subtotal_item, desconto=desc_item
        )
        db.session.add(iv)
        produto.estoque_atual -= qtd
        mov = MovimentacaoEstoque(
            tipo='S', produto_id=produto.id, quantidade=qtd,
            preco_unitario=preco, motivo='Venda PDV',
            documento=f'VENDA-{numero}', usuario_id=current_user.id
        )
        db.session.add(mov)

    db.session.commit()
    log_auditoria(f'Venda #{numero} finalizada: R$ {float(total):.2f}', 'Venda', venda.id)
    return jsonify({'ok': True, 'venda_id': venda.id, 'total': float(total), 'numero': numero})

@bp.route('/pdv/pagamento/<int:venda_id>', methods=['POST'])
@login_required
@modulo_required('PDV')
def pagamento(venda_id):
    venda = Venda.query.get_or_404(venda_id)
    data = request.get_json()
    pagamentos = data.get('pagamentos', [])
    pago = Decimal('0')
    for pg in pagamentos:
        valor = Decimal(str(pg['valor']))
        troco = Decimal(str(pg.get('troco', 0)))
        p = PagamentoVenda(
            venda_id=venda.id, forma_pagamento=pg['forma'],
            valor=valor, troco=troco, nsu=pg.get('nsu')
        )
        db.session.add(p)
        pago += valor - troco

    if pago < venda.total:
        flash('Pagamento insuficiente!', 'danger')
        return jsonify({'erro': 'Pagamento insuficiente'}), 400

    venda.status = 'F'
    caixa = venda.caixa
    caixa.valor_esperado = caixa.valor_esperado + venda.total
    db.session.commit()

    # Lançamento contábil automático
    try:
        from app.contabilidade.auto_lancamentos import lancar_venda
        lancar_venda(venda, current_user.id)
    except Exception:
        db.session.rollback()
        pass  # Contabilidade não deve bloquear a venda

    return jsonify({'ok': True, 'troco': float(pago - venda.total)})

@bp.route('/pdv/fechar_caixa', methods=['POST'])
@login_required
@modulo_required('PDV')
def fechar_caixa():
    caixa = Caixa.query.filter_by(usuario_id=current_user.id, status='A').first()
    if not caixa:
        flash('Nenhum caixa aberto!', 'warning')
        return redirect(url_for('pdv.index'))
    valor_fechamento = Decimal(request.form.get('valor_fechamento', '0'))
    caixa.valor_fechamento = valor_fechamento
    caixa.data_fechamento = datetime.now()
    caixa.status = 'F'
    db.session.commit()
    caixa_id = caixa.id
    flash(f'Caixa #{caixa.numero} fechado! Esperado: R$ {caixa.valor_esperado:.2f}', 'success')
    return redirect(url_for('pdv.resumo_caixa', caixa_id=caixa_id))

@bp.route('/pdv/fechar_caixa')
@login_required
@modulo_required('PDV')
def fechar_caixa_page():
    caixa = Caixa.query.filter_by(usuario_id=current_user.id, status='A').first()
    if not caixa:
        flash('Nenhum caixa aberto!', 'warning')
        return redirect(url_for('pdv.index'))
    return render_template('pdv_fechar.html', caixa=caixa)

@bp.route('/pdv/resumo_caixa/<int:caixa_id>')
@login_required
@modulo_required('PDV')
def resumo_caixa(caixa_id):
    caixa = Caixa.query.get_or_404(caixa_id)
    vendas = Venda.query.filter_by(caixa_id=caixa.id, status='F').all()
    total_vendas = sum(float(v.total) for v in vendas)
    pagamentos = {}
    for v in vendas:
        for pg in v.pagamentos:
            pagamentos[pg.forma_pagamento] = pagamentos.get(pg.forma_pagamento, 0) + float(pg.valor) - float(pg.troco)
    sangrias = Sangria.query.filter_by(caixa_id=caixa.id).order_by(Sangria.created_at).all()
    total_sangrias = sum(float(s.valor) for s in sangrias)
    return render_template('pdv_resumo.html', caixa=caixa, vendas=vendas, total_vendas=total_vendas, pagamentos=pagamentos, sangrias=sangrias, total_sangrias=total_sangrias)

@bp.route('/pdv/vendas')
@login_required
@modulo_required('PDV')
def historico_vendas():
    page = request.args.get('page', 1, type=int)
    vendas = Venda.query.order_by(Venda.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('pdv_historico.html', vendas=vendas)

@bp.route('/pdv/venda/<int:venda_id>')
@login_required
@modulo_required('PDV')
def venda_detalhe(venda_id):
    venda = Venda.query.get_or_404(venda_id)
    return render_template('pdv_detalhe.html', venda=venda)

@bp.route('/pdv/cancelar_venda/<int:venda_id>', methods=['POST'])
@login_required
@modulo_required('PDV')
def cancelar_venda(venda_id):
    venda = Venda.query.get_or_404(venda_id)
    if venda.status == 'C':
        flash('Venda já cancelada!', 'warning')
        return redirect(url_for('pdv.historico_vendas'))
    for item in venda.itens:
        produto = Produto.query.get(item.produto_id)
        produto.estoque_atual += item.quantidade
        mov = MovimentacaoEstoque(
            tipo='E', produto_id=produto.id, quantidade=item.quantidade,
            preco_unitario=item.preco_unitario, motivo='Cancelamento Venda',
            documento=f'CANC-VENDA-{venda.numero}', usuario_id=current_user.id
        )
        db.session.add(mov)
    venda.status = 'C'
    db.session.commit()
    log_auditoria(f'Cancelou venda #{venda.numero}', 'Venda', venda.id)
    flash(f'Venda #{venda.numero} cancelada! Estoque devolvido.', 'warning')
    return redirect(url_for('pdv.historico_vendas'))

@bp.route('/pdv/sangria', methods=['POST'])
@login_required
@modulo_required('PDV')
def sangria():
    if current_user.papel not in ('admin', 'chefe_setor'):
        flash('Apenas admin e chefes de setor podem registrar sangria!', 'danger')
        return redirect(url_for('pdv.index'))
    caixa = Caixa.query.filter_by(usuario_id=current_user.id, status='A').first()
    if not caixa:
        flash('Nenhum caixa aberto!', 'danger')
        return redirect(url_for('pdv.index'))
    valor = Decimal(request.form.get('valor', '0'))
    motivo = request.form.get('motivo', '')
    if valor <= 0:
        flash('Valor inválido!', 'danger')
        return redirect(url_for('pdv.index'))
    s = Sangria(caixa_id=caixa.id, usuario_id=current_user.id, valor=valor, motivo=motivo)
    db.session.add(s)
    db.session.commit()
    log_auditoria(f'Sangria R$ {float(valor):.2f} - {motivo}', 'Sangria', s.id)
    flash(f'Sangria de R$ {valor:.2f} registrada por {current_user.nome}', 'warning')
    return redirect(url_for('pdv.index'))

@bp.route('/pdv/sangrias')
@login_required
@modulo_required('PDV')
def lista_sangrias():
    if current_user.papel not in ('admin', 'chefe_setor'):
        flash('Apenas admin e chefes de setor podem visualizar sangrias!', 'danger')
        return redirect(url_for('pdv.index'))
    caixa = Caixa.query.filter_by(usuario_id=current_user.id, status='A').first()
    sangrias = []
    if caixa:
        sangrias = Sangria.query.filter_by(caixa_id=caixa.id).order_by(Sangria.created_at.desc()).all()
    total_sangrias = sum(float(s.valor) for s in sangrias)
    return render_template('pdv_sangrias.html', sangrias=sangrias, total_sangrias=total_sangrias, caixa=caixa)


# ── Balança ─────────────────────────────────────────────────────

@bp.route('/pdv/balanca/config', methods=['GET', 'POST'])
@login_required
@modulo_required('PDV')
def balanca_config():
    cfg = BalancaConfig.query.first()
    if not cfg:
        cfg = BalancaConfig()
        db.session.add(cfg)
        db.session.commit()

    if request.method == 'POST':
        cfg.modelo = request.form.get('modelo', 'toledo')
        cfg.porta = request.form.get('porta', 'COM1')
        cfg.baudrate = int(request.form.get('baudrate', 9600))
        cfg.bytesize = int(request.form.get('bytesize', 8))
        cfg.parity = request.form.get('parity', 'N')
        cfg.stopbits = int(request.form.get('stopbits', 1))
        cfg.timeout = int(request.form.get('timeout', 5))
        cfg.prefixo = request.form.get('prefixo', '')
        cfg.sufixo = request.form.get('sufixo', '')
        cfg.ativo = 'ativo' in request.form
        db.session.commit()
        log_auditoria('Configurou balança', 'BalancaConfig', cfg.id)
        flash('Configuração da balança salva!', 'success')
        return redirect(url_for('pdv.balanca_config'))

    portas_disponiveis = []
    try:
        from app.balanca.driver import BalancaDriver
        portas_disponiveis = BalancaDriver.listar_portas()
    except ImportError:
        pass

    return render_template('pdv_balanca.html', cfg=cfg, portas=portas_disponiveis)


@bp.route('/pdv/balanca/testar', methods=['POST'])
@login_required
@modulo_required('PDV')
def balanca_testar():
    modelo = request.form.get('modelo', 'toledo')
    porta = request.form.get('porta', 'COM1')
    baudrate = int(request.form.get('baudrate', 9600))

    try:
        from app.balanca.driver import BalancaDriver
        resultado = BalancaDriver.testar_conexao(modelo, porta, baudrate)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)})


@bp.route('/pdv/balanca/ler_peso')
@login_required
@modulo_required('PDV')
def balanca_ler_peso():
    cfg = BalancaConfig.query.filter_by(ativo=True).first()
    if not cfg:
        return jsonify({'sucesso': False, 'erro': 'Balança não configurada'})

    try:
        from app.balanca.driver import BalancaDriver
        driver = BalancaDriver({
            'modelo': cfg.modelo,
            'porta': cfg.porta,
            'baudrate': cfg.baudrate,
            'bytesize': cfg.bytesize,
            'parity': cfg.parity,
            'stopbits': cfg.stopbits,
            'timeout': cfg.timeout,
        })
        resultado = driver.ler_peso()
        driver.desconectar()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)})


# ── Promoções ───────────────────────────────────────────────────

@bp.route('/pdv/promocoes')
@login_required
@modulo_required('PDV')
def lista_promocoes():
    promocoes = Promocao.query.order_by(Promocao.created_at.desc()).all()
    return render_template('pdv_promocoes_lista.html', promocoes=promocoes, hoje=date.today())


@bp.route('/pdv/promocoes/novo', methods=['GET', 'POST'])
@login_required
@modulo_required('PDV')
def nova_promocao():
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        if not nome:
            flash('Nome da promoção é obrigatório!', 'danger')
            return render_template('pdv_promocoes_form.html', promocao=None, produtos=produtos)

        data_ini = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        tipo = request.form.get('tipo', 'porcentagem')
        valor = Decimal(request.form.get('valor', '0'))

        promocao = Promocao(
            nome=nome,
            descricao=request.form.get('descricao', ''),
            tipo=tipo,
            valor=valor,
            data_inicio=datetime.strptime(data_ini, '%Y-%m-%d').date() if data_ini else None,
            data_fim=datetime.strptime(data_fim, '%Y-%m-%d').date() if data_fim else None,
        )
        db.session.add(promocao)
        db.session.flush()

        produtos_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade_minima[]')
        precos_promo = request.form.getlist('preco_promocional[]')
        descontos = request.form.getlist('desconto_percentual[]')

        for pid, qtd, preco, desc in zip(produtos_ids, quantidades, precos_promo, descontos):
            if not pid:
                continue
            item = PromocaoItem(
                promocao_id=promocao.id,
                produto_id=int(pid),
                quantidade_minima=Decimal(qtd or '1'),
                preco_promocional=Decimal(preco) if preco else None,
                desconto_percentual=Decimal(desc or '0'),
            )
            db.session.add(item)

        db.session.commit()
        log_auditoria(f'Criou promoção: {nome}', 'Promocao', promocao.id)
        flash(f'Promoção "{nome}" criada!', 'success')
        return redirect(url_for('pdv.lista_promocoes'))

    return render_template('pdv_promocoes_form.html', promocao=None, produtos=produtos)


@bp.route('/pdv/promocoes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@modulo_required('PDV')
def editar_promocao(id):
    p = Promocao.query.get_or_404(id)
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        p.nome = request.form.get('nome', '').strip()
        p.descricao = request.form.get('descricao', '')
        p.tipo = request.form.get('tipo', 'porcentagem')
        p.valor = Decimal(request.form.get('valor', '0'))
        data_ini = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        p.data_inicio = datetime.strptime(data_ini, '%Y-%m-%d').date() if data_ini else None
        p.data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date() if data_fim else None
        p.ativo = 'ativo' in request.form

        PromocaoItem.query.filter_by(promocao_id=p.id).delete()
        db.session.flush()

        produtos_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade_minima[]')
        precos_promo = request.form.getlist('preco_promocional[]')
        descontos = request.form.getlist('desconto_percentual[]')

        for pid, qtd, preco, desc in zip(produtos_ids, quantidades, precos_promo, descontos):
            if not pid:
                continue
            item = PromocaoItem(
                promocao_id=p.id,
                produto_id=int(pid),
                quantidade_minima=Decimal(qtd or '1'),
                preco_promocional=Decimal(preco) if preco else None,
                desconto_percentual=Decimal(desc or '0'),
            )
            db.session.add(item)

        db.session.commit()
        log_auditoria(f'Editou promoção: {p.nome}', 'Promocao', p.id)
        flash(f'Promoção "{p.nome}" atualizada!', 'success')
        return redirect(url_for('pdv.lista_promocoes'))

    return render_template('pdv_promocoes_form.html', promocao=p, produtos=produtos)


@bp.route('/pdv/promocoes/buscar_produto')
@login_required
@modulo_required('PDV')
def buscar_preco_promocional():
    produto_id = request.args.get('produto_id', type=int)
    quantidade = Decimal(request.args.get('quantidade', '1'))
    if not produto_id:
        return jsonify({'promocao': False})

    from datetime import date
    hoje = date.today()
    item = PromocaoItem.query.join(Promocao).filter(
        PromocaoItem.produto_id == produto_id,
        Promocao.ativo == True,
        Promocao.data_inicio <= hoje,
        Promocao.data_fim >= hoje,
        PromocaoItem.quantidade_minima <= quantidade,
    ).order_by(PromocaoItem.desconto_percentual.desc()).first()

    if item:
        if item.preco_promocional:
            return jsonify({'promocao': True, 'preco': float(item.preco_promocional), 'tipo': 'valor', 'promocao_nome': item.promocao.nome})
        if item.desconto_percentual > 0:
            prod = Produto.query.get(produto_id)
            preco_original = float(prod.preco_venda) if prod else 0
            preco_final = preco_original * (1 - float(item.desconto_percentual) / 100)
            return jsonify({'promocao': True, 'preco': round(preco_final, 2), 'tipo': 'percentual', 'desconto': float(item.desconto_percentual), 'promocao_nome': item.promocao.nome})

    return jsonify({'promocao': False})
