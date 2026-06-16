from app import db
from flask_login import UserMixin
from datetime import date, datetime
import json


class Setor(db.Model):
    __tablename__ = 'setores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    ativo = db.Column(db.Boolean, default=True)


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    login = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    papel = db.Column(db.String(20), default='funcionario')  # admin, chefe_setor, funcionario
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'))
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    ativo = db.Column(db.Boolean, default=True)
    ultimo_login = db.Column(db.DateTime)
    setor = db.relationship('Setor', backref='usuarios')
    criado_por = db.relationship('Usuario', remote_side='Usuario.id', backref='criados')


class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    produtos = db.relationship('Produto', backref='categoria', lazy=True)


class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    codigo_barras = db.Column(db.String(20), unique=True)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'))
    preco_venda = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    preco_custo = db.Column(db.Numeric(10, 2), default=0)
    unidade = db.Column(db.String(5), default='UN')
    ncm = db.Column(db.String(10))
    cest = db.Column(db.String(10))
    origem = db.Column(db.String(1), default='0')
    estoque_minimo = db.Column(db.Numeric(10, 2), default=0)
    estoque_atual = db.Column(db.Numeric(10, 2), default=0)
    controla_lote = db.Column(db.Boolean, default=False)
    dias_validade = db.Column(db.Integer)
    peso_balanca = db.Column(db.Boolean, default=False)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class TabelaPreco(db.Model):
    __tablename__ = 'tabelas_preco'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    data_inicio = db.Column(db.Date)
    data_fim = db.Column(db.Date)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    itens = db.relationship('ItemTabelaPreco', backref='tabela', lazy='dynamic', cascade='all, delete-orphan')


