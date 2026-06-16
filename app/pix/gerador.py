"""
Gerador de QR Code PIX no padrão EMV BR Code (estático).
Compatível com qualquer banco que use o padrão BR Code.
Baseado no Manual de Padrões do PIX (BACEN).
"""
import crcmod
import qrcode
import io
import base64


def _crc16(payload: str) -> str:
    """Calcula CRC16-CCITT do payload"""
    crc16_fn = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, revInit=False, revOut=False)
    crc = crc16_fn(payload.encode('utf-8'))
    return f'{crc:04X}'


def _add_field(tag: str, valor: str) -> str:
    """Adiciona campo TLV (Tag-Length-Value)"""
    tamanho = f'{len(valor):02d}'
    return f'{tag}{tamanho}{valor}'


def gerar_payload_estatico(chave_pix: str, nome: str, cidade: str,
                           valor: float = None, txid: str = '***') -> str:
    """
    Gera payload EMV BR Code para PIX estático.
    Args:
        chave_pix: CPF, CNPJ, email, telefone ou chave aleatória
        nome: Nome do recebedor (até 25 caracteres)
        cidade: Cidade do recebedor (até 15 caracteres)
        valor: Valor opcional da transação
        txid: Identificador da transação (*** = gerado pelo banco)
    Returns:
        String base64 do payload (BR Code)
    """
    nome = nome[:25].upper()
    cidade = cidade[:15].upper()

    # 00 - Payload Format Indicator
    payload = _add_field('00', '01')

    # 26 - Merchant Account Information
    gui = 'br.gov.bcb.pix'  # GUI do PIX
    pix_account = _add_field('01', chave_pix)
    merchant_info = _add_field('00', gui) + pix_account
    payload += _add_field('26', merchant_info)

    # 52 - Merchant Category Code (supermercado)
    payload += _add_field('52', '5411')

    # 53 - Transaction Currency (986 = BRL)
    payload += _add_field('53', '986')

    # 54 - Transaction Amount (opcional)
    if valor is not None and valor > 0:
        payload += _add_field('54', f'{valor:.2f}')

    # 58 - Country Code
    payload += _add_field('58', 'BR')

    # 59 - Merchant Name
    payload += _add_field('59', nome)

    # 60 - Merchant City
    payload += _add_field('60', cidade)

    # 62 - Additional Data Field
    txid_field = _add_field('05', txid)
    payload += _add_field('62', txid_field)

    # 63 - CRC16 (checksum, deve ser o último campo)
    crc = _crc16(payload + '6304')
    payload += _add_field('63', crc)

    return payload


def gerar_qrcode_base64(payload: str) -> str:
    """Gera imagem QR Code e retorna como base64 para exibir no HTML."""
    img = qrcode.make(payload, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def gerar_qrcode_pix(chave_pix: str, nome: str, cidade: str,
                     valor: float = None, txid: str = None) -> dict:
    """
    Gera payload BR Code + QR Code imagem.
    Retorna dict com payload, qrcode_base64, txid.
    """
    import uuid
    txid = txid or uuid.uuid4().hex[:25].upper()
    payload = gerar_payload_estatico(chave_pix, nome, cidade, valor, txid)
    qrcode_b64 = gerar_qrcode_base64(payload)
    return {
        'payload': payload,
        'qrcode_base64': qrcode_b64,
        'txid': txid,
        'valor': valor,
    }
