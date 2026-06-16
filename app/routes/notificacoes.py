from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from app import db
from app.models.models import Notificacao, Produto, ContaPagar, ContaReceber, Lote
from datetime import date, timedelta, datetime

bp = Blueprint('notificacoes', __name__, url_prefix='/notificacoes')


def gerar_notificacoes():
    hoje = date.today()
    criadas = 0

    # Estoque baixo
    produtos_baixo = Produto.query.filter(
        Produto.ativo == True,
        Produto.estoque_atual <= Produto.estoque_minimo,
        Produto.estoque_minimo > 0
    ).all()
    for p in produtos_baixo:
        existe = Notificacao.query.filter_by(
            tipo='estoque_baixo', entidade='Produto', entidade_id=p.id, lida=False
        ).first()
        if not existe:
            n = Notificacao(
                tipo='estoque_baixo',
                titulo=f'Estoque baixo: {p.nome}',
                mensagem=f'Saldo atual: {float(p.estoque_atual):.2f} | Mínimo: {float(p.estoque_minimo):.2f}',
                entidade='Produto', entidade_id=p.id
            )
            db.session.add(n)
            criadas += 1

    # Contas a pagar vencendo (próximos 7 dias)
    contas = ContaPagar.query.filter(
        ContaPagar.pago == False,
        ContaPagar.data_vencimento.between(hoje, hoje + timedelta(days=7))
    ).all()
    for c in contas:
        existe = Notificacao.query.filter_by(
            tipo='conta_vencendo', entidade='ContaPagar', entidade_id=c.id, lida=False
        ).first()
        if not existe:
            n = Notificacao(
                tipo='conta_vencendo',
                titulo=f'Conta a pagar vencendo: {c.descricao}',
                mensagem=f'Valor: R$ {float(c.valor):.2f} | Vencimento: {c.data_vencimento.strftime("%d/%m/%Y")}',
                entidade='ContaPagar', entidade_id=c.id
            )
            db.session.add(n)
            criadas += 1

    # Contas a receber vencendo (próximos 7 dias)
    contas_r = ContaReceber.query.filter(
        ContaReceber.recebido == False,
        ContaReceber.data_vencimento.between(hoje, hoje + timedelta(days=7))
    ).all()
    for c in contas_r:
        existe = Notificacao.query.filter_by(
            tipo='conta_vencendo', entidade='ContaReceber', entidade_id=c.id, lida=False
        ).first()
        if not existe:
            n = Notificacao(
                tipo='conta_vencendo',
                titulo=f'Conta a receber vencendo: {c.descricao}',
                mensagem=f'Valor: R$ {float(c.valor):.2f} | Vencimento: {c.data_vencimento.strftime("%d/%m/%Y")}',
                entidade='ContaReceber', entidade_id=c.id
            )
            db.session.add(n)
            criadas += 1

    # Lotes próximos ao vencimento (30 dias)
    lotes = Lote.query.filter(
        Lote.ativo == True,
        Lote.data_validade.between(hoje, hoje + timedelta(days=30))
    ).all()
    for l in lotes:
        existe = Notificacao.query.filter_by(
            tipo='lote_vencendo', entidade='Lote', entidade_id=l.id, lida=False
        ).first()
        if not existe:
            n = Notificacao(
                tipo='lote_vencendo',
                titulo=f'Lote vencendo: {l.produto.nome} - {l.codigo}',
                mensagem=f'Validade: {l.data_validade.strftime("%d/%m/%Y")} | Qtd: {float(l.quantidade):.2f}',
                entidade='Lote', entidade_id=l.id
            )
            db.session.add(n)
            criadas += 1

    if criadas > 0:
        db.session.commit()

    return criadas


@bp.route('/')
@login_required
def lista():
    gerar_notificacoes()
    page = request.args.get('page', 1, type=int)
    notificacoes = Notificacao.query.order_by(Notificacao.created_at.desc()).paginate(page=page, per_page=30)
    return render_template('notificacoes_lista.html', notificacoes=notificacoes)


@bp.route('/contar')
@login_required
def contar():
    gerar_notificacoes()
    total = Notificacao.query.filter_by(lida=False).count()
    return jsonify({'total': total})


@bp.route('/marcar_lida/<int:id>')
@login_required
def marcar_lida(id):
    n = Notificacao.query.get_or_404(id)
    n.lida = True
    db.session.commit()
    return jsonify({'ok': True})


@bp.route('/marcar_todas_lidas')
@login_required
def marcar_todas_lidas():
    Notificacao.query.filter_by(lida=False).update({'lida': True})
    db.session.commit()
    return jsonify({'ok': True})
