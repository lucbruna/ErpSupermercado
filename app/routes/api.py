from flask import Blueprint, jsonify, request
from flask_login import login_required, login_user
from werkzeug.security import check_password_hash
from app import db
from app.models.models import Produto, Cliente, Usuario, Venda
from datetime import date

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'ok': False, 'error': 'Informe usuário e senha'}), 401

    usuario = Usuario.query.filter_by(login=username, ativo=True).first()
    if usuario and check_password_hash(usuario.senha, password):
        login_user(usuario)
        return jsonify({
            'ok': True,
            'usuario': {'id': usuario.id, 'nome': usuario.nome, 'papel': usuario.papel}
        })

    return jsonify({'ok': False, 'error': 'Usuário ou senha inválidos'}), 401


@bp.route('/produtos')
@login_required
def listar_produtos():
    produtos = Produto.query.filter_by(ativo=True).order_by(Produto.nome).all()
    return jsonify([{
        'id': p.id,
        'nome': p.nome,
        'codigo': p.codigo_barras,
        'preco_venda': float(p.preco_venda) if p.preco_venda else 0,
        'estoque_atual': float(p.estoque_atual) if p.estoque_atual else 0,
    } for p in produtos])


@bp.route('/produtos/busca')
@login_required
def buscar_produtos():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])

    produtos = Produto.query.filter(
        Produto.ativo == True,
        db.or_(
            Produto.nome.ilike(f'%{q}%'),
            Produto.codigo_barras.ilike(f'%{q}%'),
        )
    ).order_by(Produto.nome).limit(50).all()

    return jsonify([{
        'id': p.id,
        'nome': p.nome,
        'codigo': p.codigo_barras,
        'preco_venda': float(p.preco_venda) if p.preco_venda else 0,
        'estoque_atual': float(p.estoque_atual) if p.estoque_atual else 0,
    } for p in produtos])


@bp.route('/produtos/<int:id>')
@login_required
def detalhe_produto(id):
    p = Produto.query.get_or_404(id)
    return jsonify({
        'id': p.id,
        'nome': p.nome,
        'codigo_barras': p.codigo_barras,
        'descricao': p.descricao,
        'preco_venda': float(p.preco_venda) if p.preco_venda else 0,
        'preco_custo': float(p.preco_custo) if p.preco_custo else 0,
        'estoque_atual': float(p.estoque_atual) if p.estoque_atual else 0,
        'estoque_minimo': float(p.estoque_minimo) if p.estoque_minimo else 0,
        'unidade': p.unidade,
        'peso_balanca': p.peso_balanca,
        'ativo': p.ativo,
    })


@bp.route('/clientes')
@login_required
def listar_clientes():
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    return jsonify([{
        'id': c.id,
        'nome': c.nome,
        'cpf_cnpj': c.cpf_cnpj,
        'telefone': c.telefone,
        'celular': c.celular,
        'email': c.email,
    } for c in clientes])


@bp.route('/clientes/busca')
@login_required
def buscar_clientes():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])

    clientes = Cliente.query.filter(
        Cliente.ativo == True,
        db.or_(
            Cliente.nome.ilike(f'%{q}%'),
            Cliente.cpf_cnpj.ilike(f'%{q}%'),
        )
    ).order_by(Cliente.nome).limit(50).all()

    return jsonify([{
        'id': c.id,
        'nome': c.nome,
        'cpf_cnpj': c.cpf_cnpj,
        'telefone': c.telefone,
        'celular': c.celular,
        'email': c.email,
    } for c in clientes])


@bp.route('/vendas/hoje')
@login_required
def vendas_hoje():
    hoje = date.today()
    vendas = Venda.query.filter(
        Venda.status == 'F',
        db.func.date(Venda.created_at) == hoje,
    ).all()

    total = sum(float(v.total) for v in vendas if v.total)

    return jsonify({
        'count': len(vendas),
        'total': total,
    })