class ItemTabelaPreco(db.Model):
    __tablename__ = 'itens_tabela_preco'
    id = db.Column(db.Integer, primary_key=True)
    tabela_id = db.Column(db.Integer, db.ForeignKey('tabelas_preco.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    preco = db.Column(db.Numeric(10, 2), nullable=False)
    quantidade_min = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    produto = db.relationship('Produto', backref='itens_tabela')


class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cpf_cnpj = db.Column(db.String(20), unique=True)
    rg_ie = db.Column(db.String(20))
    email = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    celular = db.Column(db.String(20))
    cep = db.Column(db.String(10))
    endereco = db.Column(db.String(200))
    numero = db.Column(db.String(10))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    limite_credito = db.Column(db.Numeric(10, 2), default=0)
    tabela_preco_id = db.Column(db.Integer, db.ForeignKey('tabelas_preco.id'))
    ativo = db.Column(db.Boolean, default=True)
    data_aniversario = db.Column(db.Date)
    pontos_fidelidade = db.Column(db.Integer, default=0)
    ultima_compra = db.Column(db.DateTime)
    total_compras = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    tabela_preco = db.relationship('TabelaPreco', backref='clientes')


class FidelidadeResgate(db.Model):
    __tablename__ = 'fidelidade_resgates'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    pontos = db.Column(db.Integer, nullable=False)
    valor_desconto = db.Column(db.Numeric(10, 2), nullable=False)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    cliente = db.relationship('Cliente', backref='resgates_fidelidade')
    venda = db.relationship('Venda', backref='resgates_fidelidade')


class MetaVendedor(db.Model):
    __tablename__ = 'metas_vendedor'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    valor_meta = db.Column(db.Numeric(10, 2), nullable=False)
    comissao_percentual = db.Column(db.Numeric(5, 2), default=0)
    comissao_fixa = db.Column(db.Numeric(10, 2), default=0)
    atingido = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    usuario = db.relationship('Usuario', backref='metas')
    __table_args__ = (db.UniqueConstraint('usuario_id', 'mes', 'ano'),)


class Ativo(db.Model):
    __tablename__ = 'ativos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50))  # camera, balanca, veiculo, etc
    patrimonio = db.Column(db.String(50))
    valor_aquisicao = db.Column(db.Numeric(10, 2), default=0)
    data_aquisicao = db.Column(db.Date)
    vida_util = db.Column(db.Integer)  # meses
    observacao = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class OrdemProducao(db.Model):
    __tablename__ = 'ordens_producao'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    setor = db.Column(db.String(50))  # acougue, padaria, hortifruti
    data_producao = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(2), default='01')  # 01=Aberta, 02=Produzindo, 03=Concluida, 99=Cancelada
    observacao = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    usuario = db.relationship('Usuario', backref='ordens_producao')
    itens = db.relationship('OrdemProducaoItem', backref='ordem', lazy='dynamic', cascade='all, delete-orphan')


class OrdemProducaoItem(db.Model):
    __tablename__ = 'ordens_producao_itens'
    id = db.Column(db.Integer, primary_key=True)
    ordem_id = db.Column(db.Integer, db.ForeignKey('ordens_producao.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade_prevista = db.Column(db.Numeric(10, 2), nullable=False)
    quantidade_produzida = db.Column(db.Numeric(10, 2), default=0)
    produto = db.relationship('Produto', backref='ordens_producao')


class Mesa(db.Model):
    __tablename__ = 'mesas'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    descricao = db.Column(db.String(100))
    capacidade = db.Column(db.Integer, default=4)
    status = db.Column(db.String(2), default='01')  # 01=Livre, 02=Ocupada, 03=Reservada
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    venda = db.relationship('Venda', backref='mesa')


class ComandaItem(db.Model):
    __tablename__ = 'comanda_itens'
    id = db.Column(db.Integer, primary_key=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), nullable=False)
    preco = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(2), default='01')  # 01=Pendente, 02=Entregue, 99=Cancelado
    observacao = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    mesa = db.relationship('Mesa', backref='comanda_itens')
    produto = db.relationship('Produto', backref='comanda_itens')
    usuario = db.relationship('Usuario', backref='comanda_itens')


class Cheque(db.Model):
    __tablename__ = 'cheques'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'))
    banco = db.Column(db.String(50))
    agencia = db.Column(db.String(10))
    conta = db.Column(db.String(20))
    numero_cheque = db.Column(db.String(20))
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_emissao = db.Column(db.Date, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_deposito = db.Column(db.Date)
    data_compensacao = db.Column(db.Date)
    status = db.Column(db.String(2), default='01')  # 01=Em Carteira, 02=Depositado, 03=Compensado, 04=Devolvido, 99=Cancelado
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'))
    observacao = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    cliente = db.relationship('Cliente', backref='cheques')
    venda = db.relationship('Venda', backref='cheques')


class NfseConfig(db.Model):
    __tablename__ = 'nfse_config'
    id = db.Column(db.Integer, primary_key=True)
    municipio_ibge = db.Column(db.String(10))
    municipio_nome = db.Column(db.String(100))
    aliquota_padrao = db.Column(db.Numeric(5, 2), default=5.00)
    item_servico_lista = db.Column(db.String(10), default='01.01')
    cnae = db.Column(db.String(10))
    inscricao_municipal = db.Column(db.String(30))
    producao = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class NfseLote(db.Model):
    __tablename__ = 'nfse_lotes'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    data_emissao = db.Column(db.Date, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'))
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    descricao = db.Column(db.String(300))
    chave_acesso = db.Column(db.String(50))
    xml_enviado = db.Column(db.Text)
    xml_resposta = db.Column(db.Text)
    status = db.Column(db.String(2), default='01')  # 01=Pendente, 02=Autorizada, 03=Rejeitada, 99=Cancelada
    created_at = db.Column(db.DateTime, default=datetime.now)
    cliente = db.relationship('Cliente', backref='nfse_lotes')


class Fornecedor(db.Model):
    __tablename__ = 'fornecedores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cpf_cnpj = db.Column(db.String(20), unique=True)
    rg_ie = db.Column(db.String(20))
    email = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    cep = db.Column(db.String(10))
    endereco = db.Column(db.String(200))
    numero = db.Column(db.String(10))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    prazo_entrega = db.Column(db.Integer, default=30)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Lote(db.Model):
    __tablename__ = 'lotes'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    codigo = db.Column(db.String(50), nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), default=0)
    data_fabricacao = db.Column(db.Date)
    data_validade = db.Column(db.Date)
    preco_custo = db.Column(db.Numeric(10, 2), default=0)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    produto = db.relationship('Produto', backref='lotes')


class MovimentacaoEstoque(db.Model):
    __tablename__ = 'movimentacoes_estoque'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(1), nullable=False)  # E=Entrada, S=Saída
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    lote_id = db.Column(db.Integer, db.ForeignKey('lotes.id'))
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'))
    quantidade = db.Column(db.Numeric(10, 2), nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), default=0)
    motivo = db.Column(db.String(200))
    documento = db.Column(db.String(50))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    produto = db.relationship('Produto', backref='movimentacoes')
    lote = db.relationship('Lote', backref='movimentacoes')
    fornecedor = db.relationship('Fornecedor', backref='movimentacoes')
    usuario = db.relationship('Usuario', backref='movimentacoes')


class Caixa(db.Model):
    __tablename__ = 'caixas'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_abertura = db.Column(db.DateTime, default=datetime.now)
    data_fechamento = db.Column(db.DateTime)
    valor_abertura = db.Column(db.Numeric(10, 2), default=0)
    valor_fechamento = db.Column(db.Numeric(10, 2))
    valor_esperado = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(1), default='A')  # A=Aberto, F=Fechado
    usuario = db.relationship('Usuario', backref='caixas')


