"""
Emissor SAT - Integração com o Sistema Autenticador e Transmissor.
Implementa a comunicação com o SAT CF-e para emissão de cupons fiscais.

Funcionamento:
- O SAT possui uma DLL (sat.dll) que faz a comunicação com o equipamento
- A comunicação é feita via JSON-RPC sobre pipe nomeado ou via DLL diretamente
- Utiliza certificado digital A1 para assinatura

Referência: Manual de Integração SAT - ER SAT 3.0
"""
import json
import os
import platform
import subprocess
import uuid
from datetime import datetime
from decimal import Decimal


def _gerar_numero_sessao():
    return str(uuid.uuid4().int)[:8]


def _calcular_assinatura_qrcode(cnpj, numero_cfe, valor, cnpj_software_house):
    """Calcula o código de assinatura do QR Code conforme manual SAT"""
    from hashlib import sha1
    dados = f'{cnpj}{numero_cfe}{valor}{cnpj_software_house}'
    return sha1(dados.encode('utf-8')).hexdigest().upper()


class SATEmissor:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.caminho_dll = self.config.get('caminho_dll', 'C:\\SAT\\sat.dll')
        self.codigo_ativacao = self.config.get('codigo_ativacao', '12345678')
        self.cnpj_software_house = self.config.get('cnpj_software_house', '')
        self.ambiente = self.config.get('ambiente', '2')  # 1=Produção, 2=Homologação
        self.numero_caixa = self.config.get('numero_caixa', '001')

    def enviar_dados_venda(self, xml_cfe: str) -> dict:
        """
        Envia dados de venda para o SAT.
        Retorna o resultado com CF-e, QRCode e assinatura.
        """
        if self.ambiente == '2':
            return self._simular_envio(xml_cfe)
        return self._enviar_sat_real(xml_cfe)

    def cancelar_cfe(self, chave_cfe: str, xml_cancelamento: str) -> dict:
        """Cancela um CF-e já emitido"""
        if self.ambiente == '2':
            return self._simular_cancelamento(chave_cfe)
        return self._cancelar_sat_real(chave_cfe, xml_cancelamento)

    def _simular_envio(self, xml_cfe: str) -> dict:
        """Modo simulado para testes/homologação"""
        from random import randint
        ns = _gerar_numero_sessao()
        numero_cfe = f'{self.numero_caixa}{randint(100000, 999999)}'
        cnpj_limpo = ''.join(c for c in self.cnpj_software_house if c.isdigit())
        assinatura = _calcular_assinatura_qrcode(
            self.cnpj_software_house, numero_cfe, '0.00', cnpj_limpo
        )
        return {
            'sucesso': True,
            'numero_sessao': ns,
            'codigo': '6000',
            'mensagem': 'CF-e emitido com sucesso (simulado)',
            'numero_cfe': numero_cfe,
            'chave_acesso': f'{numero_cfe}{assinatura[:10]}',
            'assinatura': assinatura,
            'qr_code': f'https://homologacao.sat.fazenda.sp.gov.br/{assinatura}',
            'xml_cfe': xml_cfe,
        }

    def _simular_cancelamento(self, chave: str) -> dict:
        return {
            'sucesso': True,
            'numero_sessao': _gerar_numero_sessao(),
            'codigo': '7000',
            'mensagem': 'CF-e cancelado com sucesso (simulado)',
            'chave_cancelada': chave,
        }

    def _enviar_sat_real(self, xml_cfe: str) -> dict:
        """
        Envio real via DLL do SAT.
        A DLL é fornecida pelo fabricante do SAT e segue o padrão ER SAT 3.0.
        """
        if not os.path.exists(self.caminho_dll):
            raise FileNotFoundError(f'DLL do SAT não encontrada: {self.caminho_dll}')

        if platform.system() == 'Windows':
            return self._enviar_via_dll_windows(xml_cfe)
        else:
            raise RuntimeError('SAT real suportado apenas em Windows')

    def _enviar_via_dll_windows(self, xml_cfe: str) -> dict:
        """
        Comunicação com SAT via DLL em Windows.
        Utiliza ctypes para chamar a função de envio da DLL.
        """
        try:
            from ctypes import CDLL, c_char_p, c_int, create_string_buffer
            sat = CDLL(self.caminho_dll)

            ns = _gerar_numero_sessao()

            # Função ConsultarSAT (disponível em todas as DLLs)
            consultar = sat.ConsultarSAT
            consultar.argtypes = [c_int, c_char_p]
            consultar.restype = c_char_p
            resultado = consultar(c_int(int(self.numero_caixa)), c_char_p(self.codigo_ativacao.encode('utf-8')))
            if resultado:
                return json.loads(resultado.decode('utf-8'))

            # Função EnviarDadosVenda
            enviar = sat.EnviarDadosVenda
            enviar.argtypes = [c_int, c_char_p, c_char_p]
            enviar.restype = c_char_p
            resultado = enviar(
                c_int(int(ns)),
                c_char_p(self.codigo_ativacao.encode('utf-8')),
                c_char_p(xml_cfe.encode('utf-8'))
            )
            if resultado:
                return json.loads(resultado.decode('utf-8'))

            return {'sucesso': False, 'erro': 'Sem resposta da DLL do SAT'}
        except Exception as e:
            return {'sucesso': False, 'erro': f'Erro comunicação SAT: {str(e)}'}

    def _cancelar_sat_real(self, chave_cfe: str, xml_cancelamento: str) -> dict:
        """Cancelamento via DLL do SAT"""
        try:
            from ctypes import CDLL, c_char_p, c_int
            sat = CDLL(self.caminho_dll)
            ns = _gerar_numero_sessao()

            cancelar = sat.CancelarUltimaVenda
            cancelar.argtypes = [c_int, c_char_p, c_char_p, c_char_p]
            cancelar.restype = c_char_p
            resultado = cancelar(
                c_int(int(ns)),
                c_char_p(self.codigo_ativacao.encode('utf-8')),
                c_char_p(chave_cfe.encode('utf-8')),
                c_char_p(xml_cancelamento.encode('utf-8'))
            )
            if resultado:
                return json.loads(resultado.decode('utf-8'))
            return {'sucesso': False, 'erro': 'Sem resposta no cancelamento SAT'}
        except Exception as e:
            return {'sucesso': False, 'erro': f'Erro cancelamento SAT: {str(e)}'}


