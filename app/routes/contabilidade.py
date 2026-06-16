from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from app import db
from app.models.models import PlanoContas, LancamentoContabil, Empresa
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

bp = Blueprint('contabilidade', __name__, template_folder='../templates')


@bp.route('/contabilidade')
@login_required
def dashboard():
    total_contas = PlanoContas.query.filter_by(ativo=True).count()
    total_lancamentos = LancamentoContabil.query.count()

    # Balanço simplificado (saldos por grupo)
    from sqlalchemy import func as sqla_func
    grupos = {}
    for g_cod, g_nome in [('01', 'Ativo Circulante'), ('02', 'Ativo Não Circulante'),
                          ('03', 'Passivo Circulante'), ('04', 'Passivo Não Circulante'),
                          ('05', 'Patrimônio Líquido'), ('06', 'Receitas'),
                          ('07', 'Despesas')]:
        contas_grupo = PlanoContas.query.filter_by(grupo=g_cod, ativo=True, nivel=1).all()
        saldo = Decimal('0')
        for c in contas_grupo:
            deb = db.session.query(sqla_func.sum(LancamentoContabil.valor)).filter(
                LancamentoContabil.debito_id == c.id).scalar() or 0
            cred = db.session.query(sqla_func.sum(LancamentoContabil.valor)).filter(
                LancamentoContabil.credito_id == c.id).scalar() or 0
            saldo_conta = Decimal(str(deb)) - Decimal(str(cred))
            if c.natureza == 'C':
                saldo_conta = -saldo_conta
            saldo += saldo_conta
        grupos[g_nome] = float(saldo)

    return render_template('contabilidade_dashboard.html',
                           total_contas=total_contas,
                           total_lancamentos=total_lancamentos,
                           grupos=grupos)


# ── Plano de Contas ────────────────────────────────────────────

@bp.route('/contabilidade/plano-contas')
@login_required
def plano_contas():
    contas = PlanoContas.query.order_by(PlanoContas.codigo).all()
    return render_template('contabilidade_plano_contas.html', contas=contas)


@bp.route('/contabilidade/plano-contas/seed')
@login_required
def plano_contas_seed():
    from app.contabilidade.seed import seed_plano_contas
    qtd = seed_plano_contas()
    if qtd:
        flash(f'{qtd} contas padrão criadas!', 'success')
    else:
        flash('Plano de contas já populado.', 'info')
    return redirect(url_for('contabilidade.plano_contas'))


@bp.route('/contabilidade/plano-contas/novo', methods=['GET', 'POST'])
@login_required
def plano_contas_novo():
    contas_pai = PlanoContas.query.filter(PlanoContas.nivel < 3, PlanoContas.ativo == True).order_by(PlanoContas.codigo).all()
    if request.method == 'POST':
        conta = PlanoContas(
            codigo=request.form['codigo'],
            descricao=request.form['descricao'],
            tipo=request.form['tipo'],
            nivel=int(request.form.get('nivel', 1)),
            conta_pai_id=request.form.get('conta_pai_id') or None,
            natureza=request.form['natureza'],
            grupo=request.form.get('grupo'),
        )
        db.session.add(conta)
        db.session.commit()
        log_auditoria(f'Criou conta contábil: {conta.codigo} - {conta.descricao}', 'Contabilidade', conta.id)
        flash('Conta contábil criada!', 'success')
        return redirect(url_for('contabilidade.plano_contas'))
    return render_template('contabilidade_plano_contas_form.html', contas_pai=contas_pai, conta=None)


