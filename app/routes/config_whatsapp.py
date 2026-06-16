from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models.models import ConfigGeral
from app.utils.whatsapp import send_whatsapp

bp = Blueprint('config_whatsapp', __name__, url_prefix='/config/whatsapp')


@bp.route('/', methods=['GET', 'POST'])
@login_required
def config():
    if request.method == 'POST':
        for chave in ('api_url', 'api_key', 'instance'):
            val = request.form.get(chave, '')
            c = ConfigGeral.query.filter_by(modulo='whatsapp', chave=chave).first()
            if c:
                c.valor = val
            else:
                db.session.add(ConfigGeral(modulo='whatsapp', chave=chave, valor=val))
        db.session.commit()
        flash('Configurações de WhatsApp salvas!', 'success')

        if request.form.get('testar') == '1':
            telefone = request.form.get('teste_telefone', '').strip()
            if telefone:
                ok, msg = send_whatsapp(telefone, 'Teste do sistema ERP Supermercado. Configuração OK!')
                if ok:
                    flash('Mensagem de teste enviada!', 'success')
                else:
                    flash(f'Falha: {msg}', 'danger')
            else:
                flash('Informe um telefone para teste.', 'warning')

        return redirect(url_for('config_whatsapp.config'))
    configs = {c.chave: c.valor for c in ConfigGeral.query.filter_by(modulo='whatsapp').all()}
    return render_template('config_whatsapp.html', configs=configs)