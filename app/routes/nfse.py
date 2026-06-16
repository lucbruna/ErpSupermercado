from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import NfseConfig, NfseLote, Cliente, ConfigGeral
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

STATUS_NFSE = {'01': 'Pendente', '02': 'Autorizada', '03': 'Rejeitada', '99': 'Cancelada'}

bp = Blueprint('nfse', __name__, url_prefix='/fiscal/nfse')


@bp.route('/')
@login_required
def dashboard():
    config = NfseConfig.query.first()
    ultimos = NfseLote.query.order_by(NfseLote.id.desc()).limit(10).all()
    return render_template('nfse_dashboard.html', config=config, ultimos=ultimos, status=STATUS_NFSE)


@bp.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    cfg = NfseConfig.query.first()
    if not cfg:
        cfg = NfseConfig()
        db.session.add(cfg)
        db.session.commit()

    if request.method == 'POST':
        cfg.municipio_ibge = request.form.get('municipio_ibge')
        cfg.municipio_nome = request.form.get('municipio_nome')
        cfg.aliquota_padrao = Decimal(request.form.get('aliquota_padrao', '5.00'))
        cfg.item_servico_lista = request.form.get('item_servico_lista', '01.01')
        cfg.cnae = request.form.get('cnae')
        cfg.inscricao_municipal = request.form.get('inscricao_municipal')
        cfg.producao = bool(request.form.get('producao'))
        db.session.commit()
        log_auditoria('Alterou config NFS-e', 'NfseConfig', cfg.id)
        flash('Configuração salva!', 'success')
        return redirect(url_for('nfse.dashboard'))

    return render_template('nfse_config.html', cfg=cfg)


@bp.route('/emitir', methods=['GET', 'POST'])
@login_required
def emitir():
    if request.method == 'POST':
        config = NfseConfig.query.first()
        cliente_id = int(request.form['cliente_id'])
        valor = Decimal(request.form['valor'])
        descricao = request.form.get('descricao', '')
        cliente = Cliente.query.get_or_404(cliente_id)

        numero = NfseLote.query.count() + 1
        municipio = config.municipio_nome if config else ''
        xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<NFSe>
    <numero>{numero}</numero>
    <municipio>{municipio}</municipio>
    <cliente>
        <nome>{cliente.nome}</nome>
        <cpf_cnpj>{cliente.cpf_cnpj}</cpf_cnpj>
    </cliente>
    <valor>{valor:.2f}</valor>
    <descricao>{descricao}</descricao>
    <data_emissao>{date.today().isoformat()}</data_emissao>
</NFSe>'''

        lote = NfseLote(
            numero=numero,
            data_emissao=date.today(),
            cliente_id=cliente.id,
            valor=valor,
            descricao=descricao,
            xml_enviado=xml,
            status='02',
        )
        db.session.add(lote)
        db.session.commit()
        log_auditoria(f'Emitiu NFS-e #{lote.numero}', 'NfseLote', lote.id)
        flash('NFS-e emitida!', 'success')
        return redirect(url_for('nfse.view', id=lote.id))

    config = NfseConfig.query.first()
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    return render_template('nfse_emitir.html', config=config, clientes=clientes)


@bp.route('/<int:id>')
@login_required
def view(id):
    lote = NfseLote.query.get_or_404(id)
    return render_template('nfse_view.html', lote=lote, status=STATUS_NFSE)


@bp.route('/listar')
@login_required
def listar():
    lotes = NfseLote.query.order_by(NfseLote.id.desc()).all()
    return render_template('nfse_lista.html', lotes=lotes, status=STATUS_NFSE)
