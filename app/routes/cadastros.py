from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.models import Produto, Categoria, Cliente, Fornecedor, Empresa, TabelaPreco, Venda, ItemVenda, ContaReceber
from datetime import datetime, date
from app.audit import log_auditoria

bp = Blueprint('cadastros', __name__)

@bp.context_processor
def inject_now():
    return {'now': datetime.now}

def admin_only(f):
    from functools import wraps
    @wraps(f)
    def wrapped(*a, **kw):
        if current_user.papel != 'admin':
            flash('Acesso restrito ao administrador!', 'danger')
            return redirect(url_for('cadastros.dashboard'))
        return f(*a, **kw)
    return wrapped

def nz(val):
    if val == '' or val is None:
        return None
    try:
        return int(val)
    except ValueError:
        return None

@bp.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'produtos': Produto.query.count(),
        'clientes': Cliente.query.count(),
        'fornecedores': Fornecedor.query.count(),
    }
    return render_template('dashboard.html', stats=stats)

@bp.route('/produtos')
@login_required
@admin_only
def lista_produtos():
    produtos = Produto.query.all()
    return render_template('produtos_lista.html', produtos=produtos)

@bp.route('/produtos/novo', methods=['GET', 'POST'])
@login_required
@admin_only
def novo_produto():
    categorias = Categoria.query.filter_by(ativo=True).all()
    if request.method == 'POST':
        p = Produto(
            codigo_barras=request.form.get('codigo_barras'),
            nome=request.form['nome'],
            descricao=request.form.get('descricao'),
            categoria_id=nz(request.form.get('categoria_id')),
            preco_venda=request.form['preco_venda'],
            preco_custo=request.form.get('preco_custo', 0),
            unidade=request.form.get('unidade', 'UN'),
            ncm=request.form.get('ncm'),
            cest=request.form.get('cest'),
            estoque_minimo=request.form.get('estoque_minimo', 0),
            controla_lote=request.form.get('controla_lote') == 'on',
            dias_validade=nz(request.form.get('dias_validade')),
            peso_balanca=request.form.get('peso_balanca') == 'on',
        )
        db.session.add(p)
        db.session.commit()
        log_auditoria(f'Criou produto: {p.nome}', 'Produto', p.id)
        flash('Produto cadastrado!', 'success')
        return redirect(url_for('cadastros.lista_produtos'))
    return render_template('produtos_form.html', categorias=categorias, produto=None)

