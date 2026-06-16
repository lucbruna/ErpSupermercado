"""
Utilitário de impressão/PDF.
Tenta usar weasyprint se instalado, senão renderiza HTML para impressão.
TODOS os dados de usuário são sanitizados contra XSS.
"""
import html
import os

try:
    from weasyprint import HTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False


def _h(valor):
    """Sanitiza valor para uso seguro em HTML (XSS prevention)"""
    if valor is None:
        return ''
    return html.escape(str(valor), quote=True)


def render_pdf(html_content):
    if HAS_WEASYPRINT:
        return HTML(string=html_content).write_pdf()
    return None


def gerar_danfe_html(doc, empresa):
    from datetime import datetime
    itens = doc.itens.all() if hasattr(doc.itens, 'all') else doc.itens
    emp_nome = _h(empresa.nome_fantasia or empresa.razao_social)
    emp_cnpj = _h(empresa.cnpj or '')
    emp_ie = _h(empresa.ie or '-')
    emp_end = _h(empresa.endereco or '')
    emp_num = _h(empresa.numero or '')
    emp_bairro = _h(empresa.bairro or '')
    emp_cidade = _h(empresa.cidade or '')
    emp_uf = _h(empresa.uf or '')
    doc_modelo = _h(doc.modelo)
    doc_chave = _h(doc.chave_acesso or '')
    doc_protocolo = _h(doc.protocolo or '-')
    doc_emissao = doc.data_emissao.strftime('%d/%m/%Y %H:%M') if doc.data_emissao else '-'
    doc_nat_op = _h(doc.natureza_operacao or '')
    doc_cfop = _h(doc.cfop or '')
    cliente_nome = _h(doc.cliente.nome) if doc.cliente else 'CONSUMIDOR'
    linhas_itens = ''
    for i in itens:
        cod = _h(i.produto.codigo_barras or str(i.produto_id))
        nome = _h(i.produto.nome)
        un = _h(i.produto.unidade or 'UN')
        linhas_itens += f'<tr><td>{cod}</td><td>{nome}</td><td>{float(i.quantidade):.3f}</td><td>{un}</td><td>R$ {float(i.valor_unitario):.2f}</td><td>R$ {float(i.valor_total):.2f}</td></tr>'
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>DANFE NFC-e {doc.numero}</title>
<style>
    @page {{ margin: 10mm; size: A4; }}
    body {{ font-family: 'Courier New', monospace; font-size: 12px; }}
    .cab {{ text-align: center; border-bottom: 1px solid #000; padding-bottom: 10px; margin-bottom: 10px; }}
    .cab h2 {{ margin: 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
    th, td {{ border: 1px solid #000; padding: 4px 6px; text-align: left; }}
    th {{ background: #eee; }}
    .total {{ text-align: right; font-weight: bold; font-size: 14px; }}
    .info {{ margin: 5px 0; }}
    .qrcode {{ text-align: center; margin-top: 15px; }}
</style></head><body>
<div class="cab">
    <h2>{emp_nome}</h2>
    <small>{emp_cnpj} | IE: {emp_ie}</small><br>
    <small>{emp_end}, {emp_num} - {emp_bairro} - {emp_cidade}/{emp_uf}</small>
</div>
<h3>DANFE NFC-e</h3>
<div class="info">
    <strong>Número:</strong> {doc_modelo} {doc.serie}-{doc.numero} &nbsp;|&nbsp;
    <strong>Chave:</strong> {doc_chave}<br>
    <strong>Emissão:</strong> {doc_emissao} &nbsp;|&nbsp;
    <strong>Protocolo:</strong> {doc_protocolo}
</div>
<div class="info"><strong>Cliente:</strong> {cliente_nome}</div>
<table>
    <tr><th>Código</th><th>Descrição</th><th>Qtd</th><th>UN</th><th>Valor Unit.</th><th>Total</th></tr>
    {linhas_itens}
</table>
<div class="total">Valor Total: R$ {float(doc.valor_total):.2f}</div>
<div class="info">
    <strong>Natureza da Operação:</strong> {doc_nat_op}<br>
    <strong>CFOP:</strong> {doc_cfop}
</div>
<div class="info">
    <strong>Tributos:</strong> ICMS: R$ {float(doc.valor_icms):.2f} | PIS: R$ {float(doc.valor_pis):.2f} | COFINS: R$ {float(doc.valor_cofins):.2f}
</div>
<div class="qrcode">
    <p>Consulte pela chave de acesso em: https://www.sefaz.XX.gov.br/consulta</p>
    <p><strong>{doc_chave}</strong></p>
</div>
</body></html>'''


def gerar_cupom_html(venda, empresa):
    emp_nome = _h(empresa.nome_fantasia or empresa.razao_social)
    emp_cnpj = _h(empresa.cnpj or '')
    emp_end = _h(empresa.endereco or '')
    emp_num = _h(empresa.numero or '')
    emp_cidade = _h(empresa.cidade or '')
    emp_uf = _h(empresa.uf or '')
    operador = _h(venda.usuario.nome) if venda.usuario else '-'
    dt_venda = venda.created_at.strftime('%d/%m/%Y %H:%M') if venda.created_at else '-'
    linhas_itens = ''
    for item in venda.itens:
        nome = _h(item.produto.nome)
        linhas_itens += f'<tr><td>{nome}</td><td style="text-align:right">{float(item.quantidade):.3f} x {float(item.preco_unitario):.2f}</td><td style="text-align:right">R$ {float(item.subtotal):.2f}</td></tr>'
    linhas_pag = ''
    for p in venda.pagamentos:
        fp = _h(p.forma_pagamento)
        linhas_pag += f'<div>{fp}: R$ {float(p.valor):.2f}</div>'
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Cupom Venda #{venda.numero}</title>
<style>
    @page {{ margin: 5mm; size: 80mm 297mm; }}
    body {{ font-family: 'Courier New', monospace; font-size: 11px; width: 70mm; margin: auto; }}
    .center {{ text-align: center; }}
    .linha {{ border-top: 1px dashed #000; margin: 5px 0; }}
    table {{ width: 100%; }}
    td {{ padding: 2px 0; }}
    .total {{ font-size: 16px; font-weight: bold; text-align: center; }}
</style></head><body>
<div class="center">
    <strong>{emp_nome}</strong><br>
    {emp_cnpj}<br>
    {emp_end}, {emp_num} - {emp_cidade}/{emp_uf}<br>
</div>
<div class="linha"></div>
<div class="center"><strong>CUPOM FISCAL</strong></div>
<div>Venda #{venda.numero} | {dt_venda}</div>
<div>Operador: {operador}</div>
<div class="linha"></div>
<table>
    {linhas_itens}
</table>
<div class="linha"></div>
<div class="total">Total: R$ {float(venda.total):.2f}</div>
<div class="linha"></div>
<div><strong>Pagamentos:</strong></div>
{linhas_pag}
<div class="linha"></div>
<div class="center">Obrigado pela preferência!</div>
</body></html>'''
