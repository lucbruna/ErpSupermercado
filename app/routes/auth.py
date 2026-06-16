from flask import Blueprint, render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import db, _check_rate_limit, _reset_rate_limit, validar_senha
from app.models.models import Usuario, LoginAttempt
from app.audit import log_auditoria
from datetime import datetime

bp = Blueprint('auth', __name__)

MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _esta_bloqueado(login):
    """Verifica se o usuário está bloqueado por muitas tentativas"""
    recente = LoginAttempt.query.filter(
        LoginAttempt.login == login,
        LoginAttempt.sucesso == False,
        LoginAttempt.created_at >= datetime.now().timestamp() - (LOCKOUT_MINUTES * 60)
    ).count()
    return recente >= MAX_ATTEMPTS


def _registrar_tentativa(login, sucesso):
    """Registra tentativa de login para controle de bloqueio"""
    import time
    tentativa = LoginAttempt(
        login=login,
        ip=request.remote_addr or '',
        sucesso=sucesso,
        created_at=int(time.time())
    )
    db.session.add(tentativa)
    db.session.commit()


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login', '').strip()
        senha = request.form.get('senha', '')

        if not login or not senha:
            flash('Informe login e senha!', 'danger')
            return render_template('login.html')

        # Rate limit por IP
        ip_key = f'ip:{request.remote_addr}'
        if not _check_rate_limit(ip_key):
            flash(f'Muitas tentativas deste IP. Aguarde alguns minutos.', 'danger')
            log_auditoria(f'Rate limit IP: {request.remote_addr}', 'Auth')
            return render_template('login.html')

        # Bloqueio por usuário
        if _esta_bloqueado(login):
            flash(f'Usuário bloqueado por muitas tentativas. Aguarde {LOCKOUT_MINUTES} minutos.', 'danger')
            log_auditoria(f'Login bloqueado: {login}', 'Auth')
            return render_template('login.html')

        usuario = Usuario.query.filter_by(login=login, ativo=True).first()
        if usuario and check_password_hash(usuario.senha, senha):
            _registrar_tentativa(login, True)
            _reset_rate_limit(ip_key)
            login_user(usuario)
            usuario.ultimo_login = datetime.now()
            db.session.commit()
            log_auditoria(f'Login: {usuario.nome}', 'Auth', usuario.id)

            if usuario.papel == 'admin':
                return redirect(url_for('cadastros.dashboard'))
            if usuario.setor:
                mod_rota = {
                    'Estoque': 'estoque.movimentacoes',
                    'PDV': 'pdv.index',
                    'Compras': 'cadastros.dashboard',
                    'Financeiro': 'cadastros.dashboard',
                    'Fiscal': 'cadastros.dashboard',
                    'RH': 'cadastros.dashboard',
                }
                return redirect(url_for(mod_rota.get(usuario.setor.nome, 'cadastros.dashboard')))
            return redirect(url_for('cadastros.dashboard'))

        _registrar_tentativa(login, False)
        log_auditoria(f'Tentativa inválida: {login}', 'Auth')
        flash('Login ou senha inválidos', 'danger')

    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    log_auditoria(f'Logout: {current_user.nome}', 'Auth', current_user.id)
    logout_user()
    return redirect(url_for('auth.login'))


@bp.route('/minha_senha', methods=['GET', 'POST'])
@login_required
def minha_senha():
    if request.method == 'POST':
        atual = request.form.get('senha_atual', '')
        nova = request.form.get('nova_senha', '')

        if not check_password_hash(current_user.senha, atual):
            flash('Senha atual incorreta!', 'danger')
            return render_template('minha_senha.html')

        erros = validar_senha(nova)
        if erros:
            for e in erros:
                flash(f'Senha fraca: {e}', 'danger')
            return render_template('minha_senha.html')

        current_user.senha = generate_password_hash(nova)
        db.session.commit()
        log_auditoria('Alterou a própria senha', 'Auth', current_user.id)
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('cadastros.dashboard'))

    return render_template('minha_senha.html')