@bp.route('/contabilidade/plano-contas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def plano_contas_editar(id):
    conta = PlanoContas.query.get_or_404(id)
    contas_pai = PlanoContas.query.filter(PlanoContas.id != id, PlanoContas.ativo == True).order_by(PlanoContas.codigo).all()
    if request.method == 'POST':
        conta.codigo = request.form['codigo']
        conta.descricao = request.form['descricao']
        conta.tipo = request.form['tipo']
        conta.nivel = int(request.form.get('nivel', 1))
        conta.conta_pai_id = request.form.get('conta_pai_id') or None
        conta.natureza = request.form['natureza']
        conta.grupo = request.form.get('grupo')
        db.session.commit()
        log_auditoria(f'Editou conta contábil: {conta.codigo} - {conta.descricao}', 'Contabilidade', conta.id)
        flash('Conta contábil atualizada!', 'success')
        return redirect(url_for('contabilidade.plano_contas'))
    return render_template('contabilidade_plano_contas_form.html', contas_pai=contas_pai, conta=conta)


# ── Lançamentos Contábeis ──────────────────────────────────────

@bp.route('/contabilidade/lancamentos')
@login_required
def lancamentos():
    lancs = LancamentoContabil.query.order_by(LancamentoContabil.data.desc(), LancamentoContabil.id.desc()).all()
    return render_template('contabilidade_lancamentos.html', lancamentos=lancs)


@bp.route('/contabilidade/lancamentos/novo', methods=['GET', 'POST'])
@login_required
def lancamentos_novo():
    contas = PlanoContas.query.filter_by(ativo=True, nivel=1).order_by(PlanoContas.codigo).all()
    if request.method == 'POST':
        lanc = LancamentoContabil(
            data=datetime.strptime(request.form['data'], '%Y-%m-%d').date(),
            historico=request.form['historico'],
            valor=Decimal(str(request.form['valor'])),
            debito_id=request.form['debito_id'],
            credito_id=request.form['credito_id'],
            documento=request.form.get('documento'),
            lote=request.form.get('lote'),
            usuario_id=current_user.id,
        )
        db.session.add(lanc)
        db.session.commit()
        log_auditoria(f'Lançamento contábil: {lanc.historico[:50]}', 'Contabilidade', lanc.id)
        flash('Lançamento contábil registrado!', 'success')
        return redirect(url_for('contabilidade.lancamentos'))
    return render_template('contabilidade_lancamentos_form.html', contas=contas, lancamento=None)


# ── ECD (SPED Contábil) ────────────────────────────────────────

@bp.route('/contabilidade/ecd', methods=['GET', 'POST'])
@login_required
def ecd_gerar():
    if request.method == 'POST':
        empresa = Empresa.query.first()
        if not empresa:
            flash('Cadastre a empresa primeiro!', 'danger')
            return redirect(url_for('contabilidade.dashboard'))
        data_ini = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date()
        data_fim = datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date()
        from app.contabilidade.ecd import ECDGenerator
        gen = ECDGenerator(empresa, data_ini, data_fim)
        conteudo = gen.gerar()
        nome_arquivo = f'ECD_{empresa.cnpj or "000"}_{data_ini.strftime("%Y%m%d")}_{data_fim.strftime("%Y%m%d")}.txt'
        return Response(conteudo, mimetype='text/plain; charset=utf-8',
                        headers={'Content-Disposition': f'attachment; filename={nome_arquivo}'})
    ano_atual = date.today().year
    return render_template('contabilidade_ecd.html', ano_inicio=f'{ano_atual}-01-01', ano_fim=f'{ano_atual}-12-31')


# ── ECF ─────────────────────────────────────────────────────────

@bp.route('/contabilidade/ecf', methods=['GET', 'POST'])
@login_required
def ecf_gerar():
    if request.method == 'POST':
        empresa = Empresa.query.first()
        if not empresa:
            flash('Cadastre a empresa primeiro!', 'danger')
            return redirect(url_for('contabilidade.dashboard'))
        data_ini = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date()
        data_fim = datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date()
        from app.contabilidade.ecf import ECFGenerator
        gen = ECFGenerator(empresa, data_ini, data_fim)
        conteudo = gen.gerar()
        nome_arquivo = f'ECF_{empresa.cnpj or "000"}_{data_ini.strftime("%Y%m%d")}_{data_fim.strftime("%Y%m%d")}.txt'
        return Response(conteudo, mimetype='text/plain; charset=utf-8',
                        headers={'Content-Disposition': f'attachment; filename={nome_arquivo}'})
    ano_atual = date.today().year
    return render_template('contabilidade_ecf.html', ano_inicio=f'{ano_atual}-01-01', ano_fim=f'{ano_atual}-12-31')