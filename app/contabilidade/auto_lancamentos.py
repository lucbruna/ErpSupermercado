"""
Lançamentos contábeis automáticos a partir de eventos do sistema.
Suporta: vendas finalizadas, recebimentos, pagamentos.

Requer que o plano de contas padrão já esteja populado.
"""
from datetime import date
from decimal import Decimal
from app import db
from app.models.models import LancamentoContabil, PlanoContas, Venda, ContaPagar, ContaReceber


def _busca_conta(codigo):
    return PlanoContas.query.filter_by(codigo=codigo, ativo=True).first()


def lancar_venda(venda: Venda, usuario_id: int) -> list:
    """
    Gera lançamentos contábeis para uma venda finalizada.
    Débito: Caixa (1.01.01) / Crédito: Vendas (3.01.01) e ICMS a Recolher (2.01.06)
    """
    lancamentos = []
    caixa = _busca_conta('1.01.01')
    vendas = _busca_conta('3.01.01')
    icms = _busca_conta('2.01.06')

    if not all([caixa, vendas]):
        return []

    # Débito no Caixa pelo valor total
    l1 = LancamentoContabil(
        data=venda.created_at.date() if venda.created_at else date.today(),
        historico=f'Venda NF {venda.numero}',
        valor=venda.total,
        debito_id=caixa.id,
        credito_id=vendas.id,
        documento=str(venda.numero),
        lote=f'VENDA{venda.id:06d}',
        usuario_id=usuario_id,
    )
    db.session.add(l1)
    lancamentos.append(l1)

    # Se houver ICMS, debita vendas e credita ICMS a recolher
    if icms and venda.total > 0:
        # Estimativa simples: 7% de ICMS (ajustar conforme legislação)
        valor_icms = venda.total * Decimal('0.07')
        l2 = LancamentoContabil(
            data=venda.created_at.date() if venda.created_at else date.today(),
            historico=f'ICMS Venda NF {venda.numero}',
            valor=valor_icms,
            debito_id=vendas.id,
            credito_id=icms.id,
            documento=str(venda.numero),
            lote=f'VENDA{venda.id:06d}',
            usuario_id=usuario_id,
        )
        db.session.add(l2)
        lancamentos.append(l2)

    db.session.commit()
    return lancamentos


def lancar_recebimento(conta_receber: ContaReceber, usuario_id: int) -> LancamentoContabil:
    """
    Gera lançamento para recebimento de conta.
    Débito: Caixa / Crédito: Clientes
    """
    caixa = _busca_conta('1.01.01')
    clientes = _busca_conta('1.01.04')
    if not all([caixa, clientes]):
        return None

    lanc = LancamentoContabil(
        data=conta_receber.data_recebimento or date.today(),
        historico=f'Recebimento: {conta_receber.descricao[:200]}',
        valor=conta_receber.valor_recebido or conta_receber.valor,
        debito_id=caixa.id,
        credito_id=clientes.id,
        documento=conta_receber.documento,
        lote=f'REC{conta_receber.id:06d}',
        usuario_id=usuario_id,
    )
    db.session.add(lanc)
    db.session.commit()
    return lanc


def lancar_pagamento(conta_pagar: ContaPagar, usuario_id: int) -> LancamentoContabil:
    """
    Gera lançamento para pagamento de conta.
    Débito: Fornecedores / Crédito: Caixa
    """
    caixa = _busca_conta('1.01.01')
    fornecedores = _busca_conta('2.01.01')
    if not all([caixa, fornecedores]):
        return None

    lanc = LancamentoContabil(
        data=conta_pagar.data_pagamento or date.today(),
        historico=f'Pagamento: {conta_pagar.descricao[:200]}',
        valor=conta_pagar.valor_pago or conta_pagar.valor,
        debito_id=fornecedores.id,
        credito_id=caixa.id,
        documento=conta_pagar.documento,
        lote=f'PAG{conta_pagar.id:06d}',
        usuario_id=usuario_id,
    )
    db.session.add(lanc)
    db.session.commit()
    return lanc
