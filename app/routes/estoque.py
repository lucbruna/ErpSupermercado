from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db, modulo_required
from app.models.models import Produto, Fornecedor, Lote, MovimentacaoEstoque
from datetime import datetime, date, timedelta
from decimal import Decimal
from app.audit import log_auditoria

bp = Blueprint('estoque', __name__)

@bp.route('/estoque')
@login_required
@modulo_required('Estoque')
def movimentacoes():
    movs = MovimentacaoEstoque.query.order_by(MovimentacaoEstoque.created_at.desc()).all()
    return render_template('estoque_lista.html', movimentacoes=movs)

@bp.route('/estoque/entrada', methods=['GET', 'POST'])
@login_required
@modulo_required('Estoque')
def entrada():
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.nome).all()
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        quantidade = float(request.form['quantidade'])
        preco_unitario = float(request.form.get('preco_unitario', 0))
        fornecedor_id = request.form.get('fornecedor_id') or None
        documento = request.form.get('documento')
        motivo = request.form.get('motivo')
        lote_codigo = request.form.get('lote_codigo')
        data_validade = request.form.get('data_validade')

        produto = Produto.query.get_or_404(produto_id)

        lote = None
        if lote_codigo and produto.controla_lote:
            lote = Lote(
                produto_id=produto_id,
                codigo=lote_codigo,
                quantidade=Decimal(str(quantidade)),
                data_validade=datetime.strptime(data_validade, '%Y-%m-%d').date() if data_validade else None,
                preco_custo=Decimal(str(preco_unitario)),
            )
            db.session.add(lote)
            db.session.flush()

        mov = MovimentacaoEstoque(
            tipo='E',
            produto_id=produto_id,
            lote_id=lote.id if lote else None,
            fornecedor_id=fornecedor_id,
            quantidade=Decimal(str(quantidade)),
            preco_unitario=Decimal(str(preco_unitario)),
            motivo=motivo,
            documento=documento,
            usuario_id=current_user.id,
        )
        db.session.add(mov)

        produto.estoque_atual = produto.estoque_atual + Decimal(str(quantidade))
        if preco_unitario > 0:
            produto.preco_custo = Decimal(str(preco_unitario))

        db.session.commit()
        log_auditoria(f'Entrada estoque: {quantidade}x {produto.nome}', 'Estoque', produto.id)
        flash(f'Entrada registrada: {quantidade}x {produto.nome}', 'success')
        return redirect(url_for('estoque.movimentacoes'))
    return render_template('estoque_entrada.html', produtos=produtos, fornecedores=fornecedores)

@bp.route('/estoque/saida', methods=['GET', 'POST'])
@login_required
@modulo_required('Estoque')
def saida():
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        quantidade = float(request.form['quantidade'])
        motivo = request.form.get('motivo')
        documento = request.form.get('documento')

        produto = Produto.query.get_or_404(produto_id)
        qtd = Decimal(str(quantidade))
        if produto.estoque_atual < qtd:
            flash(f'Estoque insuficiente! Disponivel: {produto.estoque_atual}', 'danger')
            return redirect(url_for('estoque.saida'))

        mov = MovimentacaoEstoque(
            tipo='S',
            produto_id=produto_id,
            quantidade=qtd,
            motivo=motivo,
            documento=documento,
            usuario_id=current_user.id,
        )
        db.session.add(mov)
        produto.estoque_atual = produto.estoque_atual - qtd
        db.session.commit()
        log_auditoria(f'Saída estoque: {quantidade}x {produto.nome}', 'Estoque', produto.id)
        flash(f'Saída registrada: {quantidade}x {produto.nome}', 'warning')
        return redirect(url_for('estoque.movimentacoes'))
    return render_template('estoque_saida.html', produtos=produtos)

@bp.route('/estoque/saldo')
@login_required
@modulo_required('Estoque')
def saldo():
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    return render_template('estoque_saldo.html', produtos=produtos)


# ── Kardex / Ficha de Estoque ────────────────────────────────────

