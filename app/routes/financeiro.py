from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import ContaPagar, ContaReceber, CategoriaFinanceira, MovimentoCaixa, Cliente, Fornecedor, Boleto, Conciliacao, ConciliacaoItem
from datetime import date, datetime, timedelta
from decimal import Decimal
from app.audit import log_auditoria

bp = Blueprint('financeiro', __name__)


@bp.route('/financeiro')
@login_required
def dashboard():
    hoje = date.today()
    a_pagar = ContaPagar.query.filter_by(pago=False).order_by(ContaPagar.data_vencimento).all()
    a_receber = ContaReceber.query.filter_by(recebido=False).order_by(ContaReceber.data_vencimento).all()
    total_pagar = sum(float(c.valor) for c in a_pagar)
    total_receber = sum(float(c.valor) for c in a_receber)
    vencendo_hoje = [c for c in a_pagar if c.data_vencimento == hoje] + [c for c in a_receber if c.data_vencimento == hoje]
    return render_template('fin_dashboard.html', a_pagar=a_pagar, a_receber=a_receber,
                           total_pagar=total_pagar, total_receber=total_receber,
                           vencendo_hoje=vencendo_hoje, hoje=hoje)


@bp.route('/financeiro/categorias')
@login_required
def lista_categorias():
    cats = CategoriaFinanceira.query.order_by(CategoriaFinanceira.nome).all()
    return render_template('fin_categorias_lista.html', categorias=cats)


@bp.route('/financeiro/categorias/novo', methods=['GET', 'POST'])
@login_required
def nova_categoria():
    if request.method == 'POST':
        c = CategoriaFinanceira(nome=request.form['nome'], tipo=request.form['tipo'])
        db.session.add(c)
        db.session.commit()
        log_auditoria(f'Criou categoria financeira: {c.nome}', 'CategoriaFinanceira', c.id)
        flash('Categoria criada!', 'success')
        return redirect(url_for('financeiro.lista_categorias'))
    return render_template('fin_categorias_form.html', cat=None)


