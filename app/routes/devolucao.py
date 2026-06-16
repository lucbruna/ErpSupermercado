from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.models import Devolucao, DevolucaoItem, Venda, ItemVenda, Produto, MovimentacaoEstoque, DocumentoFiscal
from datetime import datetime
from decimal import Decimal
from app.audit import log_auditoria

bp = Blueprint('devolucao', __name__, url_prefix='/devolucao')


@bp.route('/')
@login_required
def lista():
    devolucoes = Devolucao.query.order_by(Devolucao.created_at.desc()).all()
    return render_template('devolucao_lista.html', devolucoes=devolucoes)


@bp.route('/nova/<int:venda_id>', methods=['GET', 'POST'])
@login_required
def nova(venda_id):
    venda = Venda.query.get_or_404(venda_id)
    if venda.status != 'F':
        flash('Apenas vendas finalizadas podem ter devolução!', 'danger')
        return redirect(url_for('pdv.venda_detalhe', venda_id=venda_id))

    if request.method == 'POST':
        motivo = request.form.get('motivo', '').strip()
        if not motivo:
            flash('Informe o motivo da devolução!', 'danger')
            return redirect(url_for('devolucao.nova', venda_id=venda_id))

        produtos_ids = request.form.getlist('produto_id[]')
        quantidades = request.form.getlist('quantidade[]')
        if not produtos_ids:
            flash('Selecione pelo menos um item!', 'danger')
            return redirect(url_for('devolucao.nova', venda_id=venda_id))

        dev = Devolucao(
            venda_id=venda.id, usuario_id=current_user.id,
            motivo=motivo, status='01'
        )
        db.session.add(dev)
        db.session.flush()

        valor_total = Decimal('0')
        for pid, qtd_str in zip(produtos_ids, quantidades):
            qtd = Decimal(qtd_str or '0')
            if qtd <= 0:
                continue
            item_venda = ItemVenda.query.filter_by(
                venda_id=venda.id, produto_id=int(pid)
            ).first()
            if not item_venda:
                continue
            preco = item_venda.preco_unitario
            subtotal = qtd * preco
            di = DevolucaoItem(
                devolucao_id=dev.id, produto_id=int(pid),
                quantidade=qtd, preco_unitario=preco, subtotal=subtotal
            )
            db.session.add(di)
            produto = Produto.query.get(int(pid))
            produto.estoque_atual += qtd
            mov = MovimentacaoEstoque(
                tipo='E', produto_id=int(pid), quantidade=qtd,
                preco_unitario=preco, motivo=f'Devolução Venda #{venda.numero}',
                documento=f'DEV-{venda.numero}', usuario_id=current_user.id
            )
            db.session.add(mov)
            valor_total += subtotal

        dev.valor_total = valor_total

        # Verifica se existe documento fiscal autorizado para estorno
        doc_fiscal = DocumentoFiscal.query.filter_by(
            venda_id=venda.id, status='04'
        ).first()
        if doc_fiscal:
            dev.documento_fiscal_id = doc_fiscal.id
            # Tenta estornar fiscalmente
            try:
                from app.nfe.xml_generator import xml_cancelamento
                from app.nfe.signer import assinar_evento
                from app.nfe.transmitter import transmitir_cancelamento
                from app.models.models import ConfigFiscal, Empresa

                config = ConfigFiscal.query.first()
                empresa = Empresa.query.first()

                if config and empresa and config.certificado_digital:
                    justificativa = f'Devolucao: {motivo[:50]}'
                    xml_evento = xml_cancelamento(doc_fiscal, config, empresa, justificativa)
                    xml_assinado = assinar_evento(xml_evento, config.certificado_digital, config.certificado_senha)
                    resultado = transmitir_cancelamento(xml_assinado, config, empresa, doc_fiscal.chave_acesso)

                    if resultado.get('sucesso'):
                        doc_fiscal.status = '05'
                        doc_fiscal.motivo_cancelamento = justificativa
                        dev.status = '02'
                        flash('Estorno fiscal realizado com sucesso!', 'success')
                    else:
                        flash(f'Estorno fiscal: {resultado.get("erro", "falha")}. Devolução registrada sem estorno.', 'warning')
                else:
                    flash('Certificado digital não configurado. Devolução sem estorno fiscal.', 'warning')
            except Exception as e:
                flash(f'Erro no estorno fiscal: {str(e)}. Devolução registrada.', 'warning')

        db.session.commit()
        log_auditoria(f'Devolução Venda #{venda.numero} - R$ {float(valor_total):.2f}', 'Devolucao', dev.id)
        flash(f'Devolução registrada! Estoque atualizado.', 'success')
        return redirect(url_for('pdv.venda_detalhe', venda_id=venda_id))

    return render_template('devolucao_form.html', venda=venda)
