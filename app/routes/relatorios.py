from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app import db
from app.models.models import Venda, ItemVenda, Produto, Categoria, MovimentoCaixa, MovimentacaoEstoque, ContaPagar, ContaReceber, DocumentoFiscal, PagamentoVenda, Usuario
from datetime import date, datetime, timedelta
import calendar
from decimal import Decimal
from sqlalchemy import func, extract

bp = Blueprint('relatorios', __name__)

def _as_float(val):
    return float(val) if val else 0

def _periodo():
    hoje = date.today()
    de = request.args.get('de', (hoje - timedelta(days=30)).isoformat())
    ate = request.args.get('ate', hoje.isoformat())
    try:
        d1 = datetime.strptime(de, '%Y-%m-%d').date()
        d2 = datetime.strptime(ate, '%Y-%m-%d').date()
    except ValueError:
        d1 = hoje - timedelta(days=30)
        d2 = hoje
    return d1, d2

@bp.route('/relatorios')
@login_required
def dashboard():
    hoje = date.today()
    d1, d2 = _periodo()

    vendas_hoje = Venda.query.filter(
        Venda.status == 'F', func.date(Venda.created_at) == hoje
    ).count()
    total_hoje = db.session.query(func.sum(Venda.total)).filter(
        Venda.status == 'F', func.date(Venda.created_at) == hoje
    ).scalar() or 0

    total_periodo = db.session.query(func.sum(Venda.total)).filter(
        Venda.status == 'F', func.date(Venda.created_at).between(d1, d2)
    ).scalar() or 0
    qtd_periodo = Venda.query.filter(
        Venda.status == 'F', func.date(Venda.created_at).between(d1, d2)
    ).count()
    ticket_medio = _as_float(total_periodo) / qtd_periodo if qtd_periodo else 0

    entrada_estoque = db.session.query(func.sum(MovimentacaoEstoque.quantidade)).filter(
        MovimentacaoEstoque.tipo == 'E', func.date(MovimentacaoEstoque.created_at).between(d1, d2)
    ).scalar() or 0

    saida_estoque = db.session.query(func.sum(MovimentacaoEstoque.quantidade)).filter(
        MovimentacaoEstoque.tipo == 'S', func.date(MovimentacaoEstoque.created_at).between(d1, d2)
    ).scalar() or 0

    produtos_baixo = Produto.query.filter(
        Produto.ativo == True, Produto.estoque_atual <= Produto.estoque_minimo
    ).count()

    nfce_autorizadas = DocumentoFiscal.query.filter(
        DocumentoFiscal.status == '04',
        func.date(DocumentoFiscal.created_at).between(d1, d2)
    ).count()

    return render_template('rel_dashboard.html',
        vendas_hoje=vendas_hoje, total_hoje=_as_float(total_hoje),
        total_periodo=_as_float(total_periodo), qtd_periodo=qtd_periodo,
        ticket_medio=ticket_medio, entrada_estoque=_as_float(entrada_estoque),
        saida_estoque=_as_float(saida_estoque), produtos_baixo=produtos_baixo,
        nfce_autorizadas=nfce_autorizadas, d1=d1, d2=d2)

@bp.route('/relatorios/vendas')
@login_required
def vendas():
    d1, d2 = _periodo()
    return render_template('rel_vendas.html', d1=d1, d2=d2)

@bp.route('/relatorios/vendas/dados')
@login_required
def dados_vendas():
    d1, d2 = _periodo()
    dias = (d2 - d1).days + 1
    labels, valores, quant = [], [], []
    for i in range(dias):
        dia = d1 + timedelta(days=i)
        total = db.session.query(func.sum(Venda.total)).filter(
            Venda.status == 'F', func.date(Venda.created_at) == dia
        ).scalar() or 0
        qtd = Venda.query.filter(
            Venda.status == 'F', func.date(Venda.created_at) == dia
        ).count()
        labels.append(dia.strftime('%d/%m'))
        valores.append(_as_float(total))
        quant.append(qtd)
    return jsonify(labels=labels, valores=valores, quant=quant)

@bp.route('/relatorios/produtos')
@login_required
def produtos():
    d1, d2 = _periodo()
    return render_template('rel_produtos.html', d1=d1, d2=d2)

