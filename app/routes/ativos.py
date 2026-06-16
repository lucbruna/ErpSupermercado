from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import Ativo
from datetime import date, datetime
from decimal import Decimal
from app.audit import log_auditoria

bp = Blueprint('ativos', __name__, url_prefix='/ativos')


@bp.route('/')
@login_required
def lista():
    ativos = Ativo.query.order_by(Ativo.nome).all()
    return render_template('ativos_lista.html', ativos=ativos)


@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if request.method == 'POST':
        ativo = Ativo(
            nome=request.form['nome'],
            tipo=request.form.get('tipo'),
            patrimonio=request.form.get('patrimonio'),
            valor_aquisicao=Decimal(request.form.get('valor_aquisicao', '0')),
            data_aquisicao=datetime.strptime(request.form['data_aquisicao'], '%Y-%m-%d').date() if request.form.get('data_aquisicao') else None,
            vida_util=int(request.form['vida_util']) if request.form.get('vida_util') else None,
            observacao=request.form.get('observacao'),
        )
        db.session.add(ativo)
        db.session.commit()
        log_auditoria(f'Criou ativo: {ativo.nome}', 'Ativo', ativo.id)
        flash('Ativo cadastrado!', 'success')
        return redirect(url_for('ativos.lista'))
    return render_template('ativos_form.html', ativo=None)


@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    ativo = Ativo.query.get_or_404(id)
    if request.method == 'POST':
        ativo.nome = request.form['nome']
        ativo.tipo = request.form.get('tipo')
        ativo.patrimonio = request.form.get('patrimonio')
        ativo.valor_aquisicao = Decimal(request.form.get('valor_aquisicao', '0'))
        ativo.data_aquisicao = datetime.strptime(request.form['data_aquisicao'], '%Y-%m-%d').date() if request.form.get('data_aquisicao') else None
        ativo.vida_util = int(request.form['vida_util']) if request.form.get('vida_util') else None
        ativo.observacao = request.form.get('observacao')
        db.session.commit()
        log_auditoria(f'Editou ativo: {ativo.nome}', 'Ativo', ativo.id)
        flash('Ativo atualizado!', 'success')
        return redirect(url_for('ativos.lista'))
    return render_template('ativos_form.html', ativo=ativo)


@bp.route('/<int:id>/desativar', methods=['POST'])
@login_required
def desativar(id):
    ativo = Ativo.query.get_or_404(id)
    ativo.ativo = False
    db.session.commit()
    log_auditoria(f'Desativou ativo: {ativo.nome}', 'Ativo', ativo.id)
    flash('Ativo desativado!', 'success')
    return redirect(url_for('ativos.lista'))
