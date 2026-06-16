from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import Funcionario, Cargo, Setor, Ponto, FolhaPagamento, Ferias, Rescisao, Empresa
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

bp = Blueprint('rh', __name__)


@bp.route('/rh')
@login_required
def dashboard():
    stats = {
        'funcionarios': Funcionario.query.filter_by(ativo=True).count(),
        'cargos': Cargo.query.filter_by(ativo=True).count(),
        'folhas_pendentes': FolhaPagamento.query.filter_by(pago=False).count(),
    }
    return render_template('rh_dashboard.html', stats=stats)


@bp.route('/rh/cargos')
@login_required
def lista_cargos():
    cargos = Cargo.query.order_by(Cargo.nome).all()
    return render_template('rh_cargos_lista.html', cargos=cargos)


@bp.route('/rh/cargos/novo', methods=['GET', 'POST'])
@login_required
def novo_cargo():
    if request.method == 'POST':
        c = Cargo(nome=request.form['nome'], descricao=request.form.get('descricao'),
                   salario_base=request.form.get('salario_base', 0))
        db.session.add(c)
        db.session.commit()
        log_auditoria(f'Criou cargo: {c.nome}', 'Cargo', c.id)
        flash(f'Cargo {c.nome} criado!', 'success')
        return redirect(url_for('rh.lista_cargos'))
    return render_template('rh_cargos_form.html', cargo=None)


@bp.route('/rh/cargos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cargo(id):
    c = Cargo.query.get_or_404(id)
    if request.method == 'POST':
        c.nome = request.form['nome']
        c.descricao = request.form.get('descricao')
        c.salario_base = request.form.get('salario_base', 0)
        c.ativo = 'ativo' in request.form
        db.session.commit()
        log_auditoria(f'Editou cargo: {c.nome}', 'Cargo', c.id)
        flash('Cargo atualizado!', 'success')
        return redirect(url_for('rh.lista_cargos'))
    return render_template('rh_cargos_form.html', cargo=c)


@bp.route('/rh/funcionarios')
@login_required
def lista_funcionarios():
    funcionarios = Funcionario.query.order_by(Funcionario.nome).all()
    return render_template('rh_funcionarios_lista.html', funcionarios=funcionarios)


@bp.route('/rh/funcionarios/novo', methods=['GET', 'POST'])
@login_required
def novo_funcionario():
    cargos = Cargo.query.filter_by(ativo=True).order_by(Cargo.nome).all()
    setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome).all()
    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        if Funcionario.query.filter_by(cpf=cpf).first():
            flash('CPF ja cadastrado!', 'danger')
            return render_template('rh_funcionarios_form.html', func=None, cargos=cargos, setores=setores)
        data_admissao = request.form.get('data_admissao')
        f = Funcionario(
            nome=nome, cpf=cpf, rg=request.form.get('rg'),
            ctps=request.form.get('ctps'), pis=request.form.get('pis'),
            data_nascimento=datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d').date() if request.form.get('data_nascimento') else None,
            estado_civil=request.form.get('estado_civil'),
            genero=request.form.get('genero'),
            cep=request.form.get('cep'), endereco=request.form.get('endereco'),
            numero=request.form.get('numero'), bairro=request.form.get('bairro'),
            cidade=request.form.get('cidade'), uf=request.form.get('uf'),
            telefone=request.form.get('telefone'), celular=request.form.get('celular'),
            email=request.form.get('email'),
            cargo_id=request.form.get('cargo_id') or None,
            setor_id=request.form.get('setor_id') or None,
            data_admissao=datetime.strptime(data_admissao, '%Y-%m-%d').date() if data_admissao else None,
            salario_contratual=request.form.get('salario_contratual', 0),
            tipo_salario=request.form.get('tipo_salario', 'M'),
            vale_transporte='vale_transporte' in request.form,
            vale_refeicao='vale_refeicao' in request.form,
            escala=request.form.get('escala', '6x1'),
        )
        db.session.add(f)
        db.session.commit()
        log_auditoria(f'Criou funcionário: {nome}', 'Funcionario', f.id)
        flash(f'Funcionario {nome} cadastrado!', 'success')
        return redirect(url_for('rh.lista_funcionarios'))
    return render_template('rh_funcionarios_form.html', func=None, cargos=cargos, setores=setores)


