import html
from lxml import etree
from datetime import datetime
from app.nfe.utils import gerar_chave, format_cnpj, format_cpf, format_telefone, UF_CODIGOS


def _sanitize(valor):
    """Remove caracteres que possam quebrar o XML"""
    if valor is None:
        return ''
    return html.escape(str(valor), quote=True).replace(']]>', '')

NS_NFE = 'http://www.portalfiscal.inf.br/nfe'


def xml_nfce(doc, config, empresa):
    """Gera XML completo de NFC-e conforme schema oficial"""
    ns = f'{{{NS_NFE}}}'

    raiz = etree.Element(ns + 'NFe', xmlns=NS_NFE)
    infNFe = etree.SubElement(raiz, ns + 'infNFe')
    infNFe.set('versao', '4.00')
    infNFe.set('Id', f'NFe{doc.chave_acesso}')

    ide = etree.SubElement(infNFe, ns + 'ide')
    etree.SubElement(ide, ns + 'cUF').text = UF_CODIGOS.get(empresa.uf, '35')
    etree.SubElement(ide, ns + 'cNF').text = doc.chave_acesso[35:43]
    etree.SubElement(ide, ns + 'natOp').text = doc.natureza_operacao or 'Venda'
    etree.SubElement(ide, ns + 'mod').text = '65'
    etree.SubElement(ide, ns + 'serie').text = str(doc.serie)
    etree.SubElement(ide, ns + 'nNF').text = str(doc.numero)
    etree.SubElement(ide, ns + 'dhEmi').text = doc.data_emissao.strftime('%Y-%m-%dT%H:%M:%S-03:00')
    etree.SubElement(ide, ns + 'tpNF').text = '1'
    etree.SubElement(ide, ns + 'idDest').text = '1'
    etree.SubElement(ide, ns + 'cMunFG').text = '3550308'
    etree.SubElement(ide, ns + 'tpImp').text = '4'
    etree.SubElement(ide, ns + 'tpEmis').text = '1'
    etree.SubElement(ide, ns + 'cDV').text = doc.chave_acesso[43]
    etree.SubElement(ide, ns + 'tpAmb').text = config.ambiente
    etree.SubElement(ide, ns + 'finNFe').text = '1'
    etree.SubElement(ide, ns + 'indFinal').text = '1'
    etree.SubElement(ide, ns + 'indPres').text = '1'
    etree.SubElement(ide, ns + 'procEmi').text = '0'
    etree.SubElement(ide, ns + 'verProc').text = 'ERP Supermercado 1.0'

    emit = etree.SubElement(infNFe, ns + 'emit')
    etree.SubElement(emit, ns + 'CNPJ').text = format_cnpj(empresa.cnpj)
    etree.SubElement(emit, ns + 'xNome').text = empresa.razao_social or empresa.nome_fantasia or ''
    etree.SubElement(emit, ns + 'xFant').text = empresa.nome_fantasia or ''
    enderEmit = etree.SubElement(emit, ns + 'enderEmit')
    etree.SubElement(enderEmit, ns + 'xLgr').text = empresa.endereco or ''
    etree.SubElement(enderEmit, ns + 'nro').text = empresa.numero or ''
    etree.SubElement(enderEmit, ns + 'xBairro').text = empresa.bairro or ''
    etree.SubElement(enderEmit, ns + 'xCpl').text = ''
    etree.SubElement(enderEmit, ns + 'cMun').text = '3550308'
    etree.SubElement(enderEmit, ns + 'xMun').text = empresa.cidade or ''
    etree.SubElement(enderEmit, ns + 'UF').text = empresa.uf or 'SP'
    etree.SubElement(enderEmit, ns + 'CEP').text = (empresa.cep or '').replace('-', '')
    etree.SubElement(enderEmit, ns + 'cPais').text = '1058'
    etree.SubElement(enderEmit, ns + 'xPais').text = 'BRASIL'
    etree.SubElement(enderEmit, ns + 'fone').text = format_telefone(empresa.telefone)
    etree.SubElement(emit, ns + 'IE').text = empresa.ie or ''
    etree.SubElement(emit, ns + 'CRT').text = config.regime_tributario

    if doc.cliente:
        dest = etree.SubElement(infNFe, ns + 'dest')
        if doc.cliente.cpf_cnpj and len(doc.cliente.cpf_cnpj.replace('.', '').replace('-', '').replace('/', '')) > 11:
            etree.SubElement(dest, ns + 'CNPJ').text = format_cnpj(doc.cliente.cpf_cnpj)
        else:
            etree.SubElement(dest, ns + 'CPF').text = format_cpf(doc.cliente.cpf_cnpj) if doc.cliente.cpf_cnpj else ''
        etree.SubElement(dest, ns + 'xNome').text = doc.cliente.nome or 'CONSUMIDOR'
        enderDest = etree.SubElement(dest, ns + 'enderDest')
        etree.SubElement(enderDest, ns + 'xLgr').text = doc.cliente.endereco or ''
        etree.SubElement(enderDest, ns + 'nro').text = doc.cliente.numero or ''
        etree.SubElement(enderDest, ns + 'xBairro').text = doc.cliente.bairro or ''
        etree.SubElement(enderDest, ns + 'cMun').text = '3550308'
        etree.SubElement(enderDest, ns + 'xMun').text = doc.cliente.cidade or ''
        etree.SubElement(enderDest, ns + 'UF').text = doc.cliente.uf or 'SP'
        etree.SubElement(enderDest, ns + 'CEP').text = (doc.cliente.cep or '').replace('-', '')
        etree.SubElement(enderDest, ns + 'cPais').text = '1058'
        etree.SubElement(enderDest, ns + 'xPais').text = 'BRASIL'
        etree.SubElement(enderDest, ns + 'fone').text = format_telefone(doc.cliente.telefone)
        etree.SubElement(dest, ns + 'indIEDest').text = '9'

    det_idx = 1
    for item in doc.itens:
        det = etree.SubElement(infNFe, ns + 'det')
        det.set('nItem', str(det_idx))
        prod = etree.SubElement(det, ns + 'prod')
        etree.SubElement(prod, ns + 'cProd').text = str(item.produto_id)
        etree.SubElement(prod, ns + 'cEAN').text = item.produto.codigo_barras or ''
        etree.SubElement(prod, ns + 'xProd').text = item.produto.nome
        etree.SubElement(prod, ns + 'NCM').text = item.ncm or '00'
        etree.SubElement(prod, ns + 'CEST').text = item.cest or '' if item.cest else None
        etree.SubElement(prod, ns + 'CFOP').text = item.cfop or '5102'
        etree.SubElement(prod, ns + 'uCom').text = item.produto.unidade or 'UN'
        etree.SubElement(prod, ns + 'qCom').text = f'{float(item.quantidade):.4f}'
        etree.SubElement(prod, ns + 'vUnCom').text = f'{float(item.valor_unitario):.4f}'
        etree.SubElement(prod, ns + 'vProd').text = f'{float(item.valor_total):.2f}'
        etree.SubElement(prod, ns + 'cEANTrib').text = item.produto.codigo_barras or ''
        etree.SubElement(prod, ns + 'uTrib').text = item.produto.unidade or 'UN'
        etree.SubElement(prod, ns + 'qTrib').text = f'{float(item.quantidade):.4f}'
        etree.SubElement(prod, ns + 'vUnTrib').text = f'{float(item.valor_unitario):.4f}'
        etree.SubElement(prod, ns + 'indTot').text = '1'

        imposto = etree.SubElement(det, ns + 'imposto')
        etree.SubElement(imposto, ns + 'vTotTrib').text = '0.00'

        icms = etree.SubElement(imposto, ns + 'ICMS')
        icms00 = etree.SubElement(icms, ns + 'ICMS00')
        etree.SubElement(icms00, ns + 'orig').text = '0'
        etree.SubElement(icms00, ns + 'CST').text = item.cst_icms or '00'
        etree.SubElement(icms00, ns + 'modBC').text = '3'
        etree.SubElement(icms00, ns + 'vBC').text = f'{float(item.valor_total):.2f}'
        etree.SubElement(icms00, ns + 'pICMS').text = f'{float(item.aliquota_icms):.2f}'
        v_icms = float(item.valor_total) * float(item.aliquota_icms) / 100
        etree.SubElement(icms00, ns + 'vICMS').text = f'{v_icms:.2f}'

        pis = etree.SubElement(imposto, ns + 'PIS')
        pis_outr = etree.SubElement(pis, ns + 'PISOutr')
        etree.SubElement(pis_outr, ns + 'CST').text = '99'
        etree.SubElement(pis_outr, ns + 'vBC').text = '0.00'
        etree.SubElement(pis_outr, ns + 'pPIS').text = '0.00'
        etree.SubElement(pis_outr, ns + 'vPIS').text = '0.00'

        cofins = etree.SubElement(imposto, ns + 'COFINS')
        cofins_outr = etree.SubElement(cofins, ns + 'COFINSOutr')
        etree.SubElement(cofins_outr, ns + 'CST').text = '99'
        etree.SubElement(cofins_outr, ns + 'vBC').text = '0.00'
        etree.SubElement(cofins_outr, ns + 'pCOFINS').text = '0.00'
        etree.SubElement(cofins_outr, ns + 'vCOFINS').text = '0.00'

        det_idx += 1

    total = etree.SubElement(infNFe, ns + 'total')
    icmsTot = etree.SubElement(total, ns + 'ICMSTot')
    etree.SubElement(icmsTot, ns + 'vBC').text = f'{float(doc.base_calculo):.2f}'
    etree.SubElement(icmsTot, ns + 'vICMS').text = f'{float(doc.valor_icms):.2f}'
    etree.SubElement(icmsTot, ns + 'vICMSDeson').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vFCP').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vBCST').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vST').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vFCPST').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vFCPSTRet').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vProd').text = f'{float(doc.valor_produtos):.2f}'
    etree.SubElement(icmsTot, ns + 'vFrete').text = f'{float(doc.valor_frete):.2f}'
    etree.SubElement(icmsTot, ns + 'vSeg').text = f'{float(doc.valor_seguro):.2f}'
    etree.SubElement(icmsTot, ns + 'vDesc').text = f'{float(doc.valor_desconto):.2f}'
    etree.SubElement(icmsTot, ns + 'vII').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vIPI').text = f'{float(doc.valor_ipi):.2f}'
    etree.SubElement(icmsTot, ns + 'vIPIDevol').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vPIS').text = f'{float(doc.valor_pis):.2f}'
    etree.SubElement(icmsTot, ns + 'vCOFINS').text = f'{float(doc.valor_cofins):.2f}'
    etree.SubElement(icmsTot, ns + 'vOutro').text = f'{float(doc.valor_outras):.2f}'
    etree.SubElement(icmsTot, ns + 'vNF').text = f'{float(doc.valor_total):.2d}'
    etree.SubElement(icmsTot, ns + 'vTotTrib').text = f'{float(doc.valor_total_tributos):.2f}'

    transp = etree.SubElement(infNFe, ns + 'transp')
    etree.SubElement(transp, ns + 'modFrete').text = '9'

    pag = etree.SubElement(infNFe, ns + 'pag')
    detPag = etree.SubElement(pag, ns + 'detPag')
    etree.SubElement(detPag, ns + 'indPag').text = '0'
    etree.SubElement(detPag, ns + 'tPag').text = '01'
    etree.SubElement(detPag, ns + 'vPag').text = f'{float(doc.valor_total):.2f}'

    infAdic = etree.SubElement(infNFe, ns + 'infAdic')
    etree.SubElement(infAdic, ns + 'infCpl').text = 'NFC-e gerada pelo ERP Supermercado'

    xml_str = etree.tostring(raiz, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    return xml_str


def xml_cancelamento(doc, config, empresa, justificativa):
    """Gera XML de evento de cancelamento"""
    ns = f'{{{NS_NFE}}}'
    agora = datetime.now()
    sequencia_evento = 1

    raiz = etree.Element('evento', xmlns=NS_NFE, versao='1.00')
    infEvento = etree.SubElement(raiz, ns + 'infEvento')
    infEvento.set('Id', f'ID110111{doc.chave_acesso}{sequencia_evento:02d}')

    etree.SubElement(infEvento, ns + 'cOrgao').text = UF_CODIGOS.get(empresa.uf, '35')
    etree.SubElement(infEvento, ns + 'tpAmb').text = config.ambiente
    etree.SubElement(infEvento, ns + 'CNPJ').text = format_cnpj(empresa.cnpj)
    etree.SubElement(infEvento, ns + 'chNFe').text = doc.chave_acesso
    etree.SubElement(infEvento, ns + 'dhEvento').text = agora.strftime('%Y-%m-%dT%H:%M:%S-03:00')
    etree.SubElement(infEvento, ns + 'tpEvento').text = '110111'
    etree.SubElement(infEvento, ns + 'nSeqEvento').text = str(sequencia_evento)
    etree.SubElement(infEvento, ns + 'verEvento').text = '1.00'

    detEvento = etree.SubElement(infEvento, ns + 'detEvento')
    etree.SubElement(detEvento, ns + 'descEvento').text = 'Cancelamento'
    etree.SubElement(detEvento, ns + 'xJust').text = justificativa

    return etree.tostring(raiz, xml_declaration=True, encoding='UTF-8', pretty_print=True)


def xml_nfe(doc, config, empresa):
    """Gera XML completo de NF-e (modelo 55) conforme schema oficial NT 2023.001 v1.70"""
    ns = f'{{{NS_NFE}}}'

    raiz = etree.Element(ns + 'NFe', xmlns=NS_NFE)
    infNFe = etree.SubElement(raiz, ns + 'infNFe')
    infNFe.set('versao', '4.00')
    infNFe.set('Id', f'NFe{doc.chave_acesso}')

    ide = etree.SubElement(infNFe, ns + 'ide')
    etree.SubElement(ide, ns + 'cUF').text = UF_CODIGOS.get(empresa.uf, '35')
    etree.SubElement(ide, ns + 'cNF').text = doc.chave_acesso[35:43]
    etree.SubElement(ide, ns + 'natOp').text = doc.natureza_operacao or 'Venda'
    etree.SubElement(ide, ns + 'mod').text = '55'
    etree.SubElement(ide, ns + 'serie').text = str(doc.serie)
    etree.SubElement(ide, ns + 'nNF').text = str(doc.numero)
    etree.SubElement(ide, ns + 'dhEmi').text = doc.data_emissao.strftime('%Y-%m-%dT%H:%M:%S-03:00')
    etree.SubElement(ide, ns + 'dhSaiEnt').text = doc.data_emissao.strftime('%Y-%m-%dT%H:%M:%S-03:00')
    etree.SubElement(ide, ns + 'tpNF').text = '1'
    etree.SubElement(ide, ns + 'idDest').text = '1'
    etree.SubElement(ide, ns + 'cMunFG').text = '3550308'
    etree.SubElement(ide, ns + 'tpImp').text = '1'
    etree.SubElement(ide, ns + 'tpEmis').text = '1'
    etree.SubElement(ide, ns + 'cDV').text = doc.chave_acesso[43]
    etree.SubElement(ide, ns + 'tpAmb').text = config.ambiente
    etree.SubElement(ide, ns + 'finNFe').text = '1'
    etree.SubElement(ide, ns + 'indFinal').text = '1'
    etree.SubElement(ide, ns + 'indPres').text = '1'
    etree.SubElement(ide, ns + 'procEmi').text = '0'
    etree.SubElement(ide, ns + 'verProc').text = 'ERP Supermercado 1.0'

    emit = etree.SubElement(infNFe, ns + 'emit')
    etree.SubElement(emit, ns + 'CNPJ').text = format_cnpj(empresa.cnpj)
    etree.SubElement(emit, ns + 'xNome').text = empresa.razao_social or empresa.nome_fantasia or ''
    etree.SubElement(emit, ns + 'xFant').text = empresa.nome_fantasia or ''
    enderEmit = etree.SubElement(emit, ns + 'enderEmit')
    etree.SubElement(enderEmit, ns + 'xLgr').text = empresa.endereco or ''
    etree.SubElement(enderEmit, ns + 'nro').text = empresa.numero or ''
    etree.SubElement(enderEmit, ns + 'xBairro').text = empresa.bairro or ''
    etree.SubElement(enderEmit, ns + 'xCpl').text = ''
    etree.SubElement(enderEmit, ns + 'cMun').text = '3550308'
    etree.SubElement(enderEmit, ns + 'xMun').text = empresa.cidade or ''
    etree.SubElement(enderEmit, ns + 'UF').text = empresa.uf or 'SP'
    etree.SubElement(enderEmit, ns + 'CEP').text = (empresa.cep or '').replace('-', '')
    etree.SubElement(enderEmit, ns + 'cPais').text = '1058'
    etree.SubElement(enderEmit, ns + 'xPais').text = 'BRASIL'
    etree.SubElement(enderEmit, ns + 'fone').text = format_telefone(empresa.telefone)
    etree.SubElement(emit, ns + 'IE').text = empresa.ie or ''
    etree.SubElement(emit, ns + 'CRT').text = config.regime_tributario

    if doc.cliente:
        dest = etree.SubElement(infNFe, ns + 'dest')
        if doc.cliente.cpf_cnpj and len(doc.cliente.cpf_cnpj.replace('.', '').replace('-', '').replace('/', '')) > 11:
            etree.SubElement(dest, ns + 'CNPJ').text = format_cnpj(doc.cliente.cpf_cnpj)
        else:
            etree.SubElement(dest, ns + 'CPF').text = format_cpf(doc.cliente.cpf_cnpj) if doc.cliente.cpf_cnpj else ''
        etree.SubElement(dest, ns + 'xNome').text = doc.cliente.nome or 'CONSUMIDOR'
        enderDest = etree.SubElement(dest, ns + 'enderDest')
        etree.SubElement(enderDest, ns + 'xLgr').text = doc.cliente.endereco or ''
        etree.SubElement(enderDest, ns + 'nro').text = doc.cliente.numero or ''
        etree.SubElement(enderDest, ns + 'xBairro').text = doc.cliente.bairro or ''
        etree.SubElement(enderDest, ns + 'cMun').text = '3550308'
        etree.SubElement(enderDest, ns + 'xMun').text = doc.cliente.cidade or ''
        etree.SubElement(enderDest, ns + 'UF').text = doc.cliente.uf or 'SP'
        etree.SubElement(enderDest, ns + 'CEP').text = (doc.cliente.cep or '').replace('-', '')
        etree.SubElement(enderDest, ns + 'cPais').text = '1058'
        etree.SubElement(enderDest, ns + 'xPais').text = 'BRASIL'
        etree.SubElement(enderDest, ns + 'fone').text = format_telefone(doc.cliente.telefone)
        etree.SubElement(dest, ns + 'indIEDest').text = '9'

    det_idx = 1
    for item in doc.itens:
        det = etree.SubElement(infNFe, ns + 'det')
        det.set('nItem', str(det_idx))
        prod = etree.SubElement(det, ns + 'prod')
        etree.SubElement(prod, ns + 'cProd').text = str(item.produto_id)
        etree.SubElement(prod, ns + 'cEAN').text = item.produto.codigo_barras or ''
        etree.SubElement(prod, ns + 'xProd').text = item.produto.nome
        etree.SubElement(prod, ns + 'NCM').text = item.ncm or item.produto.ncm or '00'
        etree.SubElement(prod, ns + 'CEST').text = item.cest or '' if item.cest else None
        etree.SubElement(prod, ns + 'CFOP').text = item.cfop or doc.cfop or '5102'
        etree.SubElement(prod, ns + 'uCom').text = item.produto.unidade or 'UN'
        etree.SubElement(prod, ns + 'qCom').text = f'{float(item.quantidade):.4f}'
        etree.SubElement(prod, ns + 'vUnCom').text = f'{float(item.valor_unitario):.4f}'
        etree.SubElement(prod, ns + 'vProd').text = f'{float(item.valor_total):.2f}'
        etree.SubElement(prod, ns + 'cEANTrib').text = item.produto.codigo_barras or ''
        etree.SubElement(prod, ns + 'uTrib').text = item.produto.unidade or 'UN'
        etree.SubElement(prod, ns + 'qTrib').text = f'{float(item.quantidade):.4f}'
        etree.SubElement(prod, ns + 'vUnTrib').text = f'{float(item.valor_unitario):.4f}'
        etree.SubElement(prod, ns + 'indTot').text = '1'

        imposto = etree.SubElement(det, ns + 'imposto')
        etree.SubElement(imposto, ns + 'vTotTrib').text = '0.00'

        icms = etree.SubElement(imposto, ns + 'ICMS')
        icms00 = etree.SubElement(icms, ns + 'ICMS00')
        etree.SubElement(icms00, ns + 'orig').text = '0'
        etree.SubElement(icms00, ns + 'CST').text = item.cst_icms or '00'
        etree.SubElement(icms00, ns + 'modBC').text = '3'
        etree.SubElement(icms00, ns + 'vBC').text = f'{float(item.valor_total):.2f}'
        etree.SubElement(icms00, ns + 'pICMS').text = f'{float(item.aliquota_icms):.2f}'
        v_icms = float(item.valor_total) * float(item.aliquota_icms) / 100
        etree.SubElement(icms00, ns + 'vICMS').text = f'{v_icms:.2f}'

        pis = etree.SubElement(imposto, ns + 'PIS')
        pis_outr = etree.SubElement(pis, ns + 'PISOutr')
        etree.SubElement(pis_outr, ns + 'CST').text = '99'
        etree.SubElement(pis_outr, ns + 'vBC').text = '0.00'
        etree.SubElement(pis_outr, ns + 'pPIS').text = '0.00'
        etree.SubElement(pis_outr, ns + 'vPIS').text = '0.00'

        cofins = etree.SubElement(imposto, ns + 'COFINS')
        cofins_outr = etree.SubElement(cofins, ns + 'COFINSOutr')
        etree.SubElement(cofins_outr, ns + 'CST').text = '99'
        etree.SubElement(cofins_outr, ns + 'vBC').text = '0.00'
        etree.SubElement(cofins_outr, ns + 'pCOFINS').text = '0.00'
        etree.SubElement(cofins_outr, ns + 'vCOFINS').text = '0.00'

        det_idx += 1

    total = etree.SubElement(infNFe, ns + 'total')
    icmsTot = etree.SubElement(total, ns + 'ICMSTot')
    etree.SubElement(icmsTot, ns + 'vBC').text = f'{float(doc.base_calculo):.2f}'
    etree.SubElement(icmsTot, ns + 'vICMS').text = f'{float(doc.valor_icms):.2f}'
    etree.SubElement(icmsTot, ns + 'vICMSDeson').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vFCP').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vBCST').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vST').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vFCPST').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vFCPSTRet').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vProd').text = f'{float(doc.valor_produtos):.2f}'
    etree.SubElement(icmsTot, ns + 'vFrete').text = f'{float(doc.valor_frete):.2f}'
    etree.SubElement(icmsTot, ns + 'vSeg').text = f'{float(doc.valor_seguro):.2f}'
    etree.SubElement(icmsTot, ns + 'vDesc').text = f'{float(doc.valor_desconto):.2f}'
    etree.SubElement(icmsTot, ns + 'vII').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vIPI').text = f'{float(doc.valor_ipi):.2f}'
    etree.SubElement(icmsTot, ns + 'vIPIDevol').text = '0.00'
    etree.SubElement(icmsTot, ns + 'vPIS').text = f'{float(doc.valor_pis):.2f}'
    etree.SubElement(icmsTot, ns + 'vCOFINS').text = f'{float(doc.valor_cofins):.2f}'
    etree.SubElement(icmsTot, ns + 'vOutro').text = f'{float(doc.valor_outras):.2f}'
    etree.SubElement(icmsTot, ns + 'vNF').text = f'{float(doc.valor_total):.2f}'
    etree.SubElement(icmsTot, ns + 'vTotTrib').text = f'{float(doc.valor_total_tributos):.2f}'

    transp = etree.SubElement(infNFe, ns + 'transp')
    etree.SubElement(transp, ns + 'modFrete').text = '0'

    pag = etree.SubElement(infNFe, ns + 'pag')
    detPag = etree.SubElement(pag, ns + 'detPag')
    etree.SubElement(detPag, ns + 'indPag').text = '0'
    etree.SubElement(detPag, ns + 'tPag').text = '01'
    etree.SubElement(detPag, ns + 'vPag').text = f'{float(doc.valor_total):.2f}'

    infAdic = etree.SubElement(infNFe, ns + 'infAdic')
    etree.SubElement(infAdic, ns + 'infCpl').text = 'NF-e gerada pelo ERP Supermercado'

    xml_str = etree.tostring(raiz, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    return xml_str