@bp.route('/relatorios/produtos/dados')
@login_required
def dados_produtos():
    d1, d2 = _periodo()
    rows = db.session.query(
        Produto.nome,
        func.sum(ItemVenda.quantidade).label('qtd'),
        func.sum(ItemVenda.subtotal).label('total')
    ).join(ItemVenda, ItemVenda.produto_id == Produto.id
    ).join(Venda, Venda.id == ItemVenda.venda_id
    ).filter(
        Venda.status == 'F',
        func.date(Venda.created_at).between(d1, d2)
    ).group_by(Produto.nome
    ).order_by(func.sum(ItemVenda.quantidade).desc()).limit(15).all()
    return jsonify(
        labels=[r.nome for r in rows],
        qtd=[_as_float(r.qtd) for r in rows],
        total=[_as_float(r.total) for r in rows],
    )

@bp.route('/relatorios/categorias/dados')
@login_required
def dados_categorias():
    d1, d2 = _periodo()
    rows = db.session.query(
        Categoria.nome,
        func.sum(ItemVenda.subtotal).label('total')
    ).select_from(ItemVenda
    ).join(Venda, Venda.id == ItemVenda.venda_id
    ).join(Produto, Produto.id == ItemVenda.produto_id
    ).join(Categoria, Categoria.id == Produto.categoria_id, isouter=True
    ).filter(
        Venda.status == 'F',
        func.date(Venda.created_at).between(d1, d2)
    ).group_by(Categoria.nome).order_by(func.sum(ItemVenda.subtotal).desc()).all()
    return jsonify(
        labels=[r.nome or 'Sem categoria' for r in rows],
        valores=[_as_float(r.total) for r in rows],
    )

@bp.route('/relatorios/financeiro/dados')
@login_required
def dados_financeiro():
    d1, d2 = _periodo()
    dias = (d2 - d1).days + 1
    labels, entradas, saidas = [], [], []
    for i in range(dias):
        dia = d1 + timedelta(days=i)
        e = db.session.query(func.sum(MovimentoCaixa.valor)).filter(
            MovimentoCaixa.tipo == 'E', MovimentoCaixa.data == dia
        ).scalar() or 0
        s = db.session.query(func.sum(MovimentoCaixa.valor)).filter(
            MovimentoCaixa.tipo == 'S', MovimentoCaixa.data == dia
        ).scalar() or 0
        labels.append(dia.strftime('%d/%m'))
        entradas.append(_as_float(e))
        saidas.append(_as_float(s))
    return jsonify(labels=labels, entradas=entradas, saidas=saidas)

@bp.route('/relatorios/estoque/dados')
@login_required
def dados_estoque_giro():
    rows = db.session.query(
        Produto.nome,
        Produto.estoque_atual,
        Produto.estoque_minimo,
        func.coalesce(func.sum(MovimentacaoEstoque.quantidade).filter(
            MovimentacaoEstoque.tipo == 'S',
        ), 0).label('total_saidas'),
    ).outerjoin(MovimentacaoEstoque, MovimentacaoEstoque.produto_id == Produto.id
    ).filter(Produto.ativo == True
    ).group_by(Produto.id, Produto.nome, Produto.estoque_atual, Produto.estoque_minimo
    ).order_by(
        func.coalesce(func.sum(MovimentacaoEstoque.quantidade).filter(
            MovimentacaoEstoque.tipo == 'S',
        ), 0).desc()
    ).limit(20).all()
    return jsonify(
        labels=[r.nome for r in rows],
        estoque=[_as_float(r.estoque_atual) for r in rows],
        minimo=[_as_float(r.estoque_minimo) for r in rows],
        saidas=[_as_float(r.total_saidas) for r in rows],
    )


@bp.route('/relatorios/margem')
@login_required
def margem():
    produtos = Produto.query.filter(
        Produto.ativo == True,
        Produto.preco_custo > 0
    ).order_by(Produto.nome).all()
    dados = []
    for p in produtos:
        custo = float(p.preco_custo)
        venda = float(p.preco_venda)
        margem_valor = venda - custo
        margem_perc = (margem_valor / custo) * 100 if custo else 0
        dados.append({'produto': p, 'margem_valor': margem_valor, 'margem_perc': margem_perc})
    return render_template('rel_margem.html', dados=dados)


