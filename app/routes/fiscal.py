from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import DocumentoFiscal, ItemDocumentoFiscal, ConfigFiscal, Cliente, Produto, Venda, Empresa, Convenio, ContratoConvenio
from datetime import datetime, date
from decimal import Decimal
from app.nfe.utils import gerar_chave
from app.audit import log_auditoria

bp = Blueprint('fiscal', __name__)

STATUS_DOC = {
    '01': 'Digitando', '02': 'Assinando', '03': 'Transmitindo',
    '04': 'Autorizada', '05': 'Cancelada', '99': 'Rejeitada',
}

TRIBUTACAO = {
    '1': 'Simples Nacional', '2': 'Lucro Presumido', '3': 'Lucro Real',
}

SAT_AMBIENTES = {'1': 'Produção', '2': 'Homologação'}


@bp.context_processor
def inject_fiscal():
    return dict(fiscal_status=STATUS_DOC, trib_names=TRIBUTACAO)


def get_config():
    cfg = ConfigFiscal.query.first()
    if not cfg:
        cfg = ConfigFiscal(regime_tributario='3', aliquota_padrao=18.00,
                           serie_nfe=1, serie_nfce=1,
                           proximo_numero_nfe=1, proximo_numero_nfce=1,
                           ambiente='2')
        db.session.add(cfg)
        db.session.commit()
    return cfg


# ── Dashboard ──────────────────────────────────────────────────

@bp.route('/fiscal')
@login_required
def dashboard():
    docs = DocumentoFiscal.query.order_by(DocumentoFiscal.id.desc()).limit(50).all()
    config = get_config()
    empresa = Empresa.query.first()
    return render_template('fis_dashboard.html', docs=docs, config=config, empresa=empresa)


# ── Configuração ────────────────────────────────────────────────

@bp.route('/fiscal/config', methods=['GET', 'POST'])
@login_required
def config():
    cfg = get_config()
    empresa = Empresa.query.first()
    if request.method == 'POST':
        from app.audit import model_to_dict
        campos = ['regime_tributario', 'aliquota_padrao', 'serie_nfe', 'serie_nfce', 'ambiente']
        ant = model_to_dict(cfg, campos)
        cfg.regime_tributario = request.form.get('regime_tributario', '3')
        cfg.aliquota_padrao = Decimal(request.form.get('aliquota_padrao', '18.00'))
        cfg.serie_nfe = int(request.form.get('serie_nfe', 1))
        cfg.serie_nfce = int(request.form.get('serie_nfce', 1))
        cfg.ambiente = request.form.get('ambiente', '2')
        cfg.certificado_digital = request.form.get('certificado_digital') or None
        cfg.certificado_senha = request.form.get('certificado_senha') or None
        db.session.commit()
        novos = model_to_dict(cfg, campos)
        log_auditoria('Atualizou configuração fiscal', 'ConfigFiscal', cfg.id, valores_anteriores=ant, valores_novos=novos)
        flash('Configuração fiscal salva com sucesso!', 'success')
        return redirect(url_for('fiscal.dashboard'))
    return render_template('fis_config.html', cfg=cfg, empresa=empresa)


# ── Emissão NFC-e ──────────────────────────────────────────────