class Venda(db.Model):
    __tablename__ = 'vendas'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    caixa_id = db.Column(db.Integer, db.ForeignKey('caixas.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'))
    convenio_id = db.Column(db.Integer, db.ForeignKey('convenios.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    desconto = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(1), default='A')  # A=Aberta, F=Finalizada, C=Cancelada
    created_at = db.Column(db.DateTime, default=datetime.now)
    caixa = db.relationship('Caixa', backref='vendas')
    cliente = db.relationship('Cliente', backref='vendas')
    convenio = db.relationship('Convenio', backref='vendas')
    usuario = db.relationship('Usuario', backref='vendas')


class ItemVenda(db.Model):
    __tablename__ = 'itens_venda'
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    desconto = db.Column(db.Numeric(10, 2), default=0)
    venda = db.relationship('Venda', backref='itens')
    produto = db.relationship('Produto', backref='itens_venda')


class PagamentoVenda(db.Model):
    __tablename__ = 'pagamentos_venda'
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'), nullable=False)
    forma_pagamento = db.Column(db.String(20), nullable=False)  # DINHEIRO, CREDITO, DEBITO, PIX
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    troco = db.Column(db.Numeric(10, 2), default=0)
    nsu = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.now)
    venda = db.relationship('Venda', backref='pagamentos')


class Sangria(db.Model):
    __tablename__ = 'sangrias'
    id = db.Column(db.Integer, primary_key=True)
    caixa_id = db.Column(db.Integer, db.ForeignKey('caixas.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    motivo = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
    caixa = db.relationship('Caixa', backref='sangrias')
    usuario = db.relationship('Usuario', backref='sangrias')


class CompraPedido(db.Model):
    __tablename__ = 'compras_pedidos'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    data_pedido = db.Column(db.Date, default=date.today)
    data_prevista = db.Column(db.Date)
    data_recebimento = db.Column(db.Date)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    status = db.Column(db.String(2), default='01')  # 01=Rascunho, 02=Cotacao, 03=Enviado, 04=Confirmado, 05=Recebido, 99=Cancelado
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    desconto = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), default=0)
    observacao = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    fornecedor = db.relationship('Fornecedor', backref='compras_pedidos')
    usuario = db.relationship('Usuario', backref='compras_pedidos')
    itens = db.relationship('CompraItem', backref='pedido', lazy='dynamic', cascade='all, delete-orphan')


class CompraItem(db.Model):
    __tablename__ = 'compras_itens'
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('compras_pedidos.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    desconto = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    produto = db.relationship('Produto', backref='compras_itens')


class Empresa(db.Model):
    __tablename__ = 'empresa'
    id = db.Column(db.Integer, primary_key=True)
    razao_social = db.Column(db.String(200), nullable=False)
    nome_fantasia = db.Column(db.String(200))
    cnpj = db.Column(db.String(20), unique=True, nullable=False)
    ie = db.Column(db.String(20))
    im = db.Column(db.String(20))
    cep = db.Column(db.String(10))
    endereco = db.Column(db.String(200))
    numero = db.Column(db.String(10))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    cidade_ibge = db.Column(db.String(10))
    uf = db.Column(db.String(2))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    regime_tributario = db.Column(db.String(1), default='3')
    logo = db.Column(db.Text)


class Cargo(db.Model):
    __tablename__ = 'cargos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    salario_base = db.Column(db.Numeric(10, 2), default=0)
    ativo = db.Column(db.Boolean, default=True)


class Funcionario(db.Model):
    __tablename__ = 'funcionarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    rg = db.Column(db.String(20))
    ctps = db.Column(db.String(20))
    pis = db.Column(db.String(20))
    data_nascimento = db.Column(db.Date)
    estado_civil = db.Column(db.String(20))
    genero = db.Column(db.String(1))
    cep = db.Column(db.String(10))
    endereco = db.Column(db.String(200))
    numero = db.Column(db.String(10))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    telefone = db.Column(db.String(20))
    celular = db.Column(db.String(20))
    email = db.Column(db.String(100))
    cargo_id = db.Column(db.Integer, db.ForeignKey('cargos.id'))
    setor_id = db.Column(db.Integer, db.ForeignKey('setores.id'))
    data_admissao = db.Column(db.Date)
    data_demissao = db.Column(db.Date)
    salario_contratual = db.Column(db.Numeric(10, 2), default=0)
    tipo_salario = db.Column(db.String(1), default='M')  # M=Mensalista, H=Horista, D=Diarista
    forma_pagamento = db.Column(db.String(20), default='credito')
    banco = db.Column(db.String(50))
    agencia = db.Column(db.String(10))
    conta = db.Column(db.String(20))
    tipo_conta = db.Column(db.String(10))
    vale_transporte = db.Column(db.Boolean, default=False)
    vale_refeicao = db.Column(db.Boolean, default=False)
    planoSaude = db.Column(db.Boolean, default=False)
    adicional_periculosidade = db.Column(db.Numeric(5, 2), default=0)
    adicional_insalubridade = db.Column(db.Numeric(5, 2), default=0)
    escala = db.Column(db.String(10), default='6x1')  # 12x36, 6x1, 5x2
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    cargo = db.relationship('Cargo', backref='funcionarios')
    setor = db.relationship('Setor', backref='funcionarios')


class Ponto(db.Model):
    __tablename__ = 'ponto'
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    entrada1 = db.Column(db.Time)
    saida1 = db.Column(db.Time)
    entrada2 = db.Column(db.Time)
    saida2 = db.Column(db.Time)
    horas_extras = db.Column(db.Numeric(5, 2), default=0)
    horas_noturnas = db.Column(db.Numeric(5, 2), default=0)
    faltou = db.Column(db.Boolean, default=False)
    justificativa = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now)
    funcionario = db.relationship('Funcionario', backref='pontos')


class FolhaPagamento(db.Model):
    __tablename__ = 'folhas_pagamento'
    id = db.Column(db.Integer, primary_key=True)
    competencia = db.Column(db.String(7), nullable=False)  # MM/AAAA
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    data_pagamento = db.Column(db.Date)
    salario_base = db.Column(db.Numeric(10, 2), default=0)
    horas_extras = db.Column(db.Numeric(10, 2), default=0)
    comissoes = db.Column(db.Numeric(10, 2), default=0)
    adicionais = db.Column(db.Numeric(10, 2), default=0)
    vale_transporte = db.Column(db.Numeric(10, 2), default=0)
    vale_refeicao = db.Column(db.Numeric(10, 2), default=0)
    inss = db.Column(db.Numeric(10, 2), default=0)
    irrf = db.Column(db.Numeric(10, 2), default=0)
    fgts = db.Column(db.Numeric(10, 2), default=0)
    outros_descontos = db.Column(db.Numeric(10, 2), default=0)
    salario_liquido = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(2), default='01')  # 01=Calculada, 02=Paga, 99=Cancelada
    pago = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    funcionario = db.relationship('Funcionario', backref='folhas')