@bp.route('/relatorios/dre')
@login_required
def dre():
    hoje = date.today()
    de = request.args.get('de', hoje.replace(day=1).isoformat())
    ate = request.args.get('ate', hoje.isoformat())
    d1 = datetime.strptime(de, '%Y-%m-%d').date()
    d2 = datetime.strptime(ate, '%Y-%m-%d').date()

    receita_bruta = db.session.query(func.sum(Venda.total)).filter(
        Venda.status == 'F', func.date(Venda.created_at).between(d1, d2)
    ).scalar() or 0
    desconto_total = db.session.query(func.sum(Venda.desconto)).filter(
        Venda.status == 'F', func.date(Venda.created_at).between(d1, d2)
    ).scalar() or 0

    receita_liquida = float(receita_bruta) - float(desconto_total)

    cmv_val = db.session.query(func.sum(
        MovimentacaoEstoque.quantidade * MovimentacaoEstoque.preco_unitario
    )).filter(
        MovimentacaoEstoque.tipo == 'S',
        func.date(MovimentacaoEstoque.created_at).between(d1, d2)
    ).scalar() or 0
    cmv = float(cmv_val)

    margem_bruta = receita_liquida - cmv
    margem_percent = (margem_bruta / receita_liquida * 100) if receita_liquida else 0

    despesas = db.session.query(func.sum(MovimentoCaixa.valor)).filter(
        MovimentoCaixa.tipo == 'S', MovimentoCaixa.data.between(d1, d2)
    ).scalar() or 0

    resultado = margem_bruta - float(despesas)
    resultado_percent = (resultado / receita_liquida * 100) if receita_liquida else 0

    return render_template('rel_dre.html',
        data_ini=d1, data_fim=d2,
        receita_bruta=float(receita_bruta), desconto_total=float(desconto_total),
        receita_liquida=receita_liquida, cmv=cmv,
        margem_bruta=margem_bruta, margem_percent=margem_percent,
        despesas=float(despesas), resultado=resultado,
        resultado_percent=resultado_percent)


@bp.route('/relatorios/vendas/vendedor')
@login_required
def vendas_vendedor():
    d1, d2 = _periodo()
    return render_template('rel_vendas_vendedor.html', d1=d1, d2=d2)


@bp.route('/relatorios/vendas/vendedor/dados')
@login_required
def dados_vendas_vendedor():
    d1, d2 = _periodo()
    rows = db.session.query(
        Usuario.nome,
        func.count(Venda.id).label('qtd'),
        func.sum(Venda.total).label('total')
    ).join(Venda, Venda.usuario_id == Usuario.id
    ).filter(
        Venda.status == 'F',
        func.date(Venda.created_at).between(d1, d2)
    ).group_by(Usuario.nome).order_by(func.sum(Venda.total).desc()).all()
    return jsonify(
        labels=[r.nome for r in rows],
        qtd=[int(r.qtd) for r in rows],
        valores=[_as_float(r.total) for r in rows],
    )


@bp.route('/relatorios/giro')
@login_required
def giro():
    hoje = date.today()
    de = request.args.get('de', (hoje - timedelta(days=30)).isoformat())
    ate = request.args.get('ate', hoje.isoformat())
    d1 = datetime.strptime(de, '%Y-%m-%d').date() if de else hoje - timedelta(days=30)
    d2 = datetime.strptime(ate, '%Y-%m-%d').date() if ate else hoje
    diff_dias = (d2 - d1).days or 1

    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    dados = []
    for p in produtos:
        saidas = db.session.query(func.sum(MovimentacaoEstoque.quantidade)).filter(
            MovimentacaoEstoque.tipo == 'S', MovimentacaoEstoque.produto_id == p.id,
            func.date(MovimentacaoEstoque.created_at).between(d1, d2)
        ).scalar() or 0
        estoque = float(p.estoque_atual)
        saidas_f = float(saidas)
        giro_dias = 999
        if saidas_f > 0:
            giro_dias = round((estoque / (saidas_f / diff_dias))) if (saidas_f / diff_dias) > 0 else 999
        dados.append({
            'produto': p,
            'estoque': estoque,
            'saidas': saidas_f,
            'giro_dias': giro_dias,
        })

    dados.sort(key=lambda x: x['giro_dias'] if x['giro_dias'] != 999 else 9999)
    return render_template('rel_giro.html', dados=dados, data_ini=d1, data_fim=d2)