@bp.route('/produtos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_only
def editar_produto(id):
    p = Produto.query.get_or_404(id)
    categorias = Categoria.query.filter_by(ativo=True).all()
    if request.method == 'POST':
        from app.audit import model_to_dict
        campos = ['codigo_barras','nome','descricao','preco_venda','preco_custo','unidade','ncm','cest','estoque_minimo']
        ant = model_to_dict(p, campos)
        p.codigo_barras = request.form.get('codigo_barras')
        p.nome = request.form['nome']
        p.descricao = request.form.get('descricao')
        p.categoria_id = nz(request.form.get('categoria_id'))
        p.preco_venda = request.form['preco_venda']
        p.preco_custo = request.form.get('preco_custo', 0)
        p.unidade = request.form.get('unidade', 'UN')
        p.ncm = request.form.get('ncm')
        p.cest = request.form.get('cest')
        p.estoque_minimo = request.form.get('estoque_minimo', 0)
        p.controla_lote = request.form.get('controla_lote') == 'on'
        p.dias_validade = nz(request.form.get('dias_validade'))
        p.peso_balanca = request.form.get('peso_balanca') == 'on'
        db.session.commit()
        novos = model_to_dict(p, campos)
        log_auditoria(f'Editou produto: {p.nome}', 'Produto', p.id, valores_anteriores=ant, valores_novos=novos)
        flash('Produto atualizado!', 'success')
        return redirect(url_for('cadastros.lista_produtos'))
    return render_template('produtos_form.html', categorias=categorias, produto=p)

@bp.route('/clientes')
@login_required
@admin_only
def lista_clientes():
    clientes = Cliente.query.all()
    return render_template('clientes_lista.html', clientes=clientes)

@bp.route('/clientes/novo', methods=['GET', 'POST'])
@login_required
@admin_only
def novo_cliente():
    tabelas = TabelaPreco.query.filter_by(ativo=True).order_by(TabelaPreco.nome).all()
    if request.method == 'POST':
        c = Cliente(
            nome=request.form['nome'],
            cpf_cnpj=request.form.get('cpf_cnpj'),
            rg_ie=request.form.get('rg_ie'),
            email=request.form.get('email'),
            telefone=request.form.get('telefone'),
            celular=request.form.get('celular'),
            cep=request.form.get('cep'),
            endereco=request.form.get('endereco'),
            numero=request.form.get('numero'),
            bairro=request.form.get('bairro'),
            cidade=request.form.get('cidade'),
            uf=request.form.get('uf'),
            limite_credito=request.form.get('limite_credito', 0),
            tabela_preco_id=request.form.get('tabela_preco_id') or None,
        )
        db.session.add(c)
        db.session.commit()
        log_auditoria(f'Criou cliente: {c.nome}', 'Cliente', c.id)
        flash('Cliente cadastrado!', 'success')
        return redirect(url_for('cadastros.lista_clientes'))
    return render_template('clientes_form.html', cliente=None, tabelas=tabelas)

@bp.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_only
def editar_cliente(id):
    c = Cliente.query.get_or_404(id)
    tabelas = TabelaPreco.query.filter_by(ativo=True).order_by(TabelaPreco.nome).all()
    if request.method == 'POST':
        from app.audit import model_to_dict
        campos = ['nome','cpf_cnpj','email','telefone','endereco','cidade','uf','limite_credito']
        ant = model_to_dict(c, campos)
        c.nome = request.form['nome']
        c.cpf_cnpj = request.form.get('cpf_cnpj')
        c.rg_ie = request.form.get('rg_ie')
        c.email = request.form.get('email')
        c.telefone = request.form.get('telefone')
        c.celular = request.form.get('celular')
        c.cep = request.form.get('cep')
        c.endereco = request.form.get('endereco')
        c.numero = request.form.get('numero')
        c.bairro = request.form.get('bairro')
        c.cidade = request.form.get('cidade')
        c.uf = request.form.get('uf')
        c.limite_credito = request.form.get('limite_credito', 0)
        c.tabela_preco_id = request.form.get('tabela_preco_id') or None
        db.session.commit()
        novos = model_to_dict(c, campos)
        log_auditoria(f'Editou cliente: {c.nome}', 'Cliente', c.id, valores_anteriores=ant, valores_novos=novos)
        flash('Cliente atualizado!', 'success')
        return redirect(url_for('cadastros.lista_clientes'))
    return render_template('clientes_form.html', cliente=c, tabelas=tabelas)

@bp.route('/clientes/excluir/<int:id>')
@login_required
@admin_only
def excluir_cliente(id):
    c = Cliente.query.get_or_404(id)
    nome = c.nome
    db.session.delete(c)
    db.session.commit()
    log_auditoria(f'Excluiu cliente: {nome}', 'Cliente', id)
    flash('Cliente excluído!', 'danger')
    return redirect(url_for('cadastros.lista_clientes'))

@bp.route('/fornecedores')
@login_required
@admin_only
def lista_fornecedores():
    fornecedores = Fornecedor.query.all()
    return render_template('fornecedores_lista.html', fornecedores=fornecedores)

@bp.route('/fornecedores/novo', methods=['GET', 'POST'])
@login_required
@admin_only
def novo_fornecedor():
    if request.method == 'POST':
        f = Fornecedor(
            nome=request.form['nome'],
            cpf_cnpj=request.form.get('cpf_cnpj'),
            rg_ie=request.form.get('rg_ie'),
            email=request.form.get('email'),
            telefone=request.form.get('telefone'),
            cep=request.form.get('cep'),
            endereco=request.form.get('endereco'),
            numero=request.form.get('numero'),
            bairro=request.form.get('bairro'),
            cidade=request.form.get('cidade'),
            uf=request.form.get('uf'),
            prazo_entrega=request.form.get('prazo_entrega', 30),
        )
        db.session.add(f)
        db.session.commit()
        log_auditoria(f'Criou fornecedor: {f.nome}', 'Fornecedor', f.id)
        flash('Fornecedor cadastrado!', 'success')
        return redirect(url_for('cadastros.lista_fornecedores'))
    return render_template('fornecedores_form.html', fornecedor=None)

@bp.route('/fornecedores/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_only
def editar_fornecedor(id):
    f = Fornecedor.query.get_or_404(id)
    if request.method == 'POST':
        f.nome = request.form['nome']
        f.cpf_cnpj = request.form.get('cpf_cnpj')
        f.rg_ie = request.form.get('rg_ie')
        f.email = request.form.get('email')
        f.telefone = request.form.get('telefone')
        f.cep = request.form.get('cep')
        f.endereco = request.form.get('endereco')
        f.numero = request.form.get('numero')
        f.bairro = request.form.get('bairro')
        f.cidade = request.form.get('cidade')
        f.uf = request.form.get('uf')
        f.prazo_entrega = request.form.get('prazo_entrega', 30)
        db.session.commit()
        log_auditoria(f'Editou fornecedor: {f.nome}', 'Fornecedor', f.id)
        flash('Fornecedor atualizado!', 'success')
        return redirect(url_for('cadastros.lista_fornecedores'))
    return render_template('fornecedores_form.html', fornecedor=f)


@bp.route('/fornecedores/excluir/<int:id>')
@login_required
@admin_only
def excluir_fornecedor(id):
    f = Fornecedor.query.get_or_404(id)
    nome = f.nome
    db.session.delete(f)
    db.session.commit()
    log_auditoria(f'Excluiu fornecedor: {nome}', 'Fornecedor', id)
    flash('Fornecedor excluído!', 'danger')
    return redirect(url_for('cadastros.lista_fornecedores'))
@bp.route('/produtos/excluir/<int:id>')
@login_required
@admin_only
def excluir_produto(id):
    p = Produto.query.get_or_404(id)
    nome = p.nome
    db.session.delete(p)
    db.session.commit()
    log_auditoria(f'Excluiu produto: {nome}', 'Produto', id)
    flash('Produto excluído!', 'danger')
    return redirect(url_for('cadastros.lista_produtos'))

@bp.route('/categorias')
@login_required
@admin_only
def lista_categorias():
    cats = Categoria.query.all()
    return render_template('categorias_lista.html', categorias=cats)

@bp.route('/categorias/novo', methods=['GET', 'POST'])
@login_required
@admin_only
def nova_categoria():
    if request.method == 'POST':
        c = Categoria(
            nome=request.form['nome'],
            descricao=request.form.get('descricao'),
        )
        db.session.add(c)
        db.session.commit()
        log_auditoria(f'Criou categoria: {c.nome}', 'Categoria', c.id)
        flash('Categoria criada!', 'success')
        return redirect(url_for('cadastros.lista_categorias'))
    return render_template('categorias_form.html', cat=None)

@bp.route('/categorias/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_only
def editar_categoria(id):
    c = Categoria.query.get_or_404(id)
    if request.method == 'POST':
        c.nome = request.form['nome']
        c.descricao = request.form.get('descricao')
        c.ativo = 'ativo' in request.form
        db.session.commit()
        log_auditoria(f'Editou categoria: {c.nome}', 'Categoria', c.id)
        flash('Categoria atualizada!', 'success')
        return redirect(url_for('cadastros.lista_categorias'))
    return render_template('categorias_form.html', cat=c)

@bp.route('/empresa')
@login_required
@admin_only
def lista_empresas():
    empresas = Empresa.query.all()
    return render_template('empresa_lista.html', empresas=empresas)

@bp.route('/empresa/nova', methods=['GET', 'POST'])
@login_required
@admin_only
def nova_empresa():
    if request.method == 'POST':
        e = Empresa(
            razao_social=request.form['razao_social'],
            nome_fantasia=request.form.get('nome_fantasia'),
            cnpj=request.form['cnpj'],
            ie=request.form.get('ie'),
            im=request.form.get('im'),
            cep=request.form.get('cep'),
            endereco=request.form.get('endereco'),
            numero=request.form.get('numero'),
            bairro=request.form.get('bairro'),
            cidade=request.form.get('cidade'),
            uf=request.form.get('uf'),
            telefone=request.form.get('telefone'),
            email=request.form.get('email'),
            regime_tributario=request.form.get('regime_tributario', '3'),
        )
        db.session.add(e)
        db.session.commit()
        log_auditoria(f'Criou empresa: {e.razao_social}', 'Empresa', e.id)
        flash('Empresa cadastrada!', 'success')
        return redirect(url_for('cadastros.lista_empresas'))
    return render_template('empresa_form.html', empresa=None)

@bp.route('/empresa/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_only
def editar_empresa(id):
    e = Empresa.query.get_or_404(id)
    if request.method == 'POST':
        e.razao_social = request.form['razao_social']
        e.nome_fantasia = request.form.get('nome_fantasia')
        e.cnpj = request.form['cnpj']
        e.ie = request.form.get('ie')
        e.im = request.form.get('im')
        e.cep = request.form.get('cep')
        e.endereco = request.form.get('endereco')
        e.numero = request.form.get('numero')
        e.bairro = request.form.get('bairro')
        e.cidade = request.form.get('cidade')
        e.uf = request.form.get('uf')
        e.telefone = request.form.get('telefone')
        e.email = request.form.get('email')
        e.regime_tributario = request.form.get('regime_tributario', '3')
        db.session.commit()
        log_auditoria(f'Editou empresa: {e.razao_social}', 'Empresa', e.id)
        flash('Empresa atualizada!', 'success')
        return redirect(url_for('cadastros.lista_empresas'))
    return render_template('empresa_form.html', empresa=e)


@bp.route('/clientes/ficha/<int:id>')
@login_required
@admin_only
def ficha_cliente(id):
    c = Cliente.query.get_or_404(id)
    vendas = Venda.query.filter_by(cliente_id=c.id).order_by(Venda.created_at.desc()).all()
    total_gasto = sum(float(v.total) for v in vendas if v.status == 'F')
    contas = ContaReceber.query.filter_by(cliente_id=c.id).order_by(ContaReceber.data_vencimento).all()
    saldo_aberto = sum(float(cr.valor) for cr in contas if not cr.recebido)
    return render_template('cliente_ficha.html', cliente=c, vendas=vendas,
                           total_gasto=total_gasto, contas=contas, saldo_aberto=saldo_aberto, hoje=date.today())


@bp.route('/cobranca')
@login_required
@admin_only
def cobranca():
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    return render_template('cobranca.html', clientes=clientes, hoje=date.today())


