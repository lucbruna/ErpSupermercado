from flask import Blueprint, render_template, request
from flask_login import login_required
from app import db
from app.models.models import LogAuditoria
from datetime import datetime, timedelta
from sqlalchemy import or_

bp = Blueprint('auditoria', __name__, url_prefix='/auditoria')


@bp.route('/')
@login_required
def lista():
    page = request.args.get('page', 1, type=int)
    de = request.args.get('de', '')
    ate = request.args.get('ate', '')
    usuario = request.args.get('usuario', '').strip()
    entidade = request.args.get('entidade', '').strip()
    acao = request.args.get('acao', '').strip()

    q = LogAuditoria.query

    if de:
        try:
            q = q.filter(LogAuditoria.created_at >= datetime.strptime(de, '%Y-%m-%d'))
        except ValueError:
            pass
    if ate:
        try:
            q = q.filter(LogAuditoria.created_at <= datetime.strptime(ate, '%Y-%m-%d') + timedelta(days=1))
        except ValueError:
            pass
    if usuario:
        q = q.filter(LogAuditoria.usuario_nome.ilike(f'%{usuario}%'))
    if entidade:
        q = q.filter(LogAuditoria.entidade.ilike(f'%{entidade}%'))
    if acao:
        q = q.filter(LogAuditoria.acao.ilike(f'%{acao}%'))

    logs = q.order_by(LogAuditoria.created_at.desc()).paginate(page=page, per_page=50)
    return render_template('auditoria_lista.html', logs=logs, de=de, ate=ate, usuario=usuario, entidade=entidade, acao=acao)