@bp.route('/relatorios/dashboard_gerencial')
@login_required
def dashboard_gerencial():
    return render_template('rel_dashboard_gerencial.html')


@bp.route('/relatorios/dashboard_gerencial/dados')
@login_required
def dados_dashboard_gerencial():
    from datetime import date, timedelta
    from app.models.models import ContaPagar, ContaReceber, Grupo, ItemVenda, Venda, PagamentoVenda
    from sqlalchemy import extract, func as f

    hoje = date.today()
    mes_atual = hoje.replace(day=1)
    mes_passado = (mes_atual - timedelta(days=1)).replace(day=1)
    daqui_30 = hoje + timedelta(days=30)

    def total_vendas(ini, fim):
        return float(db.session.query(f.sum(Venda.total)).filter(
            Venda.status == 'F', f.date(Venda.created_at).between(ini, fim)
        ).scalar() or 0)

    def qtd_vendas(ini, fim):
        return Venda.query.filter(
            Venda.status == 'F', f.date(Venda.created_at).between(ini, fim)
        ).count()

    vendas_mes = total_vendas(mes_atual, hoje)
    vendas_mes_passado = total_vendas(mes_passado, mes_atual - timedelta(days=1))
    qtd_mes = qtd_vendas(mes_atual, hoje)
    qtd_mes_passado = qtd_vendas(mes_passado, mes_atual - timedelta(days=1))

    ticket_medio = vendas_mes / qtd_mes if qtd_mes else 0
    crescimento = ((vendas_mes - vendas_mes_passado) / vendas_mes_passado * 100) if vendas_mes_passado else 0

    # Vendas por hora hoje
    hoje_dt = datetime.combine(hoje, datetime.min.time())
    vendas_hora = db.session.query(
        extract('hour', Venda.created_at).label('h'),
        f.count(Venda.id).label('q'),
        f.sum(Venda.total).label('v')
    ).filter(Venda.status == 'F', Venda.created_at >= hoje_dt
    ).group_by('h').order_by('h').all()

    formas = db.session.query(
        PagamentoVenda.forma_pagamento,
        f.sum(PagamentoVenda.valor).label('total')
    ).join(Venda).filter(
        Venda.status == 'F', f.date(Venda.created_at).between(mes_atual, hoje)
    ).group_by(PagamentoVenda.forma_pagamento).all()

    # Top 10 produtos
    top_prod = db.session.query(
        ItemVenda.produto_id,
        Produto.nome,
        f.sum(ItemVenda.quantidade).label('qtd'),
        f.sum(ItemVenda.subtotal).label('total')
    ).join(Produto, ItemVenda.produto_id == Produto.id
    ).join(Venda, ItemVenda.venda_id == Venda.id
    ).filter(Venda.status == 'F', f.date(Venda.created_at).between(mes_atual, hoje)
    ).group_by(ItemVenda.produto_id, Produto.nome
    ).order_by(f.sum(ItemVenda.subtotal).desc()).limit(10).all()

    # Margem por categoria
    margem_grupo = db.session.query(
        Categoria.nome,
        (f.sum(ItemVenda.subtotal) - f.sum(ItemVenda.quantidade * Produto.preco_custo)).label('margem'),
        ((f.sum(ItemVenda.subtotal) - f.sum(ItemVenda.quantidade * Produto.preco_custo)) / f.sum(ItemVenda.subtotal) * 100).label('pct')
    ).select_from(ItemVenda
    ).join(Venda, ItemVenda.venda_id == Venda.id
    ).join(Produto, ItemVenda.produto_id == Produto.id
    ).join(Categoria, Produto.categoria_id == Categoria.id, isouter=True
    ).filter(Venda.status == 'F', f.date(Venda.created_at).between(mes_atual, hoje)
    ).group_by(Categoria.nome).all()

    # Projeção fluxo caixa 30 dias
    a_pagar = ContaPagar.query.filter_by(pago=False).filter(
        ContaPagar.data_vencimento.between(hoje, daqui_30)
    ).order_by(ContaPagar.data_vencimento).all()
    a_receber = ContaReceber.query.filter_by(recebido=False).filter(
        ContaReceber.data_vencimento.between(hoje, daqui_30)
    ).order_by(ContaReceber.data_vencimento).all()
    fluxo_labels = []
    fluxo_entradas = []
    fluxo_saidas = []
    fluxo_saldo = []
    saldo = 0
    for dia in range(31):
        d = hoje + timedelta(days=dia)
        ent = sum(float(c.valor) for c in a_receber if c.data_vencimento == d)
        sai = sum(float(c.valor) for c in a_pagar if c.data_vencimento == d)
        saldo += ent - sai
        if dia % 5 == 0 or dia == 30:
            fluxo_labels.append(d.strftime('%d/%m'))
            fluxo_entradas.append(ent)
            fluxo_saidas.append(sai)
            fluxo_saldo.append(round(saldo, 2))

    return jsonify({
        'vendas_mes': round(vendas_mes, 2),
        'vendas_mes_passado': round(vendas_mes_passado, 2),
        'qtd_mes': qtd_mes,
        'qtd_mes_passado': qtd_mes_passado,
        'ticket_medio': round(ticket_medio, 2),
        'crescimento': round(crescimento, 1),
        'vendas_hora': {
            'labels': [f'{int(r.h):02d}h' for r in vendas_hora],
            'valores': [float(r.v) for r in vendas_hora],
            'qtd': [int(r.q) for r in vendas_hora],
        },
        'formas_pagamento': {
            'labels': [r.forma_pagamento for r in formas],
            'valores': [float(r.total) for r in formas],
        },
        'top_produtos': {
            'labels': [r.nome[:25] for r in top_prod],
            'valores': [float(r.total) for r in top_prod],
        },
        'margem_grupo': {
            'labels': [r.nome or 'Sem Grupo' for r in margem_grupo],
            'valores': [round(float(r.margem), 2) for r in margem_grupo],
            'pct': [round(float(r.pct), 1) if r.pct else 0 for r in margem_grupo],
        },
        'fluxo_caixa': {
            'labels': fluxo_labels,
            'entradas': [round(e, 2) for e in fluxo_entradas],
            'saidas': [round(s, 2) for s in fluxo_saidas],
            'saldo': fluxo_saldo,
        },
    })