class Ferias(db.Model):
    __tablename__ = 'ferias'
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    dias = db.Column(db.Integer, default=30)
    valor_recebido = db.Column(db.Numeric(10, 2), default=0)
    abono_pecuniario = db.Column(db.Numeric(10, 2), default=0)
    pago = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    funcionario = db.relationship('Funcionario', backref='ferias')


class Rescisao(db.Model):
    __tablename__ = 'rescisoes'
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionarios.id'), nullable=False)
    data_rescisao = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(2))  # SD=Sem justa causa, SC=Com justa causa, PD=Pedido demissao
    aviso_previo = db.Column(db.Numeric(10, 2), default=0)
    ferias_proporcionais = db.Column(db.Numeric(10, 2), default=0)
    decimo_terceiro = db.Column(db.Numeric(10, 2), default=0)
    saldo_salario = db.Column(db.Numeric(10, 2), default=0)
    multa_fgts = db.Column(db.Numeric(10, 2), default=0)
    outros = db.Column(db.Numeric(10, 2), default=0)
    total_bruto = db.Column(db.Numeric(10, 2), default=0)
    descontos = db.Column(db.Numeric(10, 2), default=0)
    total_liquido = db.Column(db.Numeric(10, 2), default=0)
    pago = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    funcionario = db.relationship('Funcionario', backref='rescisoes')


class CategoriaFinanceira(db.Model):
    __tablename__ = 'categorias_financeiro'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(1), nullable=False)  # R=Receita, D=Despesa
    ativo = db.Column(db.Boolean, default=True)


class ContaPagar(db.Model):
    __tablename__ = 'contas_pagar'
    id = db.Column(db.Integer, primary_key=True)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'))
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_financeiro.id'))
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date)
    valor_pago = db.Column(db.Numeric(10, 2), default=0)
    pago = db.Column(db.Boolean, default=False)
    documento = db.Column(db.String(50))
    observacao = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    fornecedor = db.relationship('Fornecedor', backref='contas_pagar')
    categoria = db.relationship('CategoriaFinanceira', backref='contas_pagar')


class ContaReceber(db.Model):
    __tablename__ = 'contas_receber'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'))
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_financeiro.id'))
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_recebimento = db.Column(db.Date)
    valor_recebido = db.Column(db.Numeric(10, 2), default=0)
    recebido = db.Column(db.Boolean, default=False)
    documento = db.Column(db.String(50))
    observacao = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    cliente = db.relationship('Cliente', backref='contas_receber')
    categoria = db.relationship('CategoriaFinanceira', backref='contas_receber')


class MovimentoCaixa(db.Model):
    __tablename__ = 'movimentos_caixa'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(1), nullable=False)  # E=Entrada, S=Saida
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data = db.Column(db.Date, nullable=False, default=date.today)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_financeiro.id'))
    conta_pagar_id = db.Column(db.Integer, db.ForeignKey('contas_pagar.id'))
    conta_receber_id = db.Column(db.Integer, db.ForeignKey('contas_receber.id'))
    documento = db.Column(db.String(50))
    observacao = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    categoria = db.relationship('CategoriaFinanceira', backref='movimentos')


