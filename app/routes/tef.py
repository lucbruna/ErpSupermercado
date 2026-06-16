from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app import db
from app.models.models import ConfigTEF
from app.tef.cliente import TEFCliente

bp = Blueprint('tef', __name__, url_prefix='/tef')


@bp.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    cfg = ConfigTEF.query.first()
    if not cfg:
        cfg = ConfigTEF(modo_simulado=True, adquirente='simulada')
        db.session.add(cfg)
        db.session.commit()

    if request.method == 'POST':
        cfg.modo_simulado = request.form.get('modo_simulado') == 'on'
        cfg.adquirente = request.form.get('adquirente', 'simulada')
        cfg.caminho_pinpad = request.form.get('caminho_pinpad') or None
        cfg.codigo_loja = request.form.get('codigo_loja') or None
        cfg.codigo_terminal = request.form.get('codigo_terminal', '001')
        cfg.ativo = request.form.get('ativo') == 'on'
        db.session.commit()
        flash('Configuração TEF salva!', 'success')
        return redirect(url_for('tef.config'))

    return render_template('tef_config.html', cfg=cfg)


@bp.route('/pagar', methods=['POST'])
@login_required
def pagar():
    """Endpoint chamado pelo PDV para processar pagamento via TEF."""
    data = request.get_json()
    valor = float(data.get('valor', 0))
    forma = data.get('forma', 'debito')  # debito, credito, credito_parcelado
    parcelas = int(data.get('parcelas', 1))

    if valor <= 0:
        return jsonify({'sucesso': False, 'mensagem': 'Valor inválido'}), 400

    cfg = ConfigTEF.query.first()
    if not cfg or not cfg.ativo:
        return jsonify({'sucesso': False, 'mensagem': 'TEF não configurado'}), 400

    tef = TEFCliente({
        'modo_simulado': cfg.modo_simulado,
        'caminho_pinpad': cfg.caminho_pinpad or '',
        'codigo_loja': cfg.codigo_loja or '',
        'codigo_terminal': cfg.codigo_terminal or '001',
    })

    resultado = tef.processar_pagamento(valor, forma, parcelas)
    return jsonify(resultado)


@bp.route('/cancelar', methods=['POST'])
@login_required
def cancelar():
    data = request.get_json()
    nsu = data.get('nsu', '')
    valor = float(data.get('valor', 0))

    cfg = ConfigTEF.query.first()
    tef = TEFCliente({
        'modo_simulado': cfg.modo_simulado if cfg else True,
    })
    resultado = tef.cancelar_transacao(nsu, valor)
    return jsonify(resultado)
