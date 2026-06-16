from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import DocumentoFiscal, ItemDocumentoFiscal, ConfigFiscal, Venda, Produto, Empresa, Cliente
from app.nfe.xml_generator import xml_nfe
from app.nfe.signer import assinar_xml
from app.nfe.transmitter import transmitir_nfe
from app.nfe.utils import gerar_chave
from datetime import datetime, date

bp = Blueprint('nfe', __name__, url_prefix='/fiscal/nfe')


@bp.route('/')
@login_required
def dashboard():
    docs = DocumentoFiscal.query.filter_by(modelo='NF-e').order_by(DocumentoFiscal.id.desc()).limit(50).all()
    config = ConfigFiscal.query.first()
    proximo = config.proximo_numero_nfe if config else 1
    serie = config.serie_nfe if config else 1
    return render_template('nfe_dashboard.html', docs=docs, proximo=proximo, serie=serie)


@bp.route('/emitir', methods=['GET', 'POST'])
@login_required
def emitir():
    config = ConfigFiscal.query.first()
    if not config:
        flash('Configure o certificado digital em Config Fiscal primeiro!', 'danger')
        return redirect(url_for('fiscal.config'))

    if request.method == 'POST':
        venda_id = request.form.get('venda_id')
        cliente_id = request.form.get('cliente_id')
        cfop = request.form.get('cfop', '5102')
        natureza = request.form.get('natureza_operacao', 'Venda')

        if cliente_id:
            cliente = Cliente.query.get(int(cliente_id))
            if not cliente or not cliente.cpf_cnpj:
                flash('Cliente precisa ter CPF/CNPJ para NF-e!', 'danger')
                return redirect(url_for('nfe.emitir'))
        else:
            cliente = None

        empresa = Empresa.query.first()
        if not empresa or not empresa.cnpj:
            flash('Configure a Empresa com CNPJ primeiro!', 'danger')
            return redirect(url_for('cadastros.empresa'))

        numero = config.proximo_numero_nfe
        serie = config.serie_nfe
        chave = gerar_chave(empresa.cnpj, '55', serie, numero, empresa.uf or 'SP', config.ambiente)

        venda = Venda.query.get(int(venda_id)) if venda_id else None

        total = float(venda.total) if venda else 0
        doc = DocumentoFiscal(
            modelo='NF-e',
            serie=serie,
            numero=numero,
            chave_acesso=chave,
            status='01',
            data_emissao=datetime.now(),
            cliente_id=cliente.id if cliente else None,
            venda_id=venda.id if venda else None,
            cfop=cfop,
            natureza_operacao=natureza,
            base_calculo=total,
            valor_produtos=total,
            valor_total=total,
        )
        db.session.add(doc)
        db.session.flush()

        if venda and venda.itens:
            for item in venda.itens:
                if not item.produto:
                    continue
                val_unit = float(item.valor_unitario or item.preco_unitario or 0)
                qtd = float(item.quantidade or 1)
                val_total = val_unit * qtd
                ncm = item.produto.ncm or '00'
                item_doc = ItemDocumentoFiscal(
                    documento_id=doc.id,
                    produto_id=item.produto_id,
                    quantidade=qtd,
                    valor_unitario=val_unit,
                    valor_total=val_total,
                    ncm=ncm,
                    cfop=cfop,
                )
                db.session.add(item_doc)
        else:
            flash('Selecione uma venda com itens para emitir NF-e!', 'danger')
            db.session.rollback()
            return redirect(url_for('nfe.emitir'))

        db.session.flush()

        try:
            from app.nfe.utils import SEFAZ_URLS
            xml_bytes = xml_nfe(doc, config, empresa)
            doc.status = '02'
            cert_path = config.certificado_digital
            cert_pass = config.certificado_senha
            if cert_path and cert_pass:
                xml_assinado = assinar_xml(xml_bytes, cert_path, cert_pass)
                doc.xml_assinado = xml_assinado.decode('utf-8')
                doc.status = '03'
                db.session.commit()

                if config.ambiente == '1':
                    resultado = transmitir_nfe(xml_assinado, config, empresa)
                    if resultado.get('sucesso'):
                        doc.status = '04'
                        doc.protocolo = resultado.get('protocolo')
                        doc.data_autorizacao = datetime.now()
                        flash(f'NF-e {numero} autorizada! Protocolo: {resultado.get("protocolo")}', 'success')
                    else:
                        doc.status = '99'
                        flash(f'NF-e rejeitada: {resultado.get("erro", resultado.get("motivo", "Erro desconhecido"))}', 'danger')
                else:
                    doc.status = '04'
                    doc.protocolo = '999999999999999'
                    doc.data_autorizacao = datetime.now()
                    flash(f'NF-e {numero} emitida em homologacao (simulada)!', 'info')
            else:
                doc.status = '02'
                flash('Certificado nao configurado. XML gerado mas nao assinado.', 'warning')

            config.proximo_numero_nfe = numero + 1
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao emitir NF-e: {str(e)}', 'danger')
            return redirect(url_for('nfe.dashboard'))

        return redirect(url_for('nfe.view', id=doc.id))

    vendas = Venda.query.filter_by(status='F').order_by(Venda.id.desc()).limit(100).all()
    clientes = Cliente.query.filter(Cliente.cpf_cnpj.isnot(None), Cliente.cpf_cnpj != '').order_by(Cliente.nome).all()
    return render_template('nfe_emitir.html', vendas=vendas, clientes=clientes)


@bp.route('/<int:id>')
@login_required
def view(id):
    doc = DocumentoFiscal.query.get_or_404(id)
    return render_template('nfe_view.html', doc=doc)


@bp.route('/listar')
@login_required
def listar():
    docs = DocumentoFiscal.query.filter_by(modelo='NF-e').order_by(DocumentoFiscal.id.desc()).all()
    return render_template('nfe_lista.html', docs=docs)


@bp.route('/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar(id):
    doc = DocumentoFiscal.query.get_or_404(id)
    if doc.status not in ('04',):
        flash('Apenas NF-e autorizada pode ser cancelada!', 'danger')
        return redirect(url_for('nfe.view', id=id))

    justificativa = request.form.get('justificativa', '')
    if len(justificativa) < 15:
        flash('Justificativa deve ter no minimo 15 caracteres!', 'danger')
        return redirect(url_for('nfe.view', id=id))

    doc.status = '05'
    doc.justificativa = justificativa
    db.session.commit()
    flash(f'NF-e {doc.numero} cancelada!', 'success')
    return redirect(url_for('nfe.view', id=doc.id))


@bp.route('/dados/json')
@login_required
def dados_json():
    docs = DocumentoFiscal.query.filter_by(modelo='NF-e').order_by(DocumentoFiscal.id.desc()).all()
    autorizadas = sum(1 for d in docs if d.status == '04')
    pendentes = sum(1 for d in docs if d.status in ('01', '02', '03'))
    rejeitadas = sum(1 for d in docs if d.status == '99')
    return jsonify(total=len(docs), autorizadas=autorizadas, pendentes=pendentes, rejeitadas=rejeitadas)
