"""
Plano de Contas padrão (baseado no modelo STN adaptado para supermercado).
Executar manualmente para popular a tabela plano_contas.
"""
from app import db
from app.models.models import PlanoContas


CONTAS_PADRAO = [
    # Ativo Circulante (01)
    ('1.01.01', 'Caixa', 'A', 1, None, 'D', '01'),
    ('1.01.02', 'Bancos Conta Movimento', 'A', 1, None, 'D', '01'),
    ('1.01.03', 'Aplicações Financeiras', 'A', 1, None, 'D', '01'),
    ('1.01.04', 'Clientes', 'A', 1, None, 'D', '01'),
    ('1.01.05', 'Estoque de Mercadorias', 'A', 1, None, 'D', '01'),
    ('1.01.06', 'Adiantamento a Fornecedores', 'A', 1, None, 'D', '01'),
    ('1.01.07', 'Impostos a Recuperar', 'A', 1, None, 'D', '01'),

    # Ativo Não Circulante (02)
    ('1.02.01', 'Imobilizado', 'A', 1, None, 'D', '02'),
    ('1.02.02', 'Depreciação Acumulada', 'A', 1, None, 'C', '02'),
    ('1.02.03', 'Intangível', 'A', 1, None, 'D', '02'),

    # Passivo Circulante (03)
    ('2.01.01', 'Fornecedores', 'P', 1, None, 'C', '03'),
    ('2.01.02', 'Salários a Pagar', 'P', 1, None, 'C', '03'),
    ('2.01.03', 'FGTS a Recolher', 'P', 1, None, 'C', '03'),
    ('2.01.04', 'INSS a Recolher', 'P', 1, None, 'C', '03'),
    ('2.01.05', 'IRRF a Recolher', 'P', 1, None, 'C', '03'),
    ('2.01.06', 'ICMS a Recolher', 'P', 1, None, 'C', '03'),
    ('2.01.07', 'PIS/COFINS a Recolher', 'P', 1, None, 'C', '03'),
    ('2.01.08', 'Empréstimos a Pagar', 'P', 1, None, 'C', '03'),
    ('2.01.09', 'Contas a Pagar', 'P', 1, None, 'C', '03'),

    # Passivo Não Circulante (04)
    ('2.02.01', 'Financiamentos LP', 'P', 1, None, 'C', '04'),

    # Patrimônio Líquido (05)
    ('2.03.01', 'Capital Social', 'PL', 1, None, 'C', '05'),
    ('2.03.02', 'Reservas de Lucros', 'PL', 1, None, 'C', '05'),
    ('2.03.03', 'Lucros/Prejuízos Acumulados', 'PL', 1, None, 'C', '05'),

    # Receitas (06)
    ('3.01.01', 'Vendas de Mercadorias', 'R', 1, None, 'C', '06'),
    ('3.01.02', 'Receitas Financeiras', 'R', 1, None, 'C', '06'),
    ('3.01.03', 'Outras Receitas', 'R', 1, None, 'C', '06'),

    # Despesas (07)
    ('4.01.01', 'Custo das Mercadorias Vendidas', 'D', 1, None, 'D', '07'),
    ('4.01.02', 'Salários e Encargos', 'D', 1, None, 'D', '07'),
    ('4.01.03', 'Aluguéis', 'D', 1, None, 'D', '07'),
    ('4.01.04', 'Energia Elétrica', 'D', 1, None, 'D', '07'),
    ('4.01.05', 'Água e Esgoto', 'D', 1, None, 'D', '07'),
    ('4.01.06', 'Telefone/Internet', 'D', 1, None, 'D', '07'),
    ('4.01.07', 'Material de Escritório', 'D', 1, None, 'D', '07'),
    ('4.01.08', 'Serviços de Terceiros', 'D', 1, None, 'D', '07'),
    ('4.01.09', 'Despesas com Cartão', 'D', 1, None, 'D', '07'),
    ('4.01.10', 'Despesas Bancárias', 'D', 1, None, 'D', '07'),
    ('4.01.11', 'Depreciação', 'D', 1, None, 'D', '07'),
    ('4.01.12', 'Impostos e Taxas', 'D', 1, None, 'D', '07'),
    ('4.01.13', 'Provisão para Devedores Duvidosos', 'D', 1, None, 'D', '07'),
    ('4.01.14', 'Despesas com Marketing', 'D', 1, None, 'D', '07'),
    ('4.01.15', 'Perdas com Quebra/Avaria', 'D', 1, None, 'D', '07'),
    ('4.01.16', 'Despesas de Frete', 'D', 1, None, 'D', '07'),
    ('4.01.17', 'Outras Despesas', 'D', 1, None, 'D', '07'),
]


def seed_plano_contas():
    """Popula o plano de contas padrão se estiver vazio."""
    if PlanoContas.query.first():
        return 0
    for codigo, descricao, tipo, nivel, conta_pai_id, natureza, grupo in CONTAS_PADRAO:
        conta = PlanoContas(
            codigo=codigo,
            descricao=descricao,
            tipo=tipo,
            nivel=nivel,
            conta_pai_id=conta_pai_id,
            natureza=natureza,
            grupo=grupo,
            ativo=True,
        )
        db.session.add(conta)
    db.session.commit()
    return len(CONTAS_PADRAO)


def criar_seed_plano_contas():
    """Cria a view/route para seed via CLI ou web."""
    return seed_plano_contas()
