from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import TabelaPreco, ItemTabelaPreco, Produto, Cliente
from datetime import datetime, date
from app.audit import log_auditoria

bp = Blueprint('precos', __name__, url_prefix='/precos')


@bp.route('/')
@login_required
def lista():
    if current_user.papel != 'admin':
        flash('Acesso restrito!', 'danger')
        return redirect(url_for('cadastros.dashboard'))
    tabelas = TabelaPreco.query.order_by(TabelaPreco.nome).all()
    return render_template('precos_lista.html', tabelas=tabelas, hoje=date.today())


@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if current_user.papel != 'admin':
        flash('Acesso restrito!', 'danger')
        return redirect(url_for('cadastros.dashboard'))
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        nome = request.form['nome']
        data_ini = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        t = TabelaPreco(
            nome=nome,
            data_inicio=datetime.strptime(data_ini, '%Y-%m-%d').date() if data_ini else None,
            data_fim=datetime.strptime(data_fim, '%Y-%m-%d').date() if data_fim else None,
        )
        db.session.add(t)
        db.session.flush()
        produtos_ids = request.form.getlist('produto_id[]')
        precos = request.form.getlist('preco[]')
        qtde_min = request.form.getlist('quantidade_min[]')
        for pid, p, q in zip(produtos_ids, precos, qtde_min):
            if not pid:
                continue
            item = ItemTabelaPreco(
                tabela_id=t.id, produto_id=int(pid),
                preco=float(p or 0), quantidade_min=float(q or 0)
            )
            db.session.add(item)
        db.session.commit()
        log_auditoria(f'Criou tabela de preço: {nome}', 'TabelaPreco', t.id)
        flash(f'Tabela "{nome}" criada!', 'success')
        return redirect(url_for('precos.lista'))
    return render_template('precos_form.html', tabela=None, produtos=produtos)


@bp.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    if current_user.papel != 'admin':
        flash('Acesso restrito!', 'danger')
        return redirect(url_for('cadastros.dashboard'))
    t = TabelaPreco.query.get_or_404(id)
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    if request.method == 'POST':
        t.nome = request.form['nome']
        data_ini = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        t.data_inicio = datetime.strptime(data_ini, '%Y-%m-%d').date() if data_ini else None
        t.data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date() if data_fim else None
        t.ativo = 'ativo' in request.form
        ItemTabelaPreco.query.filter_by(tabela_id=t.id).delete()
        db.session.flush()
        produtos_ids = request.form.getlist('produto_id[]')
        precos = request.form.getlist('preco[]')
        qtde_min = request.form.getlist('quantidade_min[]')
        for pid, p, q in zip(produtos_ids, precos, qtde_min):
            if not pid:
                continue
            item = ItemTabelaPreco(
                tabela_id=t.id, produto_id=int(pid),
                preco=float(p or 0), quantidade_min=float(q or 0)
            )
            db.session.add(item)
        db.session.commit()
        log_auditoria(f'Editou tabela de preço: {t.nome}', 'TabelaPreco', t.id)
        flash(f'Tabela "{t.nome}" atualizada!', 'success')
        return redirect(url_for('precos.lista'))
    return render_template('precos_form.html', tabela=t, produtos=produtos)


@bp.route('/visualizar/<int:id>')
@login_required
def visualizar(id):
    if current_user.papel != 'admin':
        flash('Acesso restrito!', 'danger')
        return redirect(url_for('cadastros.dashboard'))
    t = TabelaPreco.query.get_or_404(id)
    return render_template('precos_view.html', tabela=t, hoje=date.today())


@bp.route('/preco_produto/<int:tabela_id>/<int:produto_id>')
@login_required
def preco_produto(tabela_id, produto_id):
    item = ItemTabelaPreco.query.filter_by(
        tabela_id=tabela_id, produto_id=produto_id
    ).order_by(ItemTabelaPreco.quantidade_min).first()
    if item:
        return jsonify({'preco': float(item.preco)})
    prod = Produto.query.get(produto_id)
    return jsonify({'preco': float(prod.preco_venda) if prod else 0})
