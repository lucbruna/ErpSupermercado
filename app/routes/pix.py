from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import PixConfig
from app.audit import log_auditoria

bp = Blueprint('pix', __name__, url_prefix='/pix')


@bp.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    cfg = PixConfig.query.filter_by(ativo=True).first()
    if request.method == 'POST':
        if not cfg:
            cfg = PixConfig()
            db.session.add(cfg)
        cfg.chave_pix = request.form['chave_pix']
        cfg.tipo_chave = request.form.get('tipo_chave', 'cpf')
        cfg.nome_recebedor = request.form['nome_recebedor']
        cfg.cidade_recebedor = request.form['cidade_recebedor']
        cfg.ativo = True
        db.session.commit()
        log_auditoria(f'Configurou PIX: {cfg.chave_pix}', 'PixConfig', cfg.id)
        flash('Configuração PIX salva!', 'success')
        return redirect(url_for('pix.config'))
    return render_template('pix_config.html', cfg=cfg)


@bp.route('/gerar_qrcode', methods=['POST'])
@login_required
def gerar_qrcode():
    data = request.get_json()
    valor = float(data.get('valor', 0))
    cfg = PixConfig.query.filter_by(ativo=True).first()
    if not cfg:
        return jsonify({'erro': 'Configure o PIX primeiro!'}), 400

    from app.pix.gerador import gerar_qrcode_pix
    resultado = gerar_qrcode_pix(
        chave_pix=cfg.chave_pix,
        nome=cfg.nome_recebedor,
        cidade=cfg.cidade_recebedor,
        valor=valor,
    )
    return jsonify(resultado)


@bp.route('/pay/<int:venda_id>', methods=['POST'])
@login_required
def pagamento_pix(venda_id):
    """Registra pagamento via PIX no PDV."""
    from app.models.models import Venda, PagamentoVenda, Caixa
    from decimal import Decimal
    data = request.get_json()
    venda = Venda.query.get_or_404(venda_id)
    valor = Decimal(str(data.get('valor', venda.total)))

    pag = PagamentoVenda(
        venda_id=venda.id, forma_pagamento='PIX',
        valor=valor, troco=0, nsu=data.get('txid', ''),
    )
    db.session.add(pag)

    # Finaliza venda se pagamento cobrir
    total_pago = sum(p.valor for p in venda.pagamentos) + valor
    if total_pago >= venda.total:
        venda.status = 'F'
        caixa = venda.caixa
        caixa.valor_esperado = caixa.valor_esperado + venda.total

    db.session.commit()
    log_auditoria(f'PIX Venda #{venda.numero}: R$ {float(valor):.2f}', 'Venda', venda.id)
    return jsonify({'ok': True, 'venda_id': venda.id})
