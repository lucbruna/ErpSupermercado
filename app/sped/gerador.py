"""
Gerador de arquivos SPED Fiscal (EFD-ICMS/IPI).
Layout segundo o Guia Prático EFD-ICMS/IPI versão 3.0.1
"""
from datetime import date, datetime
from decimal import Decimal
from app import db
from app.models.models import Empresa, DocumentoFiscal, ItemDocumentoFiscal, Produto, Venda, MovimentacaoEstoque


def format_cnpj(cnpj):
    return cnpj.replace('.', '').replace('/', '').replace('-', '') if cnpj else ''


def format_cpf(cpf):
    return cpf.replace('.', '').replace('-', '') if cpf else ''


def format_ie(ie):
    return ie.replace('.', '').replace('/', '').replace('-', '') if ie else ''


def gerar_sped_efd(competencia: str, empresa_id: int = None) -> str:
    """
    Gera arquivo SPED EFD-ICMS/IPI para uma competência (MM/AAAA).
    Retorna o conteúdo do arquivo como string.
    """
    mes, ano = competencia.split('/')
    data_ini = date(int(ano), int(mes), 1)
    if int(mes) == 12:
        data_fim = date(int(ano) + 1, 1, 1)
    else:
        data_fim = date(int(ano), int(mes) + 1, 1)
    from datetime import timedelta
    data_fim = data_fim - timedelta(days=1)

    empresas = Empresa.query.all() if not empresa_id else Empresa.query.filter_by(id=empresa_id).all()
    if not empresas:
        return ''

    linhas = []

    for empresa in empresas:
        cnpj = format_cnpj(empresa.cnpj)
        ie = format_ie(empresa.ie or '')
        nome = empresa.razao_social or empresa.nome_fantasia or ''
        end = f'{empresa.endereco or ""},{empresa.numero or ""}'
        bairro = empresa.bairro or ''
        cep = (empresa.cep or '').replace('-', '')
        cidade = empresa.cidade or ''
        uf = empresa.uf or 'SP'
        telefone = (empresa.telefone or '').replace('(', '').replace(')', '').replace('-', '').replace(' ', '')

        # Bloco 0 - Abertura
        now = datetime.now()
        linhas.append(f'|0000|001|{now.strftime("%d%m%Y")}|{now.strftime("%H%M%S")}|||{competencia}|EMPRESA|{cnpj}|{ie}|{nome}|{end}|{bairro}|{cep}|{cidade}|{uf}|{telefone}|0|')

        # Bloco C - Documentos Fiscais
        docs = DocumentoFiscal.query.filter(
            DocumentoFiscal.data_emissao.between(data_ini, data_fim),
            DocumentoFiscal.modelo == 'NFC-e',
            DocumentoFiscal.status == '04',
        ).order_by(DocumentoFiscal.numero).all()

        for doc in docs:
            # C100 - Nota Fiscal
            dt_emissao = doc.data_emissao.strftime('%d%m%Y') if doc.data_emissao else ''
            dt_autorizacao = doc.data_autorizacao.strftime('%d%m%Y') if doc.data_autorizacao else ''
            chave = doc.chave_acesso or ''
            cnpj_cli = format_cnpj(doc.cliente.cpf_cnpj) if doc.cliente and doc.cliente.cpf_cnpj and len(doc.cliente.cpf_cnpj) > 11 else ''
            cpf_cli = format_cpf(doc.cliente.cpf_cnpj) if doc.cliente and doc.cliente.cpf_cnpj and len(doc.cliente.cpf_cnpj) <= 11 else ''

            linhas.append(
                f'|C100|0|{doc.modelo}|{doc.serie}|{doc.numero}|{dt_emissao}|{dt_autorizacao}|{chave}|'
                f'|{cnpj_cli}|{cpf_cli}||||5102|{float(doc.valor_total):.2f}|'
                f'|{float(doc.valor_desconto):.2f}|{float(doc.base_calculo):.2f}|'
                f'|{float(doc.valor_icms):.2f}|{float(doc.valor_total_tributos):.2f}|'
            )

            # C190 - Resumo de ICMS por CST
            for item in doc.itens:
                linhas.append(
                    f'|C190|0|{item.cst_icms or "00"}|{item.cfop or "5102"}|'
                    f'{float(item.aliquota_icms):.2f}|{float(item.valor_total):.2f}|'
                    f'|{float(item.valor_total):.2f}|{float(item.valor_total * item.aliquota_icms / 100):.2f}|'
                )

        # Bloco E - Movimentação de Estoque
        movs = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.created_at.between(
                datetime.combine(data_ini, datetime.min.time()),
                datetime.combine(data_fim, datetime.max.time())
            )
        ).order_by(MovimentacaoEstoque.created_at).all()

        for mov in movs:
            produto = Produto.query.get(mov.produto_id)
            if not produto:
                continue
            ncm = (produto.ncm or '00').replace('.', '')[:8]
            linhas.append(
                f'|E200|0|{mov.created_at.strftime("%d%m%Y")}|'
                f'{mov.tipo}|{ncm}|{mov.produto_id}|{float(mov.quantidade):.3f}|'
                f'{float(mov.preco_unitario):.2f}|{float(mov.quantidade * mov.preco_unitario):.2f}|'
            )

        # Bloco 9 - Controle
        linhas.append(f'|9990|{len(linhas)}|')
        # Bloco K - não implementado para simplificação

    # Encerramento
    linhas.append('|9999|{0}|'.format(len(linhas)))

    return '\r\n'.join(linhas)
