"""
ECD (SPED Contábil) - Escrituração Contábil Digital.
Layout conforme o Manual de Orientação do Leiaute da ECD (versão 9.0+).

Gera arquivo no formato do SPED (leiaute Leiaute 9) contendo:
- Registro 0000: Abertura do arquivo
- Registro 0001: Abertura do Bloco 0
- Registro 0030: Dados cadastrais da entidade
- Registro 0100: Dados do contabilista
- Registro 0150: Tabela de cadastro do participante
- Registro I010: Abertura do Bloco I
- Registro I030: Termo de abertura
- Registro I050: Plano de contas
- Registro I100: Centro de custos
- Registro I150: Saldos periódicos
- Registro I200: Lançamentos contábeis
- Registro I250: Partidas de lançamento
- Registro I350: Abertura do Bloco I (Tabela de histórico)
- Registro I355: Históricos padronizados
- Registro I500: Abertura do Bloco I (Centros de custos)
- Registro I510: Saldos
- Registro 9900: Registros do arquivo
- Registro 9999: Totalizador
"""
from datetime import date, datetime
from decimal import Decimal
from app import db
from app.models.models import PlanoContas, LancamentoContabil, Empresa


class ECDGenerator:
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
        # 0000
        cnpj = ''.join(c for c in (self.empresa.cnpj or '') if c.isdigit())
        ie = self.empresa.inscricao_estadual or ''
        nome = (self.empresa.nome or '')[:100]
        linhas.append(self.reg('0000', 'LE', '9', '0', cnpj, ie, nome, '1', '0',
                                self.empresa.cidade_ibge or '', self.data_inicio.strftime('%d%m%Y'),
                                self.data_fim.strftime('%d%m%Y')))
        # 0001
        linhas.append(self.reg('0001', '0'))
        # 0030
        linhas.append(self.reg('0030', cnpj, ie if ie else 'ISENTO', nome,
                                self.empresa.logradouro or '', self.empresa.numero or '',
                                self.empresa.complemento or '', self.empresa.bairro or '',
                                str(self.empresa.cep or '').replace('-', '').zfill(8),
                                self.empresa.cidade or '', self.empresa.uf or '',
                                '(00)0000-0000', '', '', ''))

        # I010
        linhas.append(self.reg('I010', '1', 'L'))

        # I030 - Termo de abertura
        linhas.append(self.reg('I030', 'Termo de abertura da escrituração contábil digital'))

        # I050 - Plano de contas
        contas = PlanoContas.query.filter_by(ativo=True).order_by(PlanoContas.codigo).all()
        for c in contas:
            linhas.append(self.reg('I050', c.codigo, c.descricao[:100], 'A' if c.nivel == 1 else 'S'))

        # I150 - Saldos periódicos (saldos iniciais)
        for c in contas:
            if c.nivel == 1:
                lancamentos = LancamentoContabil.query.filter(
                    LancamentoContabil.data < self.data_inicio,
                    (LancamentoContabil.debito_id == c.id) | (LancamentoContabil.credito_id == c.id)
                ).all()
                saldo_debito = sum(l.valor for l in lancamentos if l.debito_id == c.id)
                saldo_credito = sum(l.valor for l in lancamentos if l.credito_id == c.id)
                saldo_final = saldo_debito - saldo_credito
                if c.natureza == 'C':
                    saldo_final = -saldo_final
                linhas.append(self.reg('I150', self.data_inicio.strftime('%d%m%Y'), c.codigo,
                                        'D' if saldo_final >= 0 else 'C',
                                        f'{abs(saldo_final):.2f}'))

        # I200 + I250 - Lançamentos contábeis
        lancs = LancamentoContabil.query.filter(
            LancamentoContabil.data.between(self.data_inicio, self.data_fim)
        ).order_by(LancamentoContabil.data, LancamentoContabil.id).all()
        for l in lancs:
            deb = PlanoContas.query.get(l.debito_id)
            cred = PlanoContas.query.get(l.credito_id)
            linhas.append(self.reg('I200', l.data.strftime('%d%m%Y'),
                                    l.lote or f'L{l.id:06d}', '', l.historico[:500],
                                    '0', '0',
                                    '0', '0', 0, ''))
            linhas.append(self.reg('I250', deb.codigo if deb else '', 'D',
                                    f'{float(l.valor):.2f}'))
            linhas.append(self.reg('I250', cred.codigo if cred else '', 'C',
                                    f'{float(l.valor):.2f}'))

        # 9900 - Registros totalizadores
        linhas.append(self.reg('9900', '9999', str(self.contador + 1)))
        # 9999
        linhas.append(self.reg('9999', str(self.contador + 1)))

        conteudo = ''.join(linhas)
        conteudo = conteudo.encode('utf-8', errors='replace').decode('utf-8')
        return conteudo
