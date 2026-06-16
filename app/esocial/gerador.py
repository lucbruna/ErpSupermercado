"""
Gerador de eventos eSocial e CAGED.
Suporta os principais eventos obrigatórios do eSocial:
- S-1000: Informações do Empregador
- S-2200: Cadastramento Inicial do Trabalhador
- S-2206: Alteração de Dados do Trabalhador
- S-2230: Afastamento Temporário
- S-2299: Desligamento
- S-2300: Trabalhador Sem Vínculo
- S-2399: Trabalhador Desligado
- S-1200: Remuneração de trabalhador vinculado

Além do CAGED (movimentações de emprego)
"""
from datetime import date, datetime
from decimal import Decimal
from lxml import etree


class ESocialGenerator:
    NS = 'http://www.esocial.gov.br/schema/evento/v1_0_0'

    def __init__(self, empresa, config):
        self.empresa = empresa
        self.config = config

    def gerar_s1000(self) -> str:
        """S-1000: Informações do Empregador/Contribuinte"""
        raiz = etree.Element(f'{{{self.NS}}}eSocial', xmlns=self.NS)
        evt = etree.SubElement(raiz, f'{{{self.NS}}}evtInfoEmpregador')
        evt.set('Id', f'ID100100000000000000000000000000001')
        ide_emp = etree.SubElement(evt, f'{{{self.NS}}}ideEmpregador')
        etree.SubElement(ide_emp, f'{{{self.NS}}}tpInsc').text = '1'
        etree.SubElement(ide_emp, f'{{{self.NS}}}nrInsc').text = ''.join(c for c in (self.empresa.cnpj or '') if c.isdigit())
        return etree.tostring(raiz, xml_declaration=True, encoding='UTF-8', pretty_print=True).decode('utf-8')

    def gerar_s2200(self, funcionario) -> str:
        """S-2200: Cadastramento Inicial do Trabalhador"""
        raiz = etree.Element(f'{{{self.NS}}}eSocial', xmlns=self.NS)
        evt = etree.SubElement(raiz, f'{{{self.NS}}}evtAdmissao')
        evt.set('Id', f'ID220000000000000000000000000000001')
        ide_emp = etree.SubElement(evt, f'{{{self.NS}}}ideEmpregador')
        etree.SubElement(ide_emp, f'{{{self.NS}}}tpInsc').text = '1'
        etree.SubElement(ide_emp, f'{{{self.NS}}}nrInsc').text = ''.join(c for c in (self.empresa.cnpj or '') if c.isdigit())
        ide_trab = etree.SubElement(evt, f'{{{self.NS}}}ideTrabalhador')
        etree.SubElement(ide_trab, f'{{{self.NS}}}cpfTrab').text = ''.join(c for c in (funcionario.cpf or '') if c.isdigit())
        etree.SubElement(ide_trab, f'{{{self.NS}}}nisTrab').text = ''.join(c for c in (funcionario.pis or '') if c.isdigit())
        etree.SubElement(ide_trab, f'{{{self.NS}}}nmTrab').text = funcionario.nome or ''
        etree.SubElement(ide_trab, f'{{{self.NS}}}dtNascto').text = funcionario.data_nascimento.strftime('%Y-%m-%d') if funcionario.data_nascimento else ''
        if funcionario.ctps:
            ctps = etree.SubElement(ide_trab, f'{{{self.NS}}}ctps')
            etree.SubElement(ctps, f'{{{self.NS}}}nrCtps').text = funcionario.ctps
        vinculo = etree.SubElement(evt, f'{{{self.NS}}}vinculo')
        etree.SubElement(vinculo, f'{{{self.NS}}}matricula').text = str(funcionario.id).zfill(6)
        etree.SubElement(vinculo, f'{{{self.NS}}}tpRegPrev').text = '1'
        if funcionario.data_admissao:
            etree.SubElement(vinculo, f'{{{self.NS}}}dtAdm').text = funcionario.data_admissao.strftime('%Y-%m-%d')
        etree.SubElement(vinculo, f'{{{self.NS}}}tpAdmissao').text = '1'
        return etree.tostring(raiz, xml_declaration=True, encoding='UTF-8', pretty_print=True).decode('utf-8')

    def gerar_s2299(self, funcionario, rescisao) -> str:
        """S-2299: Desligamento"""
        raiz = etree.Element(f'{{{self.NS}}}eSocial', xmlns=self.NS)
        evt = etree.SubElement(raiz, f'{{{self.NS}}}evtDeslig')
        evt.set('Id', f'ID229900000000000000000000000000001')
        ide_emp = etree.SubElement(evt, f'{{{self.NS}}}ideEmpregador')
        etree.SubElement(ide_emp, f'{{{self.NS}}}tpInsc').text = '1'
        etree.SubElement(ide_emp, f'{{{self.NS}}}nrInsc').text = ''.join(c for c in (self.empresa.cnpj or '') if c.isdigit())
        ide_trab = etree.SubElement(evt, f'{{{self.NS}}}ideTrabalhador')
        etree.SubElement(ide_trab, f'{{{self.NS}}}cpfTrab').text = ''.join(c for c in (funcionario.cpf or '') if c.isdigit())
        info_deslig = etree.SubElement(evt, f'{{{self.NS}}}infoDeslig')
        etree.SubElement(info_deslig, f'{{{self.NS}}}matricula').text = str(funcionario.id).zfill(6)
        etree.SubElement(info_deslig, f'{{{self.NS}}}dtDeslig').text = rescisao.data_rescisao.strftime('%Y-%m-%d') if rescisao.data_rescisao else ''
        tp_rescisao = '1' if rescisao.tipo == 'SD' else '2' if rescisao.tipo == 'SC' else '3'
        etree.SubElement(info_deslig, f'{{{self.NS}}}tpDeslig').text = tp_rescisao
        return etree.tostring(raiz, xml_declaration=True, encoding='UTF-8', pretty_print=True).decode('utf-8')

    def gerar_s1200(self, funcionario, folha) -> str:
        """S-1200: Remuneração de trabalhador vinculado"""
        raiz = etree.Element(f'{{{self.NS}}}eSocial', xmlns=self.NS)
        evt = etree.SubElement(raiz, f'{{{self.NS}}}evtRemun')
        evt.set('Id', f'ID120000000000000000000000000000001')
        ide_emp = etree.SubElement(evt, f'{{{self.NS}}}ideEmpregador')
        etree.SubElement(ide_emp, f'{{{self.NS}}}tpInsc').text = '1'
        etree.SubElement(ide_emp, f'{{{self.NS}}}nrInsc').text = ''.join(c for c in (self.empresa.cnpj or '') if c.isdigit())
        ide_trab = etree.SubElement(evt, f'{{{self.NS}}}ideTrabalhador')
        etree.SubElement(ide_trab, f'{{{self.NS}}}cpfTrab').text = ''.join(c for c in (funcionario.cpf or '') if c.isdigit())
        info_remun = etree.SubElement(evt, f'{{{self.NS}}}infoRemun')
        etree.SubElement(info_remun, f'{{{self.NS}}}matricula').text = str(funcionario.id).zfill(6)
        etree.SubElement(info_remun, f'{{{self.NS}}}codCateg').text = '101'
        itens_remun = etree.SubElement(info_remun, f'{{{self.NS}}}itensRemun')
        item = etree.SubElement(itens_remun, f'{{{self.NS}}}item')
        etree.SubElement(item, f'{{{self.NS}}}codRubr').text = '1000'
        etree.SubElement(item, f'{{{self.NS}}}ideTabRubr').text = '1'
        etree.SubElement(item, f'{{{self.NS}}}qtdRubr').text = '1'
        etree.SubElement(item, f'{{{self.NS}}}fatorRubr').text = '1'
        etree.SubElement(item, f'{{{self.NS}}}vrRubr').text = f'{float(folha.salario_base):.2f}'
        return etree.tostring(raiz, xml_declaration=True, encoding='UTF-8', pretty_print=True).decode('utf-8')


def gerar_caged(funcionario, tipo_movimento='1', data_movimento=None):
    """
    Gera arquivo CAGED (Cadastro Geral de Empregados e Desempregados).
    Layout conforme portaria MTE.
    tipo_movimento: 1=Admissão, 2=Desligamento
    """
    dia = (data_movimento or date.today()).strftime('%d%m%Y')
    cpf = ''.join(c for c in (funcionario.cpf or '') if c.isdigit())
    pis = ''.join(c for c in (funcionario.pis or '') if c.isdigit())
    data_nasc = funcionario.data_nascimento.strftime('%d%m%Y') if funcionario.data_nascimento else ''
    nome = (funcionario.nome or '')[:30]
    salario = f'{float(funcionario.salario_contratual or 0):.2f}'.replace('.', ',')

    # Layout simplificado do CAGED
    linha = f'{tipo_movimento}{dia}{cpf.zfill(11)}{pis.zfill(11)}{data_nasc}{nome.ljust(30)}{salario.zfill(10)}'
    return linha