@bp.route('/fiscal/emitir/nfce', methods=['GET', 'POST'])
@login_required
def emitir_nfce():
    config = get_config()
    empresa = Empresa.query.first()
    if not empresa:
        flash('Cadastre a empresa em Cadastros > Empresa primeiro!', 'danger')
        return redirect(url_for('fiscal.config'))

    if not config.certificado_digital:
        flash('Configure o certificado digital A1 em Configuração Fiscal!', 'danger')
        return redirect(url_for('fiscal.config'))

    if request.method == 'POST':
        venda_id = request.form.get('venda_id')
        if not venda_id:
            flash('Selecione uma venda!', 'danger')
            return redirect(url_for('fiscal.emitir_nfce'))

        venda = Venda.query.get(venda_id)
        if not venda:
            flash('Venda não encontrada!', 'danger')
            return redirect(url_for('fiscal.emitir_nfce'))

        cliente_id = request.form.get('cliente_id') or None

        doc = DocumentoFiscal(
            modelo='NFC-e',
            serie=config.serie_nfce,
            numero=config.proximo_numero_nfce,
            cliente_id=cliente_id,
            venda_id=venda.id,
            cfop='5102',
            natureza_operacao='Venda de Mercadoria',
            valor_produtos=venda.subtotal,
            valor_desconto=venda.desconto,
            valor_total=venda.total,
            base_calculo=venda.total,
            status='01',
        )
        doc.chave_acesso = gerar_chave(
            empresa.cnpj, '65', config.serie_nfce, config.proximo_numero_nfce,
            empresa.uf or 'SP', config.ambiente
        )

        db.session.add(doc)
        db.session.flush()

        for item in venda.itens:
            sub = item.subtotal or (item.preco_unitario * item.quantidade)
            i_doc = ItemDocumentoFiscal(
                documento_id=doc.id,
                produto_id=item.produto_id,
                quantidade=item.quantidade,
                valor_unitario=item.preco_unitario,
                valor_total=sub,
                ncm=item.produto.ncm or '00',
                cest=item.produto.cest or '',
                cfop='5102',
                aliquota_icms=config.aliquota_padrao,
                cst_icms='00',
            )
            db.session.add(i_doc)

        config.proximo_numero_nfce += 1
        db.session.commit()

        try:
            from app.nfe.xml_generator import xml_nfce
            from app.nfe.signer import assinar_xml
            from app.nfe.transmitter import transmitir_nfce
            flash(f'NFC-e #{doc.numero} gerada! Iniciando assinatura e transmissão...', 'info')

            # 1. Gera XML
            xml_bytes = xml_nfce(doc, config, empresa)
            doc.xml_assinado = xml_bytes.decode('utf-8')
            doc.status = '02'
            db.session.commit()

            # 2. Assina XML
            xml_assinado = assinar_xml(xml_bytes, config.certificado_digital, config.certificado_senha)
            doc.xml_assinado = xml_assinado.decode('utf-8')
            doc.status = '03'
            db.session.commit()

            # 3. Transmite para SEFAZ
            resultado = transmitir_nfce(xml_assinado, config, empresa)

            if resultado.get('sucesso'):
                doc.status = '04'
                doc.protocolo = resultado.get('protocolo')
                doc.data_autorizacao = datetime.now()
                log_auditoria(f'NFC-e #{doc.numero} autorizada', 'DocumentoFiscal', doc.id)
                flash(f'NFC-e #{doc.numero} autorizada! Protocolo: {doc.protocolo}', 'success')
            else:
                doc.status = '99'
                doc.motivo_cancelamento = resultado.get('erro') or resultado.get('motivo') or 'Rejeitada pela SEFAZ'
                log_auditoria(f'NFC-e #{doc.numero} rejeitada: {doc.motivo_cancelamento}', 'DocumentoFiscal', doc.id)
                flash(f'NFC-e #{doc.numero} rejeitada: {doc.motivo_cancelamento}', 'danger')

            db.session.commit()

        except Exception as e:
            doc.status = '99'
            doc.motivo_cancelamento = str(e)
            db.session.commit()
            log_auditoria(f'Erro NFC-e #{doc.numero}: {str(e)}', 'DocumentoFiscal', doc.id)
            flash(f'Erro na transmissão: {str(e)}', 'danger')

        return redirect(url_for('fiscal.visualizar', id=doc.id))

    vendas = Venda.query.filter_by(status='F').order_by(Venda.created_at.desc()).all()
    return render_template('fis_emitir_nfce.html', vendas=vendas, config=config)


# ── Visualizar ──────────────────────────────────────────────────

@bp.route('/fiscal/visualizar/<int:id>')
@login_required
def visualizar(id):
    doc = DocumentoFiscal.query.get_or_404(id)
    return render_template('fis_view.html', doc=doc, status_map=STATUS_DOC)


# ── Transmissão Manual ──────────────────────────────────────────

@bp.route('/fiscal/transmitir/<int:id>')
@login_required
def transmitir(id):
    doc = DocumentoFiscal.query.get_or_404(id)
    config = get_config()
    empresa = Empresa.query.first()

    if doc.status == '04':
        flash('Documento já autorizado!', 'warning')
        return redirect(url_for('fiscal.visualizar', id=id))

    if doc.status == '05':
        flash('Documento cancelado!', 'warning')
        return redirect(url_for('fiscal.visualizar', id=id))

    try:
        from app.nfe.xml_generator import xml_nfce
        from app.nfe.signer import assinar_xml
        from app.nfe.transmitter import transmitir_nfce
        if doc.status == '01':
            if not doc.xml_assinado:
                xml_bytes = xml_nfce(doc, config, empresa)
                doc.xml_assinado = xml_bytes.decode('utf-8')
                doc.status = '02'
                db.session.commit()

        if doc.status == '02':
            xml_assinado = assinar_xml(
                doc.xml_assinado.encode('utf-8'),
                config.certificado_digital,
                config.certificado_senha,
            )
            doc.xml_assinado = xml_assinado.decode('utf-8')
            doc.status = '03'
            db.session.commit()

        if doc.status in ('03', '99'):
            xml_bytes = doc.xml_assinado.encode('utf-8')
            resultado = transmitir_nfce(xml_bytes, config, empresa)

            if resultado.get('sucesso'):
                doc.status = '04'
                doc.protocolo = resultado.get('protocolo')
                doc.data_autorizacao = datetime.now()
                flash(f'Documento autorizado! Protocolo: {doc.protocolo}', 'success')
            else:
                doc.status = '99'
                doc.motivo_cancelamento = resultado.get('erro') or resultado.get('motivo') or 'Rejeitada'
                flash(f'Documento rejeitado: {doc.motivo_cancelamento}', 'danger')

        db.session.commit()

    except Exception as e:
        doc.status = '99'
        doc.motivo_cancelamento = str(e)
        db.session.commit()
        flash(f'Erro: {str(e)}', 'danger')

    return redirect(url_for('fiscal.visualizar', id=id))


