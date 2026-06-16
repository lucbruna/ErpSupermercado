from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import Cheque, Cliente, Venda
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

STATUS = {'01': 'Em Carteira', '02': 'Depositado', '03': 'Compensado', '04': 'Devolvido', '99': 'Cancelado'}

bp = Blueprint('cheques', __name__, url_prefix='/financeiro/cheques')


@bp.route('/')
@login_required
def lista():
    cheques = Cheque.query.order_by(Cheque.id.desc()).all()
    return render_template('fin_cheques_lista.html', cheques=cheques, status=STATUS)


@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if request.method == 'POST':
        cheque = Cheque(
            cliente_id=int(request.form['cliente_id']) if request.form.get('cliente_id') else None,
            banco=request.form['banco'],
            agencia=request.form['agencia'],
            conta=request.form['conta'],
            numero_cheque=request.form['numero_cheque'],
            valor=Decimal(request.form['valor']),
            data_emissao=datetime.strptime(request.form['data_emissao'], '%Y-%m-%d').date(),
            data_vencimento=datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d').date(),
            venda_id=int(request.form['venda_id']) if request.form.get('venda_id') else None,
            observacao=request.form.get('observacao'),
            status='01',
        )
        db.session.add(cheque)
        db.session.commit()
        log_auditoria(f'Registrou cheque {cheque.numero_cheque}', 'Cheque', cheque.id)
        flash('Cheque registrado!', 'success')
        return redirect(url_for('cheques.lista'))

    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    vendas = Venda.query.order_by(Venda.id.desc()).limit(50).all()
    return render_template('fin_cheques_form.html', cheque=None, clientes=clientes, vendas=vendas)


@bp.route('/<int:id>/depositar', methods=['POST'])
@login_required
def depositar(id):
    cheque = Cheque.query.get_or_404(id)
    cheque.status = '02'
    cheque.data_deposito = date.today()
    db.session.commit()
    log_auditoria(f'Depositou cheque {cheque.numero_cheque}', 'Cheque', cheque.id)
    flash('Cheque depositado!', 'success')
    return redirect(url_for('cheques.lista'))


@bp.route('/<int:id>/compensar', methods=['POST'])
@login_required
def compensar(id):
    cheque = Cheque.query.get_or_404(id)
    cheque.status = '03'
    cheque.data_compensacao = date.today()
    db.session.commit()
    log_auditoria(f'Compensou cheque {cheque.numero_cheque}', 'Cheque', cheque.id)
    flash('Cheque compensado!', 'success')
    return redirect(url_for('cheques.lista'))


@bp.route('/<int:id>/devolver', methods=['POST'])
@login_required
def devolver(id):
    cheque = Cheque.query.get_or_404(id)
    cheque.status = '04'
    cheque.observacao = request.form.get('observacao', cheque.observacao or '')
    db.session.commit()
    log_auditoria(f'Devolveu cheque {cheque.numero_cheque}', 'Cheque', cheque.id)
    flash('Cheque devolvido!', 'success')
    return redirect(url_for('cheques.lista'))


@bp.route('/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar(id):
    cheque = Cheque.query.get_or_404(id)
    cheque.status = '99'
    db.session.commit()
    log_auditoria(f'Cancelou cheque {cheque.numero_cheque}', 'Cheque', cheque.id)
    flash('Cheque cancelado!', 'success')
    return redirect(url_for('cheques.lista'))
