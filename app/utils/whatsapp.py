import requests
from app import db
from app.models.models import ConfigGeral, Cliente
from datetime import date
from decimal import Decimal


def send_whatsapp(telefone, mensagem):
    api_key = ConfigGeral.query.filter_by(modulo='whatsapp', chave='api_key').first()
    api_url = ConfigGeral.query.filter_by(modulo='whatsapp', chave='api_url').first()
    instance = ConfigGeral.query.filter_by(modulo='whatsapp', chave='instance').first()

    if not api_key or not api_url or not instance:
        return (False, 'WhatsApp não configurado')

    url = api_url.valor
    payload = {
        'api_key': api_key.valor,
        'instance': instance.valor,
        'telefone': telefone,
        'mensagem': mensagem,
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return (True, 'Enviado')
    except requests.RequestException as e:
        return (False, str(e))


def enviar_cobranca(cliente_id, mensagem_personalizada=None):
    cliente = Cliente.query.get(cliente_id)
    if not cliente or not cliente.celular:
        return (False, 'Cliente sem celular cadastrado')

    from app.models.models import ContaReceber
    contas = ContaReceber.query.filter_by(cliente_id=cliente.id, recebido=False).order_by(ContaReceber.data_vencimento).all()
    total = sum(float(c.valor) for c in contas)
    vencimento = contas[0].data_vencimento if contas else date.today()

    if mensagem_personalizada:
        mensagem = mensagem_personalizada
    else:
        mensagem = (
            f'Olá {cliente.nome}, tudo bem?\n'
            f'Você possui {len(contas)} conta(s) em aberto no valor total de R$ {total:.2f} '
            f'com vencimento em {vencimento.strftime("%d/%m/%Y")}.\n'
            f'entre em contato para regularizar.'
        )

    return send_whatsapp(cliente.celular, mensagem)


def enviar_promocao(produto_nome, preco, cliente_telefone):
    mensagem = (
        f'Promoção imperdível!\n'
        f'{produto_nome} por apenas R$ {float(preco):.2f}\n'
        f'Corra e aproveite!'
    )
    return send_whatsapp(cliente_telefone, mensagem)
