from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import date, datetime
from app import db
from app.models.models import Cliente, FidelidadeResgate, MetaVendedor, Usuario, Venda, ConfigGeral
from app.audit import log_auditoria

bp = Blueprint('crm', __name__, url_prefix='/crm')


@bp.route('/')
@login_required
def dashboard():
    total_clientes = Cliente.query.filter_by(ativo=True).count()
    total_pontos = db.session.query(func.sum(Cliente.pontos_fidelidade)).filter_by(ativo=True).scalar() or 0
    resgates_recentes = FidelidadeResgate.query.order_by(FidelidadeResgate.created_at.desc()).limit(10).all()
    return render_template('crm_dashboard.html', total_clientes=total_clientes, total_pontos=total_pontos, resgates_recentes=resgates_recentes)


@bp.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    if request.method == 'POST':
        for chave in ('valor_pontos', 'pontos_por_real'):
            val = request.form.get(chave, '0')
            c = ConfigGeral.query.filter_by(modulo='fidelidade', chave=chave).first()
            if c:
                c.valor = val
            else:
                db.session.add(ConfigGeral(modulo='fidelidade', chave=chave, valor=val))
        db.session.commit()
        flash('Configurações de fidelidade salvas!', 'success')
        return redirect(url_for('crm.config'))
    configs = {c.chave: c.valor for c in ConfigGeral.query.filter_by(modulo='fidelidade').all()}
    return render_template('crm_config.html', configs=configs)


@bp.route('/pontos/<int:cliente_id>/adicionar', methods=['POST'])
@login_required
def adicionar_pontos(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    pontos = request.form.get('pontos', type=int)
    motivo = request.form.get('motivo', '')
    if not pontos or pontos <= 0:
        flash('Quantidade de pontos inválida!', 'danger')
        return redirect(url_for('crm.clientes'))
    cliente.pontos_fidelidade = (cliente.pontos_fidelidade or 0) + pontos
    db.session.commit()
    log_auditoria(f'Adicionou {pontos} pontos ao cliente {cliente.nome}. Motivo: {motivo}', 'Cliente', cliente.id)
    flash(f'{pontos} pontos adicionados a {cliente.nome}!', 'success')
    return redirect(url_for('crm.clientes'))


@bp.route('/pontos/resgatar', methods=['POST'])
@login_required
def resgatar_pontos():
    data = request.get_json()
    if not data:
        return jsonify(ok=False, erro='JSON inválido'), 400
    cliente_id = data.get('cliente_id')
    venda_id = data.get('venda_id')
    pontos = data.get('pontos', type=int)
    if not all([cliente_id, venda_id, pontos]):
        return jsonify(ok=False, erro='Dados incompletos'), 400
    config_valor = ConfigGeral.query.filter_by(modulo='fidelidade', chave='valor_pontos').first()
    valor_ponto = float(config_valor.valor) if config_valor and config_valor.valor else 0.01
    cliente = Cliente.query.get(cliente_id)
    if not cliente:
        return jsonify(ok=False, erro='Cliente não encontrado'), 404
    if (cliente.pontos_fidelidade or 0) < pontos:
        return jsonify(ok=False, erro='Pontos insuficientes'), 400
    valor_desconto = round(pontos * valor_ponto, 2)
    fidelidade_resgate = FidelidadeResgate(
        cliente_id=cliente_id,
        pontos=pontos,
        valor_desconto=valor_desconto,
        venda_id=venda_id
    )
    cliente.pontos_fidelidade -= pontos
    db.session.add(fidelidade_resgate)
    db.session.commit()
    log_auditoria(f'Resgate de {pontos} pontos (R$ {valor_desconto}) do cliente {cliente.nome}', 'FidelidadeResgate', fidelidade_resgate.id)
    return jsonify(ok=True, desconto=valor_desconto)


@bp.route('/clientes')
@login_required
def clientes():
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    return render_template('crm_clientes.html', clientes=clientes)


@bp.route('/metas')
@login_required
def metas():
    metas = MetaVendedor.query.join(Usuario).order_by(MetaVendedor.ano.desc(), MetaVendedor.mes.desc()).all()
    return render_template('crm_metas_lista.html', metas=metas)


@bp.route('/metas/nova', methods=['GET', 'POST'])
@login_required
def metas_nova():
    if request.method == 'POST':
        usuario_id = request.form.get('usuario_id', type=int)
        mes = request.form.get('mes', type=int)
        ano = request.form.get('ano', type=int)
        valor_meta = request.form.get('valor_meta', type=float)
        comissao_percentual = request.form.get('comissao_percentual', type=float) or 0
        comissao_fixa = request.form.get('comissao_fixa', type=float) or 0
        if not all([usuario_id, mes, ano, valor_meta]):
            flash('Preencha todos os campos obrigatórios!', 'danger')
            return redirect(url_for('crm.metas_nova'))
        meta = MetaVendedor(
            usuario_id=usuario_id,
            mes=mes,
            ano=ano,
            valor_meta=valor_meta,
            comissao_percentual=comissao_percentual,
            comissao_fixa=comissao_fixa
        )
        db.session.add(meta)
        db.session.commit()
        log_auditoria(f'Criou meta para usuário {usuario_id}: {mes}/{ano} - R$ {valor_meta}', 'MetaVendedor', meta.id)
        flash('Meta criada com sucesso!', 'success')
        return redirect(url_for('crm.metas'))
    vendedores = Usuario.query.order_by(Usuario.nome).all()
    return render_template('crm_metas_form.html', vendedores=vendedores)


@bp.route('/metas/calcular')
@login_required
def metas_calcular():
    hoje = date.today()
    mes = hoje.month
    ano = hoje.year
    metas = MetaVendedor.query.filter_by(mes=mes, ano=ano).all()
    resultados = []
    for meta in metas:
        total_vendas = db.session.query(func.coalesce(func.sum(Venda.total), 0)).filter(
            Venda.usuario_id == meta.usuario_id,
            Venda.status == 'F',
            func.extract('month', Venda.created_at) == mes,
            func.extract('year', Venda.created_at) == ano
        ).scalar()
        meta.atingido = float(total_vendas)
        db.session.commit()
        resultados.append({
            'meta': meta,
            'total_vendas': float(total_vendas),
            'atingiu': float(total_vendas) >= float(meta.valor_meta)
        })
    flash(f'{len(resultados)} metas calculadas para {mes}/{ano}!', 'success')
    return render_template('crm_metas_calcular.html', resultados=resultados, mes=mes, ano=ano)