@bp.route('/financeiro/categorias/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_categoria(id):
    c = CategoriaFinanceira.query.get_or_404(id)
    if request.method == 'POST':
        c.nome = request.form['nome']
        c.tipo = request.form['tipo']
        c.ativo = 'ativo' in request.form
        db.session.commit()
        log_auditoria(f'Editou categoria financeira: {c.nome}', 'CategoriaFinanceira', c.id)
        flash('Categoria atualizada!', 'success')
        return redirect(url_for('financeiro.lista_categorias'))
    return render_template('fin_categorias_form.html', cat=c)


@bp.route('/financeiro/pagar')
@login_required
def lista_pagar():
    contas = ContaPagar.query.order_by(ContaPagar.data_vencimento).all()
    return render_template('fin_pagar_lista.html', contas=contas, hoje=date.today())


@bp.route('/financeiro/pagar/novo', methods=['GET', 'POST'])
@login_required
def nova_conta_pagar():
    fornecedores = Fornecedor.query.filter_by(ativo=True).order_by(Fornecedor.nome).all()
    categorias = CategoriaFinanceira.query.filter_by(tipo='D', ativo=True).order_by(CategoriaFinanceira.nome).all()
    if request.method == 'POST':
        c = ContaPagar(
            fornecedor_id=request.form.get('fornecedor_id') or None,
            categoria_id=request.form.get('categoria_id') or None,
            descricao=request.form['descricao'],
            valor=request.form['valor'],
            data_vencimento=datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d').date(),
            documento=request.form.get('documento'),
            observacao=request.form.get('observacao'),
        )
        db.session.add(c)
        db.session.commit()
        log_auditoria(f'Criou conta a pagar: {c.descricao}', 'ContaPagar', c.id)
        flash('Conta a pagar registrada!', 'success')
        return redirect(url_for('financeiro.lista_pagar'))
    return render_template('fin_pagar_form.html', conta=None, fornecedores=fornecedores, categorias=categorias)


@bp.route('/financeiro/pagar/baixar/<int:id>', methods=['POST'])
@login_required
def baixar_pagar(id):
    conta = ContaPagar.query.get_or_404(id)
    data_pagamento = request.form.get('data_pagamento')
    valor_pago = request.form.get('valor_pago', str(conta.valor))
    conta.valor_pago = valor_pago
    conta.data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d').date() if data_pagamento else date.today()
    conta.pago = True
    mov = MovimentoCaixa(
        tipo='S', descricao=f'Pgto: {conta.descricao}', valor=valor_pago,
        data=conta.data_pagamento, categoria_id=conta.categoria_id,
        conta_pagar_id=conta.id, documento=conta.documento
    )
    db.session.add(mov)
    db.session.commit()
    log_auditoria(f'Baixou conta a pagar: {conta.descricao}', 'ContaPagar', conta.id)
    flash('Conta baixada!', 'success')
    return redirect(url_for('financeiro.lista_pagar'))


@bp.route('/financeiro/receber')
@login_required
def lista_receber():
    contas = ContaReceber.query.order_by(ContaReceber.data_vencimento).all()
    return render_template('fin_receber_lista.html', contas=contas, hoje=date.today())


@bp.route('/financeiro/receber/novo', methods=['GET', 'POST'])
@login_required
def nova_conta_receber():
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    categorias = CategoriaFinanceira.query.filter_by(tipo='R', ativo=True).order_by(CategoriaFinanceira.nome).all()
    if request.method == 'POST':
        c = ContaReceber(
            cliente_id=request.form.get('cliente_id') or None,
            categoria_id=request.form.get('categoria_id') or None,
            descricao=request.form['descricao'],
            valor=request.form['valor'],
            data_vencimento=datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d').date(),
            documento=request.form.get('documento'),
            observacao=request.form.get('observacao'),
        )
        db.session.add(c)
        db.session.commit()
        log_auditoria(f'Criou conta a receber: {c.descricao}', 'ContaReceber', c.id)
        flash('Conta a receber registrada!', 'success')
        return redirect(url_for('financeiro.lista_receber'))
    return render_template('fin_receber_form.html', conta=None, clientes=clientes, categorias=categorias)


@bp.route('/financeiro/receber/baixar/<int:id>', methods=['POST'])
@login_required
def baixar_receber(id):
    conta = ContaReceber.query.get_or_404(id)
    data_recebimento = request.form.get('data_recebimento')
    valor_recebido = request.form.get('valor_recebido', str(conta.valor))
    conta.valor_recebido = valor_recebido
    conta.data_recebimento = datetime.strptime(data_recebimento, '%Y-%m-%d').date() if data_recebimento else date.today()
    conta.recebido = True
    mov = MovimentoCaixa(
        tipo='E', descricao=f'Rec: {conta.descricao}', valor=valor_recebido,
        data=conta.data_recebimento, categoria_id=conta.categoria_id,
        conta_receber_id=conta.id, documento=conta.documento
    )
    db.session.add(mov)
    db.session.commit()
    log_auditoria(f'Recebeu conta: {conta.descricao}', 'ContaReceber', conta.id)
    flash('Conta recebida!', 'success')
    return redirect(url_for('financeiro.lista_receber'))


@bp.route('/financeiro/fluxo')
@login_required
def fluxo_caixa():
    hoje = date.today()
    data_ini = request.args.get('de')
    data_fim = request.args.get('ate')
    if not data_ini:
        data_ini = hoje.replace(day=1)
    else:
        data_ini = datetime.strptime(data_ini, '%Y-%m-%d').date()
    if not data_fim:
        data_fim = hoje
    else:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    movs = MovimentoCaixa.query.filter(MovimentoCaixa.data.between(data_ini, data_fim)).order_by(MovimentoCaixa.data).all()
    entradas = sum(float(m.valor) for m in movs if m.tipo == 'E')
    saidas = sum(float(m.valor) for m in movs if m.tipo == 'S')
    # vencimentos futuros
    a_pagar = ContaPagar.query.filter_by(pago=False).filter(ContaPagar.data_vencimento.between(data_ini, data_fim)).all()
    a_receber = ContaReceber.query.filter_by(recebido=False).filter(ContaReceber.data_vencimento.between(data_ini, data_fim)).all()
    prev_pagar = sum(float(c.valor) for c in a_pagar)
    prev_receber = sum(float(c.valor) for c in a_receber)
    return render_template('fin_fluxo.html', movs=movs, entradas=entradas, saidas=saidas,
                           saldo=entradas - saidas, prev_pagar=prev_pagar, prev_receber=prev_receber,
                           data_ini=data_ini, data_fim=data_fim)


# ── Boletos ──────────────────────────────────────────────────────

@bp.route('/financeiro/boletos')
@login_required
def lista_boletos():
    boletos = Boleto.query.order_by(Boleto.data_vencimento).all()
    return render_template('fin_boletos_lista.html', boletos=boletos, hoje=date.today())


def _gerar_linha_digitavel(valor, vencimento, documento):
    """Gera linha digitável simulada (banco 001 - BB). Para integração real, usar API."""
    from datetime import datetime
    banco = '001'
    moeda = '9'
    fator_venc = (vencimento - date(1997, 10, 7)).days
    valor_str = f'{int(valor * 100):010d}'
    nosso_numero = str(abs(hash(f'{documento}{valor}{vencimento}'))) % 99999999
    campo1 = f'{banco}{moeda}{nosso_numero[:5]:0>5}'
    dv1 = sum(int(c) * (2 if i % 2 == 0 else 1) for i, c in enumerate(campo1))
    dv1 = (10 - dv1 % 10) % 10
    campo2 = f'{nosso_numero[5:10]:0>5}{nosso_numero[10:15]:0>5}'
    dv2 = sum(int(c) * (2 if i % 2 == 0 else 1) for i, c in enumerate(campo2))
    dv2 = (10 - dv2 % 10) % 10
    campo3 = f'{nosso_numero[15:20]:0>5}000'
    dv3 = sum(int(c) * (2 if i % 2 == 0 else 1) for i, c in enumerate(campo3))
    dv3 = (10 - dv3 % 10) % 10
    cod_barras = f'{banco}{moeda}{fator_venc:04d}{valor_str}{nosso_numero:0>20}'
    dv_geral = sum(int(c) * (2 if i % 2 == 0 else 1) for i, c in enumerate(cod_barras))
    dv_geral = (10 - dv_geral % 10) % 10
    linha = f'{campo1}{dv1}.{campo2}{dv2}.{campo3}{dv3} {dv_geral} {fator_venc:04d}{valor_str}'
    return linha, cod_barras, nosso_numero


@bp.route('/financeiro/boletos/gerar/<int:conta_id>', methods=['POST'])
@login_required
def gerar_boleto(conta_id):
    conta = ContaReceber.query.get_or_404(conta_id)
    if conta.recebido:
        flash('Conta já recebida!', 'warning')
        return redirect(url_for('financeiro.lista_receber'))
    boleto_existente = Boleto.query.filter_by(conta_receber_id=conta_id, status='A').first()
    if boleto_existente:
        flash('Boleto já gerado para esta conta!', 'warning')
        return redirect(url_for('financeiro.lista_boletos'))
    linha, barras, nosso = _gerar_linha_digitavel(float(conta.valor), conta.data_vencimento, str(conta.id))
    b = Boleto(
        conta_receber_id=conta.id, cliente_id=conta.cliente_id,
        valor=conta.valor, data_vencimento=conta.data_vencimento,
        numero=f'BL-{conta.id}-{conta.data_vencimento.strftime("%Y%m%d")}',
        nosso_numero=nosso, linha_digitavel=linha, codigo_barras=barras,
    )
    db.session.add(b)
    db.session.commit()
    log_auditoria(f'Gerou boleto: {b.numero}', 'Boleto', b.id)
    flash(f'Boleto {b.numero} gerado!', 'success')
    return redirect(url_for('financeiro.lista_boletos'))


@bp.route('/financeiro/boletos/visualizar/<int:id>')
@login_required
def visualizar_boleto(id):
    b = Boleto.query.get_or_404(id)
    return render_template('fin_boletos_print.html', boleto=b)


@bp.route('/financeiro/boletos/baixar/<int:id>', methods=['POST'])
@login_required
def baixar_boleto(id):
    b = Boleto.query.get_or_404(id)
    data_pagamento = request.form.get('data_pagamento', str(date.today()))
    valor_pago = Decimal(request.form.get('valor_pago', str(b.valor)))
    b.status = 'P'
    b.data_pagamento = datetime.strptime(data_pagamento, '%Y-%m-%d').date() if data_pagamento else date.today()
    b.valor_pago = valor_pago
    if b.conta_receber:
        b.conta_receber.recebido = True
        b.conta_receber.data_recebimento = b.data_pagamento
        b.conta_receber.valor_recebido = valor_pago
        mov = MovimentoCaixa(
            tipo='E', descricao=f'Boleto: {b.numero}', valor=valor_pago,
            data=b.data_pagamento, documento=b.numero, conta_receber_id=b.conta_receber_id
        )
        db.session.add(mov)
    db.session.commit()
    log_auditoria(f'Baixou boleto: {b.numero}', 'Boleto', b.id)
    flash('Boleto baixado!', 'success')
    return redirect(url_for('financeiro.lista_boletos'))


@bp.route('/financeiro/boletos/cancelar/<int:id>', methods=['POST'])
@login_required
def cancelar_boleto(id):
    b = Boleto.query.get_or_404(id)
    b.status = 'C'
    db.session.commit()
    log_auditoria(f'Cancelou boleto: {b.numero}', 'Boleto', b.id)
    flash('Boleto cancelado.', 'warning')
    return redirect(url_for('financeiro.lista_boletos'))


# ── Conciliação Bancária ─────────────────────────────────────────

@bp.route('/financeiro/conciliacao')
@login_required
def lista_conciliacoes():
    lista = Conciliacao.query.order_by(Conciliacao.created_at.desc()).all()
    return render_template('fin_conciliacao_lista.html', conciliacoes=lista)


@bp.route('/financeiro/conciliacao/nova', methods=['GET', 'POST'])
@login_required
def nova_conciliacao():
    if request.method == 'POST':
        c = Conciliacao(arquivo_nome=request.form.get('arquivo_nome', ''), usuario_id=current_user.id)
        db.session.add(c)
        db.session.flush()

        linhas_raw = request.form.get('linhas', '')
        linhas = 0
        if linhas_raw:
            for raw in linhas_raw.strip().split('\n'):
                raw = raw.strip()
                if not raw:
                    continue
                parts = raw.split('\t')
                if len(parts) < 3:
                    continue
                try:
                    tipo = 'C' if parts[0].upper() in ('C', 'CREDITO', '+') else 'D'
                    valor = Decimal(parts[1].replace(',', '.'))
                    descricao = parts[2]
                    documento = parts[3] if len(parts) > 3 else ''
                    data_item = datetime.strptime(parts[4], '%Y-%m-%d').date() if len(parts) > 4 else date.today()
                    item = ConciliacaoItem(
                        conciliacao_id=c.id,
                        tipo=tipo, descricao=descricao, valor=abs(valor),
                        data=data_item, documento=documento,
                    )
                    db.session.add(item)
                    linhas += 1
                except (ValueError, IndexError):
                    pass

        c.total_linhas = linhas
        db.session.commit()
        log_auditoria(f'Nova conciliação: {c.arquivo_nome or "manual"} ({linhas} linhas)', 'Conciliacao', c.id)
        flash(f'Conciliação criada com {linhas} linhas!', 'success')
        return redirect(url_for('financeiro.detalhe_conciliacao', id=c.id))
    return render_template('fin_conciliacao_form.html')


@bp.route('/financeiro/conciliacao/<int:id>')
@login_required
def detalhe_conciliacao(id):
    c = Conciliacao.query.get_or_404(id)
    itens_pendentes = c.itens.filter_by(conciliado=False).order_by(ConciliacaoItem.data).all()
    itens_conciliados = c.itens.filter_by(conciliado=True).order_by(ConciliacaoItem.data).all()
    a_pagar = ContaPagar.query.filter_by(pago=False).order_by(ContaPagar.data_vencimento).all()
    a_receber = ContaReceber.query.filter_by(recebido=False).order_by(ContaReceber.data_vencimento).all()
    return render_template('fin_conciliacao_detalhe.html', conciliacao=c,
                           pendentes=itens_pendentes, conciliados=itens_conciliados,
                           a_pagar=a_pagar, a_receber=a_receber)


@bp.route('/financeiro/conciliacao/<int:id>/conciliar/<int:item_id>', methods=['POST'])
@login_required
def conciliar_item(id, item_id):
    c = Conciliacao.query.get_or_404(id)
    item = ConciliacaoItem.query.get_or_404(item_id)
    if item.conciliacao_id != c.id:
        flash('Item não pertence a esta conciliação.', 'danger')
        return redirect(url_for('financeiro.detalhe_conciliacao', id=id))

    tipo_destino = request.form.get('tipo_destino')  # pagar or receber
    destino_id = request.form.get('destino_id')
    if tipo_destino and destino_id:
        if tipo_destino == 'pagar':
            item.conta_pagar_id = int(destino_id)
            conta = ContaPagar.query.get(int(destino_id))
            if conta and not conta.pago:
                conta.pago = True
                conta.valor_pago = item.valor
                conta.data_pagamento = item.data or date.today()
                mov = MovimentoCaixa(tipo='S', descricao=f'Conc: {item.descricao}',
                    valor=item.valor, data=item.data or date.today(), documento=item.documento or conta.documento)
                db.session.add(mov)
                log_auditoria(f'Conciliou item #{item_id} com conta pagar #{destino_id}', 'Conciliacao', id)
        elif tipo_destino == 'receber':
            item.conta_receber_id = int(destino_id)
            conta = ContaReceber.query.get(int(destino_id))
            if conta and not conta.recebido:
                conta.recebido = True
                conta.valor_recebido = item.valor
                conta.data_recebimento = item.data or date.today()
                mov = MovimentoCaixa(tipo='E', descricao=f'Conc: {item.descricao}',
                    valor=item.valor, data=item.data or date.today(), documento=item.documento or conta.documento)
                db.session.add(mov)
                log_auditoria(f'Conciliou item #{item_id} com conta receber #{destino_id}', 'Conciliacao', id)

    item.conciliado = True
    c.total_conciliado = c.itens.filter_by(conciliado=True).count()
    db.session.commit()
    flash('Item conciliado!', 'success')
    return redirect(url_for('financeiro.detalhe_conciliacao', id=id))


@bp.route('/financeiro/conciliacao/<int:id>/fechar', methods=['POST'])
@login_required
def fechar_conciliacao(id):
    c = Conciliacao.query.get_or_404(id)
    c.status = 'F'
    db.session.commit()
    flash('Conciliação fechada!', 'success')
    return redirect(url_for('financeiro.lista_conciliacoes'))
