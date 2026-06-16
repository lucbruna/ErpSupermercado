from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.models import ConfigGeral
from app.utils.mail import send_email

bp = Blueprint('config_email', __name__, url_prefix='/config/email')


@bp.route('/', methods=['GET', 'POST'])
@login_required
def config():
    if request.method == 'POST':
        for chave in ('smtp_host', 'smtp_port', 'smtp_user', 'smtp_pass', 'smtp_tls', 'from_email', 'from_name'):
            val = request.form.get(chave, '')
            c = ConfigGeral.query.filter_by(modulo='email', chave=chave).first()
            if c:
                c.valor = val
            else:
                db.session.add(ConfigGeral(modulo='email', chave=chave, valor=val))
        db.session.commit()
        flash('Configurações de email salvas!', 'success')

        if request.form.get('testar') == '1':
            from_addr = request.form.get('from_email') or request.form.get('smtp_user', '')
            ok, msg = send_email(from_addr, 'Teste de Email', '<h2>Teste OK</h2><p>Configuração de email funcionando!</p>')
            if ok:
                flash('Email de teste enviado! Verifique sua caixa.', 'success')
            else:
                flash(f'Falha no envio: {msg}', 'danger')

        return redirect(url_for('config_email.config'))
    configs = {c.chave: c.valor for c in ConfigGeral.query.filter_by(modulo='email').all()}
    return render_template('config_email.html', configs=configs)