@bp.route('/rh/funcionarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_funcionario(id):
    f = Funcionario.query.get_or_404(id)
    cargos = Cargo.query.filter_by(ativo=True).order_by(Cargo.nome).all()
    setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome).all()
    if request.method == 'POST':
        from app.audit import model_to_dict
        campos = ['nome','cpf','rg','ctps','pis','endereco','cidade','uf','telefone','email','salario_contratual','tipo_salario','escala']
        ant = model_to_dict(f, campos)
        f.nome = request.form['nome']
        f.cpf = request.form['cpf']
        f.rg = request.form.get('rg')
        f.ctps = request.form.get('ctps')
        f.pis = request.form.get('pis')
        f.data_nascimento = datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d').date() if request.form.get('data_nascimento') else None
        f.estado_civil = request.form.get('estado_civil')
        f.genero = request.form.get('genero')
        f.cep = request.form.get('cep')
        f.endereco = request.form.get('endereco')
        f.numero = request.form.get('numero')
        f.bairro = request.form.get('bairro')
        f.cidade = request.form.get('cidade')
        f.uf = request.form.get('uf')
        f.telefone = request.form.get('telefone')
        f.celular = request.form.get('celular')
        f.email = request.form.get('email')
        f.cargo_id = request.form.get('cargo_id') or None
        f.setor_id = request.form.get('setor_id') or None
        data_admissao = request.form.get('data_admissao')
        f.data_admissao = datetime.strptime(data_admissao, '%Y-%m-%d').date() if data_admissao else None
        f.salario_contratual = request.form.get('salario_contratual', 0)
        f.tipo_salario = request.form.get('tipo_salario', 'M')
        f.vale_transporte = 'vale_transporte' in request.form
        f.vale_refeicao = 'vale_refeicao' in request.form
        f.escala = request.form.get('escala', '6x1')
        f.ativo = 'ativo' in request.form
        db.session.commit()
        novos = model_to_dict(f, campos)
        log_auditoria(f'Editou funcionário: {f.nome}', 'Funcionario', f.id, valores_anteriores=ant, valores_novos=novos)
        flash('Funcionario atualizado!', 'success')
        return redirect(url_for('rh.lista_funcionarios'))
    return render_template('rh_funcionarios_form.html', func=f, cargos=cargos, setores=setores)


@bp.route('/rh/folha')
@login_required
def lista_folhas():
    folhas = FolhaPagamento.query.order_by(FolhaPagamento.competencia.desc(), FolhaPagamento.funcionario_id).all()
    return render_template('rh_folha_lista.html', folhas=folhas)


@bp.route('/rh/folha/gerar', methods=['GET', 'POST'])
@login_required
def gerar_folha():
    funcionarios_atuais = Funcionario.query.filter_by(ativo=True).order_by(Funcionario.nome).all()
    if request.method == 'POST':
        competencia = request.form['competencia']
        for f in funcionarios_atuais:
            existe = FolhaPagamento.query.filter_by(competencia=competencia, funcionario_id=f.id).first()
            if existe:
                continue
            salario = Decimal(str(f.salario_contratual or '0'))
            inss = salario * Decimal('0.08')
            irrf = Decimal('0')
            if salario > Decimal('2112.00'):
                irrf = salario * Decimal('0.075')
            fgts = salario * Decimal('0.08')
            vt = salario * Decimal('0.06') if f.vale_transporte else Decimal('0')
            vr = Decimal('400') if f.vale_refeicao else Decimal('0')
            liquidos = salario + fgts - inss - irrf - vt
            folha = FolhaPagamento(
                competencia=competencia, funcionario_id=f.id,
                salario_base=salario, inss=inss, irrf=irrf, fgts=fgts,
                vale_transporte=vt, vale_refeicao=vr,
                salario_liquido=liquidos
            )
            db.session.add(folha)
        db.session.commit()
        log_auditoria(f'Gerou folha {competencia} para {len(funcionarios_atuais)} funcionários', 'FolhaPagamento')
        flash(f'Folha {competencia} gerada para {len(funcionarios_atuais)} funcionarios!', 'success')
        return redirect(url_for('rh.lista_folhas'))
    return render_template('rh_folha_gerar.html', funcionarios=funcionarios_atuais)


@bp.route('/rh/folha/pagar/<int:id>')
@login_required
def pagar_folha(id):
    folha = FolhaPagamento.query.get_or_404(id)
    folha.pago = True
    folha.status = '02'
    folha.data_pagamento = date.today()
    db.session.commit()
    log_auditoria(f'Pagou folha: {folha.competencia} - {folha.funcionario.nome}', 'FolhaPagamento', folha.id)
    flash('Folha paga!', 'success')
    return redirect(url_for('rh.lista_folhas'))


@bp.route('/rh/ponto')
@login_required
def lista_ponto():
    funcionarios = Funcionario.query.filter_by(ativo=True).order_by(Funcionario.nome).all()
    pontos = Ponto.query.order_by(Ponto.data.desc()).limit(50).all()
    return render_template('rh_ponto_lista.html', pontos=pontos, funcionarios=funcionarios)