@bp.route('/estoque/kardex')
@login_required
@modulo_required('Estoque')
def kardex():
    produto_id = request.args.get('produto_id', type=int)
    data_ini = request.args.get('data_ini')
    data_fim = request.args.get('data_fim')
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()

    movs = []
    produto = None
    saldo_inicial = 0

    if produto_id:
        produto = Produto.query.get_or_404(produto_id)
        q = MovimentacaoEstoque.query.filter_by(produto_id=produto_id)
        if data_ini:
            q = q.filter(MovimentacaoEstoque.created_at >= datetime.strptime(data_ini, '%Y-%m-%d'))
        if data_fim:
            q = q.filter(MovimentacaoEstoque.created_at <= datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1))
        movs = q.order_by(MovimentacaoEstoque.created_at, MovimentacaoEstoque.id).all()

        # Calcular saldo antes do período filtrado
        q_antes = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.produto_id == produto_id,
            MovimentacaoEstoque.created_at < (movs[0].created_at if movs else datetime.now())
        )
        if data_ini:
            q_antes = q_antes.filter(MovimentacaoEstoque.created_at < datetime.strptime(data_ini, '%Y-%m-%d'))
        total_antes = 0
        for m in q_antes.all():
            if m.tipo == 'E':
                total_antes += float(m.quantidade)
            elif m.tipo in ('S',):
                total_antes -= float(m.quantidade)
            elif m.tipo == 'A':
                total_antes += float(m.quantidade)
        saldo_inicial = total_antes

    # Calcular saldo acumulado para exibição
    linhas = []
    saldo_corrente = saldo_inicial
    for m in movs:
        qtd = float(m.quantidade)
        if m.tipo == 'E':
            delta = qtd
        elif m.tipo == 'S':
            delta = -qtd
        elif m.tipo == 'A':
            delta = qtd
        else:
            delta = 0
        saldo_anterior = saldo_corrente
        saldo_corrente += delta
        linhas.append({
            'mov': m,
            'delta': delta,
            'saldo_anterior': saldo_anterior,
            'saldo_atual': saldo_corrente,
        })

    return render_template('estoque_kardex.html', produtos=produtos, produto=produto,
                           linhas=linhas, saldo_inicial=saldo_inicial,
                           data_ini=data_ini, data_fim=data_fim)

@bp.route('/estoque/lotes')
@login_required
@modulo_required('Estoque')
def lotes():
    lotes = Lote.query.filter_by(ativo=True).order_by(Lote.data_validade).all()
    hoje = date.today()
    proximo_mes = hoje + timedelta(days=30)
    return render_template('estoque_lotes.html', lotes=lotes, hoje=hoje, proximo_mes=proximo_mes)


# ── Curva ABC ───────────────────────────────────────────────────

@bp.route('/estoque/curva_abc')
@login_required
@modulo_required('Estoque')
def curva_abc():
    from sqlalchemy import func
    from app.models.models import ItemVenda, Venda

    trinta_dias = date.today() - timedelta(days=30)
    vendas = db.session.query(
        ItemVenda.produto_id,
        func.sum(ItemVenda.quantidade).label('qtd'),
        func.sum(ItemVenda.subtotal).label('total')
    ).join(Venda, ItemVenda.venda_id == Venda.id
    ).filter(Venda.created_at >= trinta_dias, Venda.status == 'F'
    ).group_by(ItemVenda.produto_id).order_by(func.sum(ItemVenda.subtotal).desc()).all()

    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    prod_venda = {v.produto_id: {'qtd': float(v.qtd), 'total': float(v.total)} for v in vendas}

    vendas_ordenadas = sorted(prod_venda.items(), key=lambda x: x[1]['total'], reverse=True)
    total_geral = sum(v['total'] for _, v in vendas_ordenadas)

    acumulado = 0
    classificacao = []
    for pid, dados in vendas_ordenadas:
        acumulado += dados['total']
        pct = (dados['total'] / total_geral * 100) if total_geral > 0 else 0
        pct_acum = (acumulado / total_geral * 100) if total_geral > 0 else 0
        if pct_acum <= 50:
            classe = 'A'
        elif pct_acum <= 80:
            classe = 'B'
        else:
            classe = 'C'
        p = Produto.query.get(pid)
        if p:
            dados['produto'] = p
            dados['pct'] = pct
            dados['pct_acum'] = pct_acum
            dados['classe'] = classe
            classificacao.append(dados)

    for p in produtos:
        if p.id not in prod_venda:
            classificacao.append({
                'produto': p,
                'qtd': 0,
                'total': 0,
                'pct': 0,
                'pct_acum': 100,
                'classe': 'C',
            })

    return render_template('estoque_curva_abc.html', classificacao=classificacao, total_geral=total_geral)


# ── Inventário Físico ──────────────────────────────────────────