def gerar_xml_cfe(venda, empresa, config_fiscal, itens) -> str:
    """
    Gera XML do CF-e SAT conforme leiaute ER SAT 3.0.
    Retorna string XML assinável.
    """
    from lxml import etree
    ns_sat = 'http://www.fazenda.sp.gov.br/sat'

    raiz = etree.Element(f'{{{ns_sat}}}CFe', xmlns=ns_sat)
    raiz.set('versao', '0.09')
    raiz.set('xmlns', ns_sat)

    infCFe = etree.SubElement(raiz, f'{{{ns_sat}}}infCFe')
    infCFe.set('versao', '0.09')
    versao = '0.09'

    ide = etree.SubElement(infCFe, f'{{{ns_sat}}}ide')
    etree.SubElement(ide, f'{{{ns_sat}}}cUF').text = '35'
    etree.SubElement(ide, f'{{{ns_sat}}}cNF').text = str(config_fiscal.proximo_numero_nfce or 1).zfill(9)[:8]
    etree.SubElement(ide, f'{{{ns_sat}}}natOp').text = 'Venda a consumidor'
    etree.SubElement(ide, f'{{{ns_sat}}}indPag').text = '0'
    etree.SubElement(ide, f'{{{ns_sat}}}mod').text = '59'
    etree.SubElement(ide, f'{{{ns_sat}}}serie').text = str(config_fiscal.serie_nfce or 1).zfill(3)
    etree.SubElement(ide, f'{{{ns_sat}}}nCFe').text = str(config_fiscal.proximo_numero_nfce or 1).zfill(9)
    etree.SubElement(ide, f'{{{ns_sat}}}dhEmi').text = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    etree.SubElement(ide, f'{{{ns_sat}}}tpAmb').text = config_fiscal.ambiente or '2'
    etree.SubElement(ide, f'{{{ns_sat}}}cDV').text = ''
    etree.SubElement(ide, f'{{{ns_sat}}}tpEmis').text = '1'
    etree.SubElement(ide, f'{{{ns_sat}}}cMunFG').text = empresa.cidade_ibge or ''
    etree.SubElement(ide, f'{{{ns_sat}}}munFG').text = empresa.cidade or ''

    emit = etree.SubElement(infCFe, f'{{{ns_sat}}}emit')
    etree.SubElement(emit, f'{{{ns_sat}}}CNPJ').text = ''.join(c for c in (empresa.cnpj or '') if c.isdigit())
    etree.SubElement(emit, f'{{{ns_sat}}}xNome').text = empresa.razao_social or empresa.nome_fantasia or ''
    etree.SubElement(emit, f'{{{ns_sat}}}xFant').text = empresa.nome_fantasia or ''
    etree.SubElement(emit, f'{{{ns_sat}}}IE').text = (empresa.ie or '').replace('.', '').replace('-', '')
    etree.SubElement(emit, f'{{{ns_sat}}}IM').text = (empresa.im or '').replace('.', '').replace('-', '')
    etree.SubElement(emit, f'{{{ns_sat}}}cRegTrib').text = config_fiscal.regime_tributario or '3'
    indRatISSQN = 'N' if config_fiscal.regime_tributario == '3' else 'S' if config_fiscal.regime_tributario == '1' else 'N'
    etree.SubElement(emit, f'{{{ns_sat}}}indRatISSQN').text = indRatISSQN

    dest = etree.SubElement(infCFe, f'{{{ns_sat}}}dest')
    if venda.cliente:
        cpf_cnpj = ''.join(c for c in (venda.cliente.cpf_cnpj or '') if c.isdigit())
        if len(cpf_cnpj) > 11:
            etree.SubElement(dest, f'{{{ns_sat}}}CNPJ').text = cpf_cnpj
        else:
            etree.SubElement(dest, f'{{{ns_sat}}}CPF').text = cpf_cnpj if cpf_cnpj else '00000000000'
        etree.SubElement(dest, f'{{{ns_sat}}}xNome').text = venda.cliente.nome or 'CONSUMIDOR'

    for idx, item in enumerate(itens, 1):
        det = etree.SubElement(infCFe, f'{{{ns_sat}}}det')
        det.set('nItem', str(idx))
        prod = etree.SubElement(det, f'{{{ns_sat}}}prod')
        etree.SubElement(prod, f'{{{ns_sat}}}cProd').text = str(item.produto_id)
        etree.SubElement(prod, f'{{{ns_sat}}}xProd').text = item.produto.nome
        etree.SubElement(prod, f'{{{ns_sat}}}NCM').text = (item.produto.ncm or '00').replace('.', '')[:8]
        etree.SubElement(prod, f'{{{ns_sat}}}CFOP').text = '5102'
        etree.SubElement(prod, f'{{{ns_sat}}}uCom').text = item.produto.unidade or 'UN'
        etree.SubElement(prod, f'{{{ns_sat}}}qCom').text = f'{float(item.quantidade):.4f}'
        etree.SubElement(prod, f'{{{ns_sat}}}vUnCom').text = f'{float(item.preco_unitario):.4f}'
        etree.SubElement(prod, f'{{{ns_sat}}}vProd').text = f'{float(item.subtotal):.2f}'
        etree.SubElement(prod, f'{{{ns_sat}}}indRegra').text = 'A'

        imposto = etree.SubElement(det, f'{{{ns_sat}}}imposto')
        etc = etree.SubElement(imposto, f'{{{ns_sat}}}vItem12741').text = '0.00'
        icms = etree.SubElement(imposto, f'{{{ns_sat}}}ICMS')
        icms00 = etree.SubElement(icms, f'{{{ns_sat}}}ICMS00')
        etree.SubElement(icms00, f'{{{ns_sat}}}Orig').text = '0'
        etree.SubElement(icms00, f'{{{ns_sat}}}CST').text = '00'
        etree.SubElement(icms00, f'{{{ns_sat}}}vBC').text = f'{float(item.subtotal):.2f}'
        etree.SubElement(icms00, f'{{{ns_sat}}}pICMS').text = '0.00'
        etree.SubElement(icms00, f'{{{ns_sat}}}vICMS').text = '0.00'
        pis = etree.SubElement(imposto, f'{{{ns_sat}}}PIS')
        pis_outr = etree.SubElement(pis, f'{{{ns_sat}}}PISOutr')
        etree.SubElement(pis_outr, f'{{{ns_sat}}}CST').text = '99'
        etree.SubElement(pis_outr, f'{{{ns_sat}}}vBC').text = '0.00'
        etree.SubElement(pis_outr, f'{{{ns_sat}}}pPIS').text = '0.00'
        etree.SubElement(pis_outr, f'{{{ns_sat}}}vPIS').text = '0.00'
        cofins = etree.SubElement(imposto, f'{{{ns_sat}}}COFINS')
        cofins_outr = etree.SubElement(cofins, f'{{{ns_sat}}}COFINSOutr')
        etree.SubElement(cofins_outr, f'{{{ns_sat}}}CST').text = '99'
        etree.SubElement(cofins_outr, f'{{{ns_sat}}}vBC').text = '0.00'
        etree.SubElement(cofins_outr, f'{{{ns_sat}}}pCOFINS').text = '0.00'
        etree.SubElement(cofins_outr, f'{{{ns_sat}}}vCOFINS').text = '0.00'

    total = etree.SubElement(infCFe, f'{{{ns_sat}}}total')
    icmstot = etree.SubElement(total, f'{{{ns_sat}}}ICMSTot')
    etree.SubElement(icmstot, f'{{{ns_sat}}}vBC').text = f'{float(venda.total):.2f}'
    etree.SubElement(icmstot, f'{{{ns_sat}}}vICMS').text = '0.00'
    etree.SubElement(icmstot, f'{{{ns_sat}}}vProd').text = f'{float(venda.subtotal):.2f}'
    etree.SubElement(icmstot, f'{{{ns_sat}}}vDesc').text = f'{float(venda.desconto):.2f}'
    etree.SubElement(icmstot, f'{{{ns_sat}}}vPIS').text = '0.00'
    etree.SubElement(icmstot, f'{{{ns_sat}}}vCOFINS').text = '0.00'
    etree.SubElement(icmstot, f'{{{ns_sat}}}vOutro').text = '0.00'
    etree.SubElement(icmstot, f'{{{ns_sat}}}vCFe').text = f'{float(venda.total):.2f}'
    etree.SubElement(icmstot, f'{{{ns_sat}}}vCFeLei12741').text = '0.00'

    pgto = etree.SubElement(infCFe, f'{{{ns_sat}}}pgto')
    for pg in venda.pagamentos:
        mp = etree.SubElement(pgto, f'{{{ns_sat}}}MP')
        etree.SubElement(mp, f'{{{ns_sat}}}cMP').text = _codigo_mp(pg.forma_pagamento)
        etree.SubElement(mp, f'{{{ns_sat}}}vMP').text = f'{float(pg.valor):.2f}'
        if pg.troco and float(pg.troco) > 0:
            etree.SubElement(mp, f'{{{ns_sat}}}vTroco').text = f'{float(pg.troco):.2f}'

    infAdic = etree.SubElement(infCFe, f'{{{ns_sat}}}infAdic')
    etree.SubElement(infAdic, f'{{{ns_sat}}}infCpl').text = 'CF-e gerado pelo ERP Supermercado'

    return etree.tostring(raiz, xml_declaration=True, encoding='UTF-8', pretty_print=True).decode('utf-8')


def _codigo_mp(forma):
    """Mapeia forma de pagamento para código SAT"""
    mapa = {
        'DINHEIRO': '01', 'CHEQUE': '02', 'CREDITO': '03', 'DEBITO': '04',
        'CRÉDITO': '03', 'DÉBITO': '04',
        'CREDITO_LOJA': '05', 'CRED_LOJA': '05',
        'VALE_ALIMENTACAO': '06', 'VALE_REFEICAO': '07', 'VALE_PRESENTE': '08',
        'VALE_COMBUSTIVEL': '09', 'DUPLICATA': '10',
        'PIX': '17', 'OUTROS': '99',
    }
    return mapa.get(forma.upper().strip(), '99')