@bp.route('/rh/ponto/registrar', methods=['POST'])
@login_required
def registrar_ponto():
    func_id = request.form['funcionario_id']
    data_str = request.form['data']
    entrada1 = request.form.get('entrada1')
    saida1 = request.form.get('saida1')
    entrada2 = request.form.get('entrada2')
    saida2 = request.form.get('saida2')
    data = datetime.strptime(data_str, '%Y-%m-%d').date()
    # fecha ponto anterior se existir
    p = Ponto.query.filter_by(funcionario_id=func_id, data=data).first()
    if not p:
        p = Ponto(funcionario_id=func_id, data=data)
        db.session.add(p)
    if entrada1:
        p.entrada1 = datetime.strptime(entrada1, '%H:%M').time()
    if saida1:
        p.saida1 = datetime.strptime(saida1, '%H:%M').time()
    if entrada2:
        p.entrada2 = datetime.strptime(entrada2, '%H:%M').time()
    if saida2:
        p.saida2 = datetime.strptime(saida2, '%H:%M').time()
    p.faltou = 'faltou' in request.form
    p.justificativa = request.form.get('justificativa')
    db.session.commit()
    log_auditoria(f'Registrou ponto: {p.funcionario.nome} - {data_str}', 'Ponto', p.id)
    flash('Ponto registrado!', 'success')
    return redirect(url_for('rh.lista_ponto'))


# ── eSocial ─────────────────────────────────────────────────────

@bp.route('/rh/esocial')
@login_required
def esocial_index():
    funcionarios = Funcionario.query.filter_by(ativo=True).order_by(Funcionario.nome).all()
    return render_template('rh_esocial.html', funcionarios=funcionarios)


@bp.route('/rh/esocial/gerar/<evento>/<int:funcionario_id>')
@login_required
def esocial_gerar(evento, funcionario_id):
    func = Funcionario.query.get_or_404(funcionario_id)
    empresa = Empresa.query.first()
    if not empresa:
        flash('Cadastre a empresa primeiro!', 'danger')
        return redirect(url_for('rh.esocial_index'))

    from app.esocial.gerador import ESocialGenerator
    gen = ESocialGenerator(empresa, None)

    eventos = {
        's2200': gen.gerar_s2200,
        's2299': gen.gerar_s2299,
    }

    if evento == 's1200':
        folha = FolhaPagamento.query.filter_by(
            funcionario_id=funcionario_id
        ).order_by(FolhaPagamento.competencia.desc()).first()
        if not folha:
            flash('Nenhuma folha encontrada para este funcionário!', 'danger')
            return redirect(url_for('rh.esocial_index'))
        xml = gen.gerar_s1200(func, folha)
    elif evento == 's2299':
        rescisao = Rescisao.query.filter_by(funcionario_id=funcionario_id).first()
        if not rescisao:
            flash('Nenhuma rescisão encontrada!', 'danger')
            return redirect(url_for('rh.esocial_index'))
        xml = gen.gerar_s2299(func, rescisao)
    elif evento == 's2200':
        xml = gen.gerar_s2200(func)
    elif evento == 's1000':
        xml = gen.gerar_s1000()
    else:
        flash('Evento não suportado!', 'danger')
        return redirect(url_for('rh.esocial_index'))

    from flask import Response
    nome_arquivo = f'{evento}_{func.cpf or func.id}_{datetime.now().strftime("%Y%m%d")}.xml'
    return Response(
        xml,
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename={nome_arquivo}'}
    )


@bp.route('/rh/esocial/s1000')
@login_required
def esocial_s1000():
    empresa = Empresa.query.first()
    if not empresa:
        flash('Cadastre a empresa primeiro!', 'danger')
        return redirect(url_for('rh.esocial_index'))
    from app.esocial.gerador import ESocialGenerator
    gen = ESocialGenerator(empresa, None)
    xml = gen.gerar_s1000()
    from flask import Response
    return Response(
        xml,
        mimetype='application/xml',
        headers={'Content-Disposition': f'attachment; filename=S1000_{datetime.now().strftime("%Y%m%d")}.xml'}
    )


# ── CAGED ───────────────────────────────────────────────────────

@bp.route('/rh/caged')
@login_required
def caged_index():
    funcionarios = Funcionario.query.order_by(Funcionario.nome).all()
    rescisoes = Rescisao.query.order_by(Rescisao.created_at.desc()).all()
    return render_template('rh_caged.html', funcionarios=funcionarios, rescisoes=rescisoes)


@bp.route('/rh/caged/gerar_admissao/<int:funcionario_id>')
@login_required
def caged_gerar_admissao(funcionario_id):
    func = Funcionario.query.get_or_404(funcionario_id)
    from app.esocial.gerador import gerar_caged
    linha = gerar_caged(func, '1', func.data_admissao)
    from flask import Response
    return Response(
        linha,
        mimetype='text/plain; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=CAGED_ADM_{func.cpf}_{datetime.now().strftime("%Y%m%d")}.txt'}
    )


@bp.route('/rh/caged/gerar_desligamento/<int:rescisao_id>')
@login_required
def caged_gerar_desligamento(rescisao_id):
    rescisao = Rescisao.query.get_or_404(rescisao_id)
    func = rescisao.funcionario
    from app.esocial.gerador import gerar_caged
    linha = gerar_caged(func, '2', rescisao.data_rescisao)
    from flask import Response
    return Response(
        linha,
        mimetype='text/plain; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=CAGED_DESL_{func.cpf}_{datetime.now().strftime("%Y%m%d")}.txt'}
    )
