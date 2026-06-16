from flask import Blueprint, render_template, request, Response
from flask_login import login_required
from app import db
from app.models.models import DocumentoFiscal, Venda, Empresa
from app.print_utils import gerar_danfe_html, gerar_cupom_html, render_pdf

bp = Blueprint('imprimir', __name__, url_prefix='/imprimir')


@bp.route('/danfe/<int:doc_id>')
@login_required
def danfe(doc_id):
    doc = DocumentoFiscal.query.get_or_404(doc_id)
    empresa = Empresa.query.first()
    html = gerar_danfe_html(doc, empresa)

    fmt = request.args.get('formato', 'html')
    if fmt == 'pdf':
        pdf = render_pdf(html)
        if pdf:
            return Response(pdf, mimetype='application/pdf',
                            headers={'Content-Disposition': f'attachment; filename=danfe_{doc.chave_acesso}.pdf'})

    return Response(html, mimetype='text/html')


@bp.route('/cupom/<int:venda_id>')
@login_required
def cupom(venda_id):
    venda = Venda.query.get_or_404(venda_id)
    empresa = Empresa.query.first()
    if not empresa:
        empresa = type('obj', (object,), {'nome_fantasia': 'ERP Supermercado', 'cnpj': '', 'endereco': '', 'numero': '', 'cidade': '', 'uf': ''})()

    html = gerar_cupom_html(venda, empresa)

    fmt = request.args.get('formato', 'html')
    if fmt == 'pdf':
        pdf = render_pdf(html)
        if pdf:
            return Response(pdf, mimetype='application/pdf',
                            headers={'Content-Disposition': f'attachment; filename=cupom_{venda.numero}.pdf'})

    return Response(html, mimetype='text/html')
