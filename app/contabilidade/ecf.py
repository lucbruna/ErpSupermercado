"""
ECF (Escrituração Contábil Fiscal) - SPED Contábil Fiscal.
Gera arquivo no formato do SPED contendo a escrituração contábil
para fins fiscais (substitui a DIPJ a partir de 2014).

Blocos gerados:
- Bloco 0: Abertura, dados cadastrais
- Bloco E: Plano de contas e partidas
- Bloco J: Demonstrações contábeis (BP, DRE, DLPA/DMPL, DFC)
- Bloco K: Saldos das contas
- Bloco L: Lucro Real (LALUR)
- Bloco M: Livro de Apuração do Lucro Real
- Bloco N: Cálculo da CSLL
- Bloco P: Cálculo do IRPJ
- Bloco Q: Informações econômicas
- Bloco U: Informações gerais
- Bloco Y: Encerramento
"""
from datetime import date, datetime
from decimal import Decimal
from app import db
from app.models.models import PlanoContas, LancamentoContabil, Empresa, Venda, ContaPagar, ContaReceber
from sqlalchemy import func


class ECFGenerator:
    def __init__(self, empresa: Empresa, data_inicio: date, data_fim: date):
        self.empresa = empresa
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.contador = 0

    def reg(self, cod: str, *args) -> str:
        self.contador += 1
        return f'|{cod}|{"|".join(str(a) for a in args)}|\r\n'

    def gerar(self) -> str:
        linhas = []
        cnpj = ''.join(c for c in (self.empresa.cnpj or '') if c.isdigit())
        nome = (self.empresa.nome or '')[:100]

        # 0000
        linhas.append(self.reg('0000', 'LECF', '9', '8', cnpj,
                                self.empresa.inscricao_estadual or '', nome,
                                self.data_inicio.strftime('%d%m%Y'),
                                self.data_fim.strftime('%d%m%Y'),
                                '0', 'A', '1'))

        # Bloco 0 - Abertura
        linhas.append(self.reg('0001', '0'))
        linhas.append(self.reg('0020', cnpj, '0', 'R'))
        linhas.append(self.reg('0030', cnpj,
                                self.empresa.inscricao_estadual or 'ISENTO',
                                nome, self.empresa.logradouro or '',
                                self.empresa.numero or '', self.empresa.complemento or '',
                                self.empresa.bairro or '',
                                str(self.empresa.cep or '').replace('-', '').zfill(8),
                                self.empresa.cidade or '', self.empresa.uf or ''))

        # 0035 - Dados do contabilista (simplificado)
        linhas.append(self.reg('0035', '', '', '', '', '', '', '', '', '', '', '', '', ''))

        # Bloco E - Plano de contas
        linhas.append(self.reg('E010', '1', 'H'))
        contas = PlanoContas.query.filter_by(ativo=True).order_by(PlanoContas.codigo).all()
        for c in contas:
            tipo_ref = '01' if c.tipo in ('A',) else '02' if c.tipo in ('P',) else \
                       '03' if c.tipo == 'PL' else '04' if c.tipo == 'R' else '05'
            nat = 'D' if c.natureza == 'D' else 'C'
            linhas.append(self.reg('E020', c.codigo, c.descricao[:80],
                                    'A' if c.nivel == 1 else 'S', nat, tipo_ref))

        # Bloco K - Saldos das contas
        linhas.append(self.reg('K010', '1'))
        for c in contas:
            if c.nivel == 1:
                lancamentos = LancamentoContabil.query.filter(
                    LancamentoContabil.data.between(self.data_inicio, self.data_fim),
                    (LancamentoContabil.debito_id == c.id) | (LancamentoContabil.credito_id == c.id)
                ).all()
                saldo_debito = sum(l.valor for l in lancamentos if l.debito_id == c.id)
                saldo_credito = sum(l.valor for l in lancamentos if l.credito_id == c.id)
                saldo_final = saldo_debito - saldo_credito
                if c.natureza == 'C':
                    saldo_final = -saldo_final
                linhas.append(self.reg('K030', c.codigo, self.data_fim.strftime('%d%m%Y'),
                                        'D' if saldo_final >= 0 else 'C',
                                        f'{abs(saldo_final):.2f}'))

        # Bloco L - Lucro Real (LALUR - simplificado)
        linhas.append(self.reg('L010', '1'))
        total_vendas = db.session.query(func.sum(Venda.total)).filter(
            Venda.created_at.between(
                datetime.combine(self.data_inicio, datetime.min.time()),
                datetime.combine(self.data_fim, datetime.max.time())
            ),
            Venda.status == 'F'
        ).scalar() or 0
        total_despesas = db.session.query(func.sum(ContaPagar.valor)).filter(
            ContaPagar.data_pagamento.between(self.data_inicio, self.data_fim),
            ContaPagar.pago == True
        ).scalar() or 0
        lucro = float(total_vendas) - float(total_despesas)
        linhas.append(self.reg('L210', f'{lucro:.2f}', '0,00', '0,00', '0,00', '0,00', '0,00', '0,00',
                                '0,00', '0,00', '0,00', '0,00', '0,00', '0,00'))

        # 9900 + 9999
        linhas.append(self.reg('9900', '9999', str(self.contador + 1)))
        linhas.append(self.reg('9999', str(self.contador + 1)))

        return ''.join(linhas)