@bp.route('/estoque/inventario', methods=['GET', 'POST'])
@login_required
@modulo_required('Estoque')
def inventario():
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        divergencias = []
        for p in produtos:
            campo = f'qtd_{p.id}'
            if campo in request.form:
                qtd_real = Decimal(str(request.form[campo]))
                diferenca = qtd_real - p.estoque_atual
                if diferenca != 0:
                    motivo = request.form.get(f'motivo_{p.id}', 'Ajuste inventário')
                    mov = MovimentacaoEstoque(
                        tipo='A',
                        produto_id=p.id,
                        quantidade=diferenca,
                        preco_unitario=p.preco_custo,
                        motivo=f'Inventário: {motivo}',
                        usuario_id=current_user.id,
                    )
                    db.session.add(mov)
                    p.estoque_atual = qtd_real
                    divergencias.append({
                        'produto': p.nome,
                        'sistema': float(p.estoque_atual - diferenca),
                        'real': float(qtd_real),
                        'diferenca': float(diferenca),
                    })
                    log_auditoria(f'Ajuste inventário: {p.nome} sist={float(p.estoque_atual - diferenca)} real={float(qtd_real)} dif={float(diferenca)}', 'Estoque', p.id)
        db.session.commit()
        if divergencias:
            flash(f'Inventário concluído! {len(divergencias)} divergências ajustadas.', 'warning')
        else:
            flash('Inventário concluído! Nenhuma divergência.', 'success')
        return redirect(url_for('estoque.inventario'))
    return render_template('estoque_inventario.html', produtos=produtos)


# ── Sugestão de Compra ──────────────────────────────────────────

@bp.route('/estoque/sugestao_compra')
@login_required
@modulo_required('Estoque')
def sugestao_compra():
    from app.models.models import SugestaoCompra, ItemVenda, Venda
    from sqlalchemy import func as sqla_func
    from datetime import date, timedelta

    trinta_dias = date.today() - timedelta(days=30)
    vendas = db.session.query(
        ItemVenda.produto_id,
        sqla_func.sum(ItemVenda.quantidade).label('qtd')
    ).join(Venda, ItemVenda.venda_id == Venda.id
    ).filter(Venda.status == 'F', Venda.created_at >= trinta_dias
    ).group_by(ItemVenda.produto_id).all()
    vendas_dict = {v.produto_id: float(v.qtd) for v in vendas}

    SugestaoCompra.query.delete()
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    sugestoes = []
    for p in produtos:
        v30 = vendas_dict.get(p.id, 0)
        estoque = float(p.estoque_atual)
        minimo = float(p.estoque_minimo or 0)
        if estoque < minimo or v30 > 0:
            dias_giro = 999
            if v30 > 0:
                dias_giro = round((estoque / (v30 / 30))) if (v30 / 30) > 0 else 999
            qtd_sugerida = max(minimo * 2 - estoque, v30 / 30 * 15 - estoque, 0)
            if qtd_sugerida <= 0 and estoque >= minimo:
                continue
            if v30 == 0:
                classe = 'C'
            elif v30 <= sum(vendas_dict.values()) * 0.05:
                classe = 'C'
            elif v30 <= sum(vendas_dict.values()) * 0.2:
                classe = 'B'
            else:
                classe = 'A'

            sug = SugestaoCompra(
                produto_id=p.id,
                quantidade_sugerida=max(qtd_sugerida, 1),
                estoque_atual=estoque,
                vendas_30d=v30,
                classe_abc=classe,
                prioridade={'A': 1, 'B': 2, 'C': 3}.get(classe, 9),
            )
            db.session.add(sug)
            sugestoes.append(sug)

    db.session.commit()
    sugestoes = SugestaoCompra.query.order_by(SugestaoCompra.prioridade, SugestaoCompra.quantidade_sugerida.desc()).all()
    return render_template('estoque_sugestao_compra.html', sugestoes=sugestoes)


# ── Etiquetas (Impressão) ────────────────────────────────────────

@bp.route('/estoque/etiquetas', methods=['GET', 'POST'])
@login_required
@modulo_required('Estoque')
def etiquetas():
    from app.models.models import Categoria
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    grupos = Categoria.query.order_by(Categoria.nome).all()
    if request.method == 'POST':
        ids = request.form.getlist('produtos')
        tipo = request.form.get('tipo', 'gondola')
        qtd = int(request.form.get('qtd', 1))
        if not ids:
            flash('Selecione ao menos um produto.', 'warning')
            return redirect(url_for('estoque.etiquetas'))
        selecionados = Produto.query.filter(Produto.id.in_(ids), Produto.ativo == True).order_by(Produto.nome).all()
        if qtd > 1:
            expandidos = []
            for p in selecionados:
                for _ in range(qtd):
                    expandidos.append(p)
            selecionados = expandidos
        return render_template('estoque_etiquetas_print.html', produtos=selecionados, tipo=tipo)
    return render_template('estoque_etiquetas.html', produtos=produtos, grupos=grupos)