@bp.route('/relatorios/kpis/dados')
@login_required
def dados_kpis():
    hoje = date.today()
    mes_atual = hoje.replace(day=1)
    mes_anterior = (mes_atual - timedelta(days=1)).replace(day=1)

    def vendas_periodo(ini, fim):
        total = db.session.query(func.sum(Venda.total)).filter(
            Venda.status == 'F', func.date(Venda.created_at).between(ini, fim)
        ).scalar() or 0
        qtd = Venda.query.filter(
            Venda.status == 'F', func.date(Venda.created_at).between(ini, fim)
        ).count()
        return float(total), qtd

    total_atual, qtd_atual = vendas_periodo(mes_atual, hoje)
    total_ant, qtd_ant = vendas_periodo(mes_anterior, mes_atual - timedelta(days=1))
    crescimento = ((total_atual - total_ant) / total_ant * 100) if total_ant else 0

    ticket_atual = total_atual / qtd_atual if qtd_atual else 0
    ticket_ant = total_ant / qtd_ant if qtd_ant else 0

    custo_total = db.session.query(func.sum(
        MovimentacaoEstoque.quantidade * MovimentacaoEstoque.preco_unitario
    )).filter(
        MovimentacaoEstoque.tipo == 'S',
        func.date(MovimentacaoEstoque.created_at).between(mes_atual, hoje)
    ).scalar() or 0
    margem_bruta = total_atual - float(custo_total)
    margem_percent = (margem_bruta / total_atual * 100) if total_atual else 0

    return jsonify({
        'total_atual': total_atual, 'qtd_atual': qtd_atual,
        'total_ant': total_ant, 'qtd_ant': qtd_ant,
        'crescimento': round(crescimento, 1),
        'ticket_atual': round(ticket_atual, 2),
        'ticket_ant': round(ticket_ant, 2),
        'margem_bruta': round(margem_bruta, 2),
        'margem_percent': round(margem_percent, 1),
    })


