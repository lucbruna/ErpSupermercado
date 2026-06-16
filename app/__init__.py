import os
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, flash, redirect, url_for, request, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from flask_socketio import SocketIO

socketio = SocketIO()

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# ── Rate limiting simples (memória) ──
_login_attempts = {}

def _check_rate_limit(key, max_attempts=5, window=300):
    now = datetime.now()
    if key in _login_attempts:
        attempts, first = _login_attempts[key]
        if (now - first).total_seconds() > window:
            _login_attempts[key] = [1, now]
            return True
        if attempts >= max_attempts:
            return False
        _login_attempts[key] = [attempts + 1, first]
    else:
        _login_attempts[key] = [1, now]
    return True

def _reset_rate_limit(key):
    _login_attempts.pop(key, None)

# ── Validação de senha forte ──
def validar_senha(senha):
    erros = []
    if len(senha) < 8:
        erros.append('Mínimo 8 caracteres')
    if not re.search(r'[A-Z]', senha):
        erros.append('Pelo menos uma letra maiúscula')
    if not re.search(r'[a-z]', senha):
        erros.append('Pelo menos uma letra minúscula')
    if not re.search(r'[0-9]', senha):
        erros.append('Pelo menos um número')
    if not re.search(r'[^a-zA-Z0-9]', senha):
        erros.append('Pelo menos um caractere especial')
    return erros

# ── Sanitização de entrada ──
def sanitizar(valor, max_len=500):
    if not valor:
        return valor
    import html
    return html.escape(str(valor)[:max_len])

# ── Decorator de módulo ──
def modulo_required(modulo):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if current_user.is_authenticated:
                if current_user.papel == 'admin':
                    return f(*args, **kwargs)
                if current_user.setor and current_user.setor.nome == modulo:
                    return f(*args, **kwargs)
            flash('Acesso negado ao modulo!', 'danger')
            return redirect(url_for('cadastros.dashboard'))
        return wrapped
    return decorator

def create_app():
    app = Flask(__name__)

    # ── Carrega configurações de ambiente ──
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', '')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        f"postgresql://{os.environ.get('DB_USER', 'openpg')}:{os.environ.get('DB_PASS', 'openpgpwd')}"
        f"@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}"
        f"/{os.environ.get('DB_NAME', 'erp_supermercado')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
        seconds=int(os.environ.get('PERMANENT_SESSION_LIFETIME', '3600'))
    )
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload max

    if not app.config['SECRET_KEY']:
        raise RuntimeError('SECRET_KEY não configurada! Defina a variável de ambiente SECRET_KEY.')

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from app.models.models import Usuario
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # ── Middleware de segurança: headers ──
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        return response

    # ── Registro de Blueprints ──
    from app.routes import auth, cadastros, estoque, pdv, usuarios, compras, rh, financeiro, fiscal, precos, relatorios, auditoria, notificacoes, backup, orcamentos, devolucao, imprimir, sped, tef
    app.register_blueprint(auth.bp)
    app.register_blueprint(cadastros.bp)
    app.register_blueprint(estoque.bp)
    app.register_blueprint(pdv.bp)
    app.register_blueprint(usuarios.bp)
    app.register_blueprint(compras.bp)
    app.register_blueprint(rh.bp)
    app.register_blueprint(financeiro.bp)
    app.register_blueprint(fiscal.bp)
    app.register_blueprint(precos.bp)
    app.register_blueprint(relatorios.bp)
    app.register_blueprint(auditoria.bp)
    app.register_blueprint(notificacoes.bp)
    app.register_blueprint(backup.bp)
    app.register_blueprint(orcamentos.bp)
    app.register_blueprint(devolucao.bp)
    app.register_blueprint(imprimir.bp)
    app.register_blueprint(sped.bp)
    app.register_blueprint(tef.bp)

    from app.routes import contabilidade
    app.register_blueprint(contabilidade.bp)
    from app.routes import pix
    app.register_blueprint(pix.bp)
    from app.routes import cotacoes
    app.register_blueprint(cotacoes.bp)
    from app.routes import config_email
    app.register_blueprint(config_email.bp)
    from app.routes import transferencias
    app.register_blueprint(transferencias.bp)
    from app.routes import crm
    app.register_blueprint(crm.bp)
    from app.routes import api
    app.register_blueprint(api.bp)
    from app.routes import csv_import
    app.register_blueprint(csv_import.bp)
    from app.routes import producao
    app.register_blueprint(producao.bp)
    from app.routes import mesas
    app.register_blueprint(mesas.bp)
    from app.routes import cheques
    app.register_blueprint(cheques.bp)
    from app.routes import ativos
    app.register_blueprint(ativos.bp)
    from app.routes import nfse
    app.register_blueprint(nfse.bp)
    from app.routes import config_whatsapp
    app.register_blueprint(config_whatsapp.bp)
    from app.routes import pwa
    app.register_blueprint(pwa.bp)
    from app.routes import nfe
    app.register_blueprint(nfe.bp)
    from app.routes import biometria
    app.register_blueprint(biometria.bp)
    from app.routes import dashboard_real
    app.register_blueprint(dashboard_real.bp)

    from app.socketio_events import init_socketio_events
    init_socketio_events(app)

    @app.context_processor
    def inject_user():
        def has_module(mod):
            if current_user.is_authenticated:
                if current_user.papel == 'admin':
                    return True
                if current_user.setor:
                    return current_user.setor.nome == mod
            return False
        return dict(has_module=has_module, now=datetime.now)

    return app, socketio