class ConfigFiscal(db.Model):
    __tablename__ = 'config_fiscal'
    id = db.Column(db.Integer, primary_key=True)
    regime_tributario = db.Column(db.String(1), default='3')  # 1=SN, 2=LP, 3=NP
    aliquota_padrao = db.Column(db.Numeric(5, 2), default=18.00)
    proximo_numero_nfe = db.Column(db.Integer, default=1)
    proximo_numero_nfce = db.Column(db.Integer, default=1)
    serie_nfe = db.Column(db.Integer, default=1)
    serie_nfce = db.Column(db.Integer, default=1)
    certificado_digital = db.Column(db.String(200))
    certificado_senha = db.Column(db.String(100))
    ambiente = db.Column(db.String(1), default='2')  # 1=Producao, 2=Homologacao
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresa.id'))
    caminho_dll_sat = db.Column(db.String(255), default='C:\\SAT\\sat.dll')
    codigo_ativacao_sat = db.Column(db.String(20), default='12345678')
    cnpj_software_house = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.now)


class DocumentoFiscal(db.Model):
    __tablename__ = 'documentos_fiscais'
    id = db.Column(db.Integer, primary_key=True)
    modelo = db.Column(db.String(3), nullable=False)  # NF-e, NFC-e, SAT
    serie = db.Column(db.Integer, nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    chave_acesso = db.Column(db.String(44))
    status = db.Column(db.String(2), default='01')  # 01=Digitando, 02=Assinando, 03=Transmitindo, 04=Autorizada, 05=Cancelada, 99=Rejeitada
    data_emissao = db.Column(db.DateTime, default=datetime.now)
    data_autorizacao = db.Column(db.DateTime)
    protocolo = db.Column(db.String(20))
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'))
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'))
    cfop = db.Column(db.String(4), default='5102')
    natureza_operacao = db.Column(db.String(100), default='Venda')
    base_calculo = db.Column(db.Numeric(10, 2), default=0)
    valor_produtos = db.Column(db.Numeric(10, 2), default=0)
    valor_desconto = db.Column(db.Numeric(10, 2), default=0)
    valor_total = db.Column(db.Numeric(10, 2), default=0)
    valor_frete = db.Column(db.Numeric(10, 2), default=0)
    valor_seguro = db.Column(db.Numeric(10, 2), default=0)
    valor_outras = db.Column(db.Numeric(10, 2), default=0)
    valor_icms = db.Column(db.Numeric(10, 2), default=0)
    valor_ipi = db.Column(db.Numeric(10, 2), default=0)
    valor_pis = db.Column(db.Numeric(10, 2), default=0)
    valor_cofins = db.Column(db.Numeric(10, 2), default=0)
    valor_total_tributos = db.Column(db.Numeric(10, 2), default=0)
    xml_assinado = db.Column(db.Text)
    xml_protocolo = db.Column(db.Text)
    motivo_cancelamento = db.Column(db.String(200))
    justificativa = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    cliente = db.relationship('Cliente', backref='documentos_fiscais')
    venda = db.relationship('Venda', backref='documentos_fiscais')
    itens = db.relationship('ItemDocumentoFiscal', backref='documento', lazy='dynamic', cascade='all, delete-orphan')


class ItemDocumentoFiscal(db.Model):
    __tablename__ = 'itens_documento_fiscal'
    id = db.Column(db.Integer, primary_key=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos_fiscais.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), nullable=False)
    valor_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    ncm = db.Column(db.String(10))
    cest = db.Column(db.String(10))
    cfop = db.Column(db.String(4))
    aliquota_icms = db.Column(db.Numeric(5, 2), default=0)
    aliquota_ipi = db.Column(db.Numeric(5, 2), default=0)
    aliquota_pis = db.Column(db.Numeric(5, 2), default=0)
    aliquota_cofins = db.Column(db.Numeric(5, 2), default=0)
    cst_icms = db.Column(db.String(3))
    cst_ipi = db.Column(db.String(2))
    cst_pis = db.Column(db.String(2))
    cst_cofins = db.Column(db.String(2))
    produto = db.relationship('Produto', backref='itens_fiscais')


class LogAuditoria(db.Model):
    __tablename__ = 'log_auditoria'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_nome = db.Column(db.String(100))
    acao = db.Column(db.String(200), nullable=False)
    entidade = db.Column(db.String(50))
    entidade_id = db.Column(db.Integer)
    valores_anteriores = db.Column(db.Text)
    valores_novos = db.Column(db.Text)
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.now)
    usuario = db.relationship('Usuario', backref='logs_auditoria')


