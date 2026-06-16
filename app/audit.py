from flask import request
from flask_login import current_user
from app import db


def log_auditoria(acao, entidade=None, entidade_id=None, valores_anteriores=None, valores_novos=None):
    from app.models.models import LogAuditoria
    log = LogAuditoria(
        usuario_id=current_user.id if current_user.is_authenticated else None,
        usuario_nome=current_user.nome if current_user.is_authenticated else 'Sistema',
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        valores_anteriores=str(valores_anteriores)[:5000] if valores_anteriores else None,
        valores_novos=str(valores_novos)[:5000] if valores_novos else None,
        ip=request.remote_addr if request else None,
    )
    db.session.add(log)


def diff_dict(obj, campos):
    """Retorna (anteriores, novos) como dicts dos campos dados."""
    antes = {c: str(getattr(obj, c, '')) for c in campos}
    return antes, {}  # novos preenchido depois do commit


def model_to_dict(obj, campos):
    """Serializa campos de um modelo para dict."""
    return {c: str(getattr(obj, c, '')) for c in campos}
