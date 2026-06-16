import csv
import io
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
from flask_login import login_required
from app import db
from app.models.models import Produto, Cliente

bp = Blueprint('csv_import', __name__, url_prefix='/csv')


@bp.route('/')
@login_required
def index():
    return render_template('csv_import.html')


@bp.route('/produtos', methods=['POST'])
@login_required
def importar_produtos():
    if 'file' not in request.files:
        flash('Nenhum arquivo enviado!', 'danger')
        return redirect(url_for('csv_import.index'))

    file = request.files['file']
    if not file.filename:
        flash('Arquivo sem nome!', 'danger')
        return redirect(url_for('csv_import.index'))

    stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
    reader = csv.DictReader(stream, delimiter=request.form.get('delimitador', ','))

    criados = 0
    atualizados = 0
    erros = 0

    for row in reader:
        codigo = row.get('codigo', '').strip()
        nome = row.get('nome', '').strip()

        if not nome or not codigo:
            erros += 1
            continue

        try:
            produto = Produto.query.filter_by(codigo_barras=codigo).first()

            if produto:
                produto.nome = nome
                atualizados += 1
            else:
                produto = Produto(
                    codigo_barras=codigo,
                    nome=nome,
                    ativo=True,
                )
                db.session.add(produto)
                criados += 1

            if row.get('codigo_barras'):
                produto.codigo_barras = row['codigo_barras'].strip()
            if row.get('preco_venda'):
                produto.preco_venda = row['preco_venda'].strip().replace(',', '.')
            if row.get('preco_custo'):
                produto.preco_custo = row['preco_custo'].strip().replace(',', '.')
            if row.get('estoque_atual'):
                produto.estoque_atual = row['estoque_atual'].strip().replace(',', '.')
            if row.get('estoque_minimo'):
                produto.estoque_minimo = row['estoque_minimo'].strip().replace(',', '.')
            if row.get('unidade'):
                produto.unidade = row['unidade'].strip()

        except Exception:
            db.session.rollback()
            erros += 1
            continue

    db.session.commit()

    msg = f'Produtos: {criados} criados, {atualizados} atualizados'
    if erros:
        msg += f', {erros} erros'
    flash(msg, 'success' if erros == 0 else 'warning')

    return redirect(url_for('csv_import.index'))


@bp.route('/clientes', methods=['POST'])
@login_required
def importar_clientes():
    if 'file' not in request.files:
        flash('Nenhum arquivo enviado!', 'danger')
        return redirect(url_for('csv_import.index'))

    file = request.files['file']
    if not file.filename:
        flash('Arquivo sem nome!', 'danger')
        return redirect(url_for('csv_import.index'))

    stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
    reader = csv.DictReader(stream, delimiter=request.form.get('delimitador', ','))

    criados = 0
    atualizados = 0
    erros = 0

    for row in reader:
        cpf_cnpj = row.get('cpf_cnpj', '').strip()
        nome = row.get('nome', '').strip()

        if not nome:
            erros += 1
            continue

        try:
            cliente = None
            if cpf_cnpj:
                cliente = Cliente.query.filter_by(cpf_cnpj=cpf_cnpj).first()

            if cliente:
                cliente.nome = nome
                atualizados += 1
            else:
                cliente = Cliente(
                    nome=nome,
                    cpf_cnpj=cpf_cnpj or None,
                    ativo=True,
                )
                db.session.add(cliente)
                criados += 1

            if row.get('telefone'):
                cliente.telefone = row['telefone'].strip()
            if row.get('celular'):
                cliente.celular = row['celular'].strip()
            if row.get('email'):
                cliente.email = row['email'].strip()
            if row.get('endereco'):
                cliente.endereco = row['endereco'].strip()
            if row.get('cidade'):
                cliente.cidade = row['cidade'].strip()
            if row.get('uf'):
                cliente.uf = row['uf'].strip()

        except Exception:
            db.session.rollback()
            erros += 1
            continue

    db.session.commit()

    msg = f'Clientes: {criados} criados, {atualizados} atualizados'
    if erros:
        msg += f', {erros} erros'
    flash(msg, 'success' if erros == 0 else 'warning')

    return redirect(url_for('csv_import.index'))


@bp.route('/produtos/export')
@login_required
def exportar_produtos():
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nome', 'codigo', 'codigo_barras', 'preco_venda', 'preco_custo',
                     'estoque_atual', 'estoque_minimo', 'unidade'])

    for p in produtos:
        writer.writerow([
            p.nome,
            p.codigo_barras or '',
            p.codigo_barras or '',
            str(p.preco_venda or '0').replace('.', ','),
            str(p.preco_custo or '0').replace('.', ','),
            str(p.estoque_atual or '0').replace('.', ','),
            str(p.estoque_minimo or '0').replace('.', ','),
            p.unidade or 'UN',
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8-sig',
        headers={'Content-Disposition': 'attachment; filename=produtos.csv'},
    )


@bp.route('/clientes/export')
@login_required
def exportar_clientes():
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nome', 'cpf_cnpj', 'telefone', 'celular', 'email',
                     'endereco', 'cidade', 'uf'])

    for c in clientes:
        writer.writerow([
            c.nome,
            c.cpf_cnpj or '',
            c.telefone or '',
            c.celular or '',
            c.email or '',
            c.endereco or '',
            c.cidade or '',
            c.uf or '',
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8-sig',
        headers={'Content-Disposition': 'attachment; filename=clientes.csv'},
    )