# ── Cancelamento ────────────────────────────────────────────────

@bp.route('/fiscal/cancelar/<int:id>', methods=['POST'])
@login_required
def cancelar(id):
    doc = DocumentoFiscal.query.get_or_404(id)
    config = get_config()
    empresa = Empresa.query.first()

    if doc.status == '05':
        flash('Documento já cancelado!', 'warning')
        return redirect(url_for('fiscal.visualizar', id=id))

    if doc.status != '04':
        flash('Apenas documentos autorizados podem ser cancelados!', 'danger')
        return redirect(url_for('fiscal.visualizar', id=id))

    justificativa = request.form.get('justificativa', '').strip()
    if len(justificativa) < 15:
        flash('Justificativa deve ter no mínimo 15 caracteres!', 'danger')
        return redirect(url_for('fiscal.visualizar', id=id))

    try:
        from app.nfe.xml_generator import xml_cancelamento
        from app.nfe.signer import assinar_evento
        from app.nfe.transmitter import transmitir_cancelamento
        # Gera XML de cancelamento
        xml_evento = xml_cancelamento(doc, config, empresa, justificativa)

        # Assina evento
        xml_assinado = assinar_evento(xml_evento, config.certificado_digital, config.certificado_senha)

        # Transmite cancelamento
        resultado = transmitir_cancelamento(xml_assinado, config, empresa, doc.chave_acesso)

        if resultado.get('sucesso'):
            doc.status = '05'
            doc.motivo_cancelamento = justificativa
            doc.protocolo = resultado.get('protocolo')

            if doc.venda:
                for item in doc.venda.itens:
                    item.produto.estoque_atual += item.quantidade

            log_auditoria(f'Cancelou NFC-e #{doc.numero}: {justificativa}', 'DocumentoFiscal', doc.id)
            flash(f'Documento cancelado! Protocolo: {doc.protocolo}', 'success')
        else:
            log_auditoria(f'Falha cancelamento NFC-e #{doc.numero}', 'DocumentoFiscal', doc.id)
            flash(f'Erro no cancelamento: {resultado.get("erro") or resultado.get("motivo", "Desconhecido")}', 'danger')

        db.session.commit()

    except Exception as e:
        log_auditoria(f'Erro cancelamento NFC-e #{doc.numero}: {str(e)}', 'DocumentoFiscal', doc.id)
        flash(f'Erro ao cancelar: {str(e)}', 'danger')

    return redirect(url_for('fiscal.visualizar', id=id))


# ── Convenios ──────────────────────────────────────────────────

@bp.route('/fiscal/convenios')
@login_required
def lista_convenios():
    convenios = Convenio.query.order_by(Convenio.nome).all()
    return render_template('fis_convenios_lista.html', convenios=convenios)


@bp.route('/fiscal/convenios/novo', methods=['GET', 'POST'])
@login_required
def novo_convenio():
    if request.method == 'POST':
        c = Convenio(
            nome=request.form['nome'],
            cnpj=request.form.get('cnpj'),
            contato=request.form.get('contato'),
            telefone=request.form.get('telefone'),
            email=request.form.get('email'),
            limite_credito=Decimal(request.form.get('limite_credito', '0')),
            prazo_recebimento=int(request.form.get('prazo_recebimento', 30)),
            taxa_administracao=Decimal(request.form.get('taxa_administracao', '0')),
        )
        db.session.add(c)
        db.session.commit()
        log_auditoria(f'Criou convênio: {c.nome}', 'Convenio', c.id)
        flash(f'Convênio {c.nome} criado!', 'success')
        return redirect(url_for('fiscal.lista_convenios'))
    return render_template('fis_convenios_form.html', conv=None)


