from flask import request
from flask_socketio import emit, join_room, leave_room
from app import socketio
from app.models.models import Venda, MovimentoCaixa
from datetime import date, datetime, timedelta
from sqlalchemy import func


@socketio.on('connect')
def handle_connect():
    emit('status', {'msg': 'Conectado'})


@socketio.on('join_dashboard')
def join_dashboard(data):
    room = data.get('room', 'dashboard')
    join_room(room)
    emit('status', {'msg': f'Entrou em {room}'})


@socketio.on('leave_dashboard')
def leave_dashboard(data):
    room = data.get('room', 'dashboard')
    leave_room(room)


def emitir_dados(room='dashboard'):
    hoje = date.today()
    mes_atual = hoje.replace(day=1)

    vendas_hoje = db_session_query(
        Venda.query.filter(Venda.status == 'F', func.date(Venda.created_at) == hoje).count()
    )
    total_hoje = db_session_query(
        db_session_sum(Venda.total, Venda.status == 'F', func.date(Venda.created_at) == hoje)
    )

    total_mes = db_session_query(
        db_session_sum(Venda.total, Venda.status == 'F', func.date(Venda.created_at) >= mes_atual)
    )
    qtd_mes = db_session_query(
        Venda.query.filter(Venda.status == 'F', func.date(Venda.created_at) >= mes_atual).count()
    )
    ticket_medio = round(total_mes / qtd_mes, 2) if qtd_mes else 0

    socketio.emit('dashboard_update', {
        'vendas_hoje': vendas_hoje,
        'total_hoje': round(float(total_hoje), 2),
        'total_mes': round(float(total_mes), 2),
        'qtd_mes': qtd_mes,
        'ticket_medio': ticket_medio,
        'timestamp': datetime.now().strftime('%H:%M:%S'),
    }, room=room)


def db_session_query(query):
    from app import db
    return db.session.execute(query).scalar() if hasattr(query, 'statement') else query


def db_session_sum(field, *filters):
    from app import db
    return db.session.query(func.sum(field)).filter(*filters).scalar() or 0


def init_socketio_events(app):
    pass