class Notificacao(db.Model):
    __tablename__ = 'notificacoes'
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(30), nullable=False)  # estoque_baixo, conta_vencendo, lote_vencendo
    titulo = db.Column(db.String(200), nullable=False)
    mensagem = db.Column(db.Text)
    entidade = db.Column(db.String(50))
    entidade_id = db.Column(db.Integer)
    lida = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Orcamento(db.Model):
    __tablename__ = 'orcamentos'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_orcamento = db.Column(db.Date, default=date.today)
    data_validade = db.Column(db.Date)
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    desconto = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(2), default='01')  # 01=Rascunho, 02=Aprovado, 03=Convertido, 99=Cancelado
    observacao = db.Column(db.Text)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    cliente = db.relationship('Cliente', backref='orcamentos')
    usuario = db.relationship('Usuario', backref='orcamentos')
    venda = db.relationship('Venda', backref='orcamento')
    itens = db.relationship('OrcamentoItem', backref='orcamento', lazy='dynamic', cascade='all, delete-orphan')


class OrcamentoItem(db.Model):
    __tablename__ = 'orcamentos_itens'
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamentos.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    desconto = db.Column(db.Numeric(10, 2), default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    produto = db.relationship('Produto', backref='orcamentos_itens')


class Devolucao(db.Model):
    __tablename__ = 'devolucoes'
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('vendas.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_devolucao = db.Column(db.DateTime, default=datetime.now)
    motivo = db.Column(db.Text, nullable=False)
    valor_total = db.Column(db.Numeric(10, 2), default=0)
    documento_fiscal_id = db.Column(db.Integer, db.ForeignKey('documentos_fiscais.id'))
    status = db.Column(db.String(2), default='01')  # 01=Registrada, 02=Estorno fiscal realizado
    created_at = db.Column(db.DateTime, default=datetime.now)
    venda = db.relationship('Venda', backref='devolucoes')
    usuario = db.relationship('Usuario', backref='devolucoes')
    documento_fiscal = db.relationship('DocumentoFiscal', backref='devolucao')
    itens = db.relationship('DevolucaoItem', backref='devolucao', lazy='dynamic', cascade='all, delete-orphan')


class DevolucaoItem(db.Model):
    __tablename__ = 'devolucoes_itens'
    id = db.Column(db.Integer, primary_key=True)
    devolucao_id = db.Column(db.Integer, db.ForeignKey('devolucoes.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    produto = db.relationship('Produto', backref='devolucoes_itens')


class ConfigTEF(db.Model):
    __tablename__ = 'config_tef'
    id = db.Column(db.Integer, primary_key=True)
    modo_simulado = db.Column(db.Boolean, default=True)
    adquirente = db.Column(db.String(50), default='simulada')  # simulada, rede, cielo, getnet, stone
    caminho_pinpad = db.Column(db.String(255))
    codigo_loja = db.Column(db.String(50))
    codigo_terminal = db.Column(db.String(20), default='001')
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Convenio(db.Model):
    __tablename__ = 'convenios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cnpj = db.Column(db.String(20))
    contato = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    limite_credito = db.Column(db.Numeric(10, 2), default=0)
    prazo_recebimento = db.Column(db.Integer, default=30)
    taxa_administracao = db.Column(db.Numeric(5, 2), default=0)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class ContratoConvenio(db.Model):
    __tablename__ = 'contratos_convenio'
    id = db.Column(db.Integer, primary_key=True)
    convenio_id = db.Column(db.Integer, db.ForeignKey('convenios.id'), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    numero = db.Column(db.String(30), nullable=False)
    limite = db.Column(db.Numeric(10, 2), default=0)
    saldo_utilizado = db.Column(db.Numeric(10, 2), default=0)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    convenio = db.relationship('Convenio', backref='contratos')
    cliente = db.relationship('Cliente', backref='contratos_convenio')


class LoginAttempt(db.Model):
    __tablename__ = 'login_attempts'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), nullable=False)
    ip = db.Column(db.String(45), nullable=False)
    sucesso = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.Integer, nullable=False)


class Promocao(db.Model):
    __tablename__ = 'promocoes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    tipo = db.Column(db.String(20), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_inicio = db.Column(db.Date)
    data_fim = db.Column(db.Date)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    itens = db.relationship('PromocaoItem', backref='promocao', lazy='dynamic', cascade='all, delete-orphan')


class PromocaoItem(db.Model):
    __tablename__ = 'promocoes_itens'
    id = db.Column(db.Integer, primary_key=True)
    promocao_id = db.Column(db.Integer, db.ForeignKey('promocoes.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade_minima = db.Column(db.Numeric(10, 2), default=1)
    preco_promocional = db.Column(db.Numeric(10, 2))
    desconto_percentual = db.Column(db.Numeric(5, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    produto = db.relationship('Produto', backref='promocoes')


class BalancaConfig(db.Model):
    __tablename__ = 'balanca_config'
    id = db.Column(db.Integer, primary_key=True)
    modelo = db.Column(db.String(50), default='toledo')
    porta = db.Column(db.String(50), default='COM1')
    baudrate = db.Column(db.Integer, default=9600)
    bytesize = db.Column(db.Integer, default=8)
    parity = db.Column(db.String(1), default='N')
    stopbits = db.Column(db.Integer, default=1)
    timeout = db.Column(db.Integer, default=5)
    prefixo = db.Column(db.String(10), default='')
    sufixo = db.Column(db.String(10), default='')
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


# ── Contabilidade ───────────────────────────────────────────────

class PlanoContas(db.Model):
    __tablename__ = 'plano_contas'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), nullable=False, unique=True)
    descricao = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(2), nullable=False)  # A=Ativo, P=Passivo, D=Despesa, R=Receita, PL=Patrimônio Líquido
    nivel = db.Column(db.Integer, default=1)  # 1=analítico, 2=sintético, etc.
    conta_pai_id = db.Column(db.Integer, db.ForeignKey('plano_contas.id'))
    natureza = db.Column(db.String(1), nullable=False)  # D=Devedora, C=Credora
    grupo = db.Column(db.String(2))  # 01=Ativo Circ, 02=Ativo NCirc, 03=Passivo Circ, etc.
    receita_despesa = db.Column(db.String(1))  # R=Receita, D=Despesa (para resultado)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    filhos = db.relationship('PlanoContas', backref=db.backref('conta_pai', remote_side=[id]), lazy='dynamic')


class LancamentoContabil(db.Model):
    __tablename__ = 'lancamentos_contabeis'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    historico = db.Column(db.String(500), nullable=False)
    valor = db.Column(db.Numeric(15, 2), nullable=False)
    debito_id = db.Column(db.Integer, db.ForeignKey('plano_contas.id'), nullable=False)
    credito_id = db.Column(db.Integer, db.ForeignKey('plano_contas.id'), nullable=False)
    documento = db.Column(db.String(50))
    lote = db.Column(db.String(20))  # lote contábil (ex: FOLHA01, VENDA001)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    conta_debito = db.relationship('PlanoContas', foreign_keys=[debito_id])
    conta_credito = db.relationship('PlanoContas', foreign_keys=[credito_id])
    usuario = db.relationship('Usuario', backref='lancamentos_contabeis')


# ── PIX ─────────────────────────────────────────────────────────

class PixConfig(db.Model):
    __tablename__ = 'pix_config'
    id = db.Column(db.Integer, primary_key=True)
    chave_pix = db.Column(db.String(100), nullable=False)
    tipo_chave = db.Column(db.String(10), default='cpf')  # cpf, cnpj, email, telefone, aleatoria
    nome_recebedor = db.Column(db.String(100), nullable=False)
    cidade_recebedor = db.Column(db.String(50), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class SugestaoCompra(db.Model):
    __tablename__ = 'sugestoes_compra'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade_sugerida = db.Column(db.Numeric(10, 2), nullable=False)
    estoque_atual = db.Column(db.Numeric(10, 2), default=0)
    vendas_30d = db.Column(db.Numeric(10, 2), default=0)
    classe_abc = db.Column(db.String(1))
    prioridade = db.Column(db.Integer, default=0)
    gerado_em = db.Column(db.DateTime, default=datetime.now)
    atendido = db.Column(db.Boolean, default=False)
    produto = db.relationship('Produto', backref='sugestoes_compra')


class Boleto(db.Model):
    __tablename__ = 'boletos'
    id = db.Column(db.Integer, primary_key=True)
    conta_receber_id = db.Column(db.Integer, db.ForeignKey('contas_receber.id'))
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'))
    numero = db.Column(db.String(20))
    nosso_numero = db.Column(db.String(50))
    linha_digitavel = db.Column(db.String(60))
    codigo_barras = db.Column(db.String(50))
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_emissao = db.Column(db.Date, nullable=False, default=date.today)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date)
    valor_pago = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(db.String(1), default='A')  # A=Aberto, P=Pago, C=Cancelado
    arquivo_pdf = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    conta_receber = db.relationship('ContaReceber', backref='boletos')
    cliente = db.relationship('Cliente', backref='boletos')


class Conciliacao(db.Model):
    __tablename__ = 'conciliacoes'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False, default=date.today)
    arquivo_nome = db.Column(db.String(255))
    total_linhas = db.Column(db.Integer, default=0)
    total_conciliado = db.Column(db.Integer, default=0)
    status = db.Column(db.String(1), default='A')  # A=Aberta, F=Fechada
    created_at = db.Column(db.DateTime, default=datetime.now)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    usuario = db.relationship('Usuario', backref='conciliacoes')
    itens = db.relationship('ConciliacaoItem', backref='conciliacao', lazy='dynamic')


class ConciliacaoItem(db.Model):
    __tablename__ = 'conciliacao_itens'
    id = db.Column(db.Integer, primary_key=True)
    conciliacao_id = db.Column(db.Integer, db.ForeignKey('conciliacoes.id'), nullable=False)
    tipo = db.Column(db.String(1))  # C=Credito, D=Debito
    descricao = db.Column(db.String(200))
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data = db.Column(db.Date)
    documento = db.Column(db.String(50))
    conciliado = db.Column(db.Boolean, default=False)
    conta_pagar_id = db.Column(db.Integer, db.ForeignKey('contas_pagar.id'))
    conta_receber_id = db.Column(db.Integer, db.ForeignKey('contas_receber.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    conta_pagar = db.relationship('ContaPagar', backref='conciliacao_itens')
    conta_receber = db.relationship('ContaReceber', backref='conciliacao_itens')


# ── Filial / Multi-Filial ───────────────────────────────────────

class Filial(db.Model):
    __tablename__ = 'filiais'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(20))
    cep = db.Column(db.String(10))
    endereco = db.Column(db.String(200))
    numero = db.Column(db.String(10))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class TransferenciaEstoque(db.Model):
    __tablename__ = 'transferencias_estoque'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    filial_origem_id = db.Column(db.Integer, db.ForeignKey('filiais.id'), nullable=False)
    filial_destino_id = db.Column(db.Integer, db.ForeignKey('filiais.id'), nullable=False)
    data_transferencia = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(2), default='01')  # 01=Pendente, 02=Concluida, 99=Cancelada
    observacao = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    filial_origem = db.relationship('Filial', foreign_keys=[filial_origem_id], backref='transferencias_saida')
    filial_destino = db.relationship('Filial', foreign_keys=[filial_destino_id], backref='transferencias_entrada')
    usuario = db.relationship('Usuario', backref='transferencias')
    itens = db.relationship('TransferenciaItem', backref='transferencia', lazy='dynamic', cascade='all, delete-orphan')


class TransferenciaItem(db.Model):
    __tablename__ = 'transferencia_itens'
    id = db.Column(db.Integer, primary_key=True)
    transferencia_id = db.Column(db.Integer, db.ForeignKey('transferencias_estoque.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), nullable=False)
    produto = db.relationship('Produto', backref='transferencias')


# ── Cotação / Quotation ──────────────────────────────────────────

class Cotacao(db.Model):
    __tablename__ = 'cotacoes'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    data_cotacao = db.Column(db.Date, nullable=False, default=date.today)
    data_validade = db.Column(db.Date)
    observacao = db.Column(db.Text)
    status = db.Column(db.String(2), default='01')
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    compra_pedido_id = db.Column(db.Integer, db.ForeignKey('compras_pedidos.id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    usuario = db.relationship('Usuario', backref='cotacoes')
    compra_pedido = db.relationship('CompraPedido', backref='cotacao')
    fornecedores = db.relationship('CotacaoFornecedor', backref='cotacao', lazy='dynamic', cascade='all, delete-orphan')
    itens = db.relationship('CotacaoItem', backref='cotacao', lazy='dynamic', cascade='all, delete-orphan')


class CotacaoFornecedor(db.Model):
    __tablename__ = 'cotacao_fornecedores'
    id = db.Column(db.Integer, primary_key=True)
    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id'), nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedores.id'), nullable=False)
    status = db.Column(db.String(2), default='01')
    prazo_entrega = db.Column(db.Integer)
    observacao = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    fornecedor = db.relationship('Fornecedor', backref='cotacoes')
    respostas = db.relationship('CotacaoResposta', backref='cotacao_fornecedor', lazy='dynamic', cascade='all, delete-orphan')


class CotacaoItem(db.Model):
    __tablename__ = 'cotacao_itens'
    id = db.Column(db.Integer, primary_key=True)
    cotacao_id = db.Column(db.Integer, db.ForeignKey('cotacoes.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Numeric(10, 2), nullable=False, default=1)
    produto = db.relationship('Produto', backref='cotacao_itens')


class CotacaoResposta(db.Model):
    __tablename__ = 'cotacao_respostas'
    id = db.Column(db.Integer, primary_key=True)
    cotacao_fornecedor_id = db.Column(db.Integer, db.ForeignKey('cotacao_fornecedores.id'), nullable=False)
    cotacao_item_id = db.Column(db.Integer, db.ForeignKey('cotacao_itens.id'), nullable=False)
    preco_unitario = db.Column(db.Numeric(10, 2), default=0)
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    item = db.relationship('CotacaoItem', backref='respostas')


class ConfigGeral(db.Model):
    __tablename__ = 'config_geral'
    id = db.Column(db.Integer, primary_key=True)
    modulo = db.Column(db.String(50), nullable=False)  # pix, nfe, pdv, etc
    chave = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now)
    __table_args__ = (db.UniqueConstraint('modulo', 'chave'),)