@bp.route('/fiscal/convenios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_convenio(id):
    c = Convenio.query.get_or_404(id)
    if request.method == 'POST':
        c.nome = request.form['nome']
        c.cnpj = request.form.get('cnpj')
        c.contato = request.form.get('contato')
        c.telefone = request.form.get('telefone')
        c.email = request.form.get('email')
        c.limite_credito = Decimal(request.form.get('limite_credito', '0'))
        c.prazo_recebimento = int(request.form.get('prazo_recebimento', 30))
        c.taxa_administracao = Decimal(request.form.get('taxa_administracao', '0'))
        c.ativo = 'ativo' in request.form
        db.session.commit()
        log_auditoria(f'Editou convênio: {c.nome}', 'Convenio', c.id)
        flash('Convênio atualizado!', 'success')
        return redirect(url_for('fiscal.lista_convenios'))
    return render_template('fis_convenios_form.html', conv=c)


@bp.route('/fiscal/convenios/excluir/<int:id>')
@login_required
def excluir_convenio(id):
    c = Convenio.query.get_or_404(id)
    nome = c.nome
    db.session.delete(c)
    db.session.commit()
    log_auditoria(f'Excluiu convênio: {nome}', 'Convenio', id)
    flash('Convênio excluído!', 'danger')
    return redirect(url_for('fiscal.lista_convenios'))


# ── SAT ─────────────────────────────────────────────────────────

@bp.route('/fiscal/sat/config', methods=['GET', 'POST'])
@login_required
def sat_config():
    from app.models.models import ConfigFiscal
    cfg = get_config()
    empresa = Empresa.query.first()
    if request.method == 'POST':
        cfg.ambiente = request.form.get('ambiente', '2')
        cfg.serie_nfce = int(request.form.get('serie_nfce', 1))
        cfg.certificado_digital = request.form.get('certificado_digital') or cfg.certificado_digital
        cfg.certificado_senha = request.form.get('certificado_senha') or cfg.certificado_senha
        cfg.caminho_dll_sat = request.form.get('caminho_dll_sat') or getattr(cfg, 'caminho_dll_sat', '')
        cfg.codigo_ativacao_sat = request.form.get('codigo_ativacao_sat') or getattr(cfg, 'codigo_ativacao_sat', '')
        cfg.cnpj_software_house = request.form.get('cnpj_software_house') or getattr(cfg, 'cnpj_software_house', '')
        db.session.commit()
        log_auditoria('Configurou SAT', 'ConfigFiscal', cfg.id)
        flash('Configuração SAT salva!', 'success')
        return redirect(url_for('fiscal.sat_config'))
    return render_template('fis_sat_config.html', cfg=cfg, empresa=empresa)


@bp.route('/fiscal/sat/emitir/<int:venda_id>')
@login_required
def sat_emitir(venda_id):
    venda = Venda.query.get_or_404(venda_id)
    if venda.status != 'F':
        flash('Apenas vendas finalizadas!', 'danger')
        return redirect(url_for('fiscal.dashboard'))
    config = get_config()
    empresa = Empresa.query.first()
    if not empresa:
        flash('Cadastre a empresa primeiro!', 'danger')
        return redirect(url_for('fiscal.config'))

    try:
        from app.sat.emissor import SATEmissor, gerar_xml_cfe
        sat = SATEmissor({
            'caminho_dll': getattr(config, 'caminho_dll_sat', 'C:\\SAT\\sat.dll'),
            'codigo_ativacao': getattr(config, 'codigo_ativacao_sat', '12345678'),
            'cnpj_software_house': getattr(config, 'cnpj_software_house', ''),
            'ambiente': config.ambiente or '2',
            'numero_caixa': '001',
        })
        itens = venda.itens
        xml_cfe = gerar_xml_cfe(venda, empresa, config, itens)
        resultado = sat.enviar_dados_venda(xml_cfe)

        if resultado.get('sucesso'):
            doc = DocumentoFiscal(
                modelo='SAT',
                serie=config.serie_nfce or 1,
                numero=config.proximo_numero_nfce or 1,
                chave_acesso=resultado.get('chave_acesso', ''),
                status='04',
                data_autorizacao=datetime.now(),
                protocolo=resultado.get('numero_sessao', ''),
                venda_id=venda.id,
                cliente_id=venda.cliente_id,
                cfop='5102',
                natureza_operacao='Venda SAT',
                valor_produtos=venda.subtotal,
                valor_desconto=venda.desconto,
                valor_total=venda.total,
                xml_assinado=xml_cfe,
            )
            db.session.add(doc)
            if hasattr(config, 'proximo_numero_nfce') and config.proximo_numero_nfce:
                config.proximo_numero_nfce += 1
            db.session.commit()
            log_auditoria(f'SAT CF-e emitido #{doc.numero}', 'DocumentoFiscal', doc.id)
            flash(f'SAT CF-e emitido! Sessão: {resultado.get("numero_sessao", "")}', 'success')
        else:
            flash(f'Erro SAT: {resultado.get("erro", resultado.get("mensagem", "Falha"))}', 'danger')

    except Exception as e:
        flash(f'Erro ao emitir SAT: {str(e)}', 'danger')
        log_auditoria(f'Erro SAT venda #{venda.numero}: {str(e)}', 'DocumentoFiscal')

    return redirect(url_for('fiscal.dashboard'))