@bp.route('/relatorios/vendas/hora')
@login_required
def dados_vendas_hora():
    rows = db.session.query(
        extract('hour', Venda.created_at).label('hora'),
        func.count(Venda.id).label('qtd'),
        func.sum(Venda.total).label('total'),
    ).filter(Venda.status == 'F').group_by('hora').order_by('hora').all()
    labels = [f'{int(r.hora):02d}h' if r.hora else '00h' for r in rows]
    qtd = [int(r.qtd) for r in rows]
    valores = [float(r.total) for r in rows]
    return jsonify(labels=labels, qtd=qtd, valores=valores)


@bp.route('/relatorios/vendas/formas_pagamento')
@login_required
def dados_formas_pagamento():
    rows = db.session.query(
        PagamentoVenda.forma_pagamento,
        func.sum(PagamentoVenda.valor).label('total'),
    ).join(Venda, Venda.id == PagamentoVenda.venda_id
    ).filter(Venda.status == 'F'
    ).group_by(PagamentoVenda.forma_pagamento).all()
    return jsonify(
        labels=[r.forma_pagamento for r in rows],
        valores=[float(r.total) for r in rows],
    )


@bp.route('/relatorios/dashboard_ano_anterior/dados')
@login_required
def dados_ano_anterior():
    hoje = date.today()
    mes_atual = hoje.replace(day=1)

    labels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    ano_atual = hoje.year
    ano_passado = hoje.year - 1

    atual = []
    passado = []
    for mes in range(1, 13):
        if mes == hoje.month and ano_atual == hoje.year:
            fim = hoje
        else:
            _, ultimo = calendar.monthrange(ano_atual if mes <= hoje.month else ano_passado, mes)
            fim = date(ano_atual if mes <= hoje.month else ano_atual, mes, ultimo)
        ini = date(ano_atual, mes, 1)
        if mes >= 1 and mes <= hoje.month:
            v = db.session.query(func.sum(Venda.total)).filter(
                Venda.status == 'F', func.date(Venda.created_at).between(ini, fim)
            ).scalar() or 0
            atual.append(round(float(v), 2))
        else:
            atual.append(None)

        ini_p = date(ano_passado, mes, 1)
        _, ult_p = calendar.monthrange(ano_passado, mes)
        fim_p = date(ano_passado, mes, ult_p)
        v_p = db.session.query(func.sum(Venda.total)).filter(
            Venda.status == 'F', func.date(Venda.created_at).between(ini_p, fim_p)
        ).scalar() or 0
        passado.append(round(float(v_p), 2))

    crescimento_anual = 0
    total_atual = sum(v for v in atual if v)
    total_passado = sum(v for v in passado if v)
    if total_passado:
        crescimento_anual = round((total_atual - total_passado) / total_passado * 100, 1)

    return jsonify(labels=labels, atual=atual, passado=passado, crescimento_anual=crescimento_anual)


@bp.route('/relatorios/dashboard_metas/dados')
@login_required
def dados_metas():
    from app.models.models import MetaVendedor, Usuario
    hoje = date.today()
    mes = hoje.month
    ano = hoje.year

    metas = MetaVendedor.query.filter_by(mes=mes, ano=ano).order_by(MetaVendedor.valor_meta.desc()).all()
    labels = []
    meta_valores = []
    real_valores = []

    for m in metas:
        labels.append(m.usuario.nome if m.usuario else f'Vendedor {m.usuario_id}')
        meta_valores.append(float(m.valor_meta))
        if m.atingido and m.atingido > 0:
            real_valores.append(float(m.atingido))
        else:
            vendas = db.session.query(func.sum(Venda.total)).filter(
                Venda.status == 'F',
                Venda.usuario_id == m.usuario_id,
                func.extract('month', Venda.created_at) == mes,
                func.extract('year', Venda.created_at) == ano
            ).scalar() or 0
            real_valores.append(round(float(vendas), 2))

    return jsonify(labels=labels, meta=meta_valores, real=real_valores)
