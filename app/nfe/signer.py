from lxml import etree
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import os


def assinar_xml(xml_bytes, certificado_path, senha):
    """Assina digitalmente o XML com certificado A1 (PKCS#12)"""
    if not certificado_path or not os.path.exists(certificado_path):
        raise FileNotFoundError(f'Certificado nao encontrado: {certificado_path}')

    with open(certificado_path, 'rb') as f:
        pkcs12 = f.read()

    private_key = serialization.pkcs12.load_key_and_certificates(
        pkcs12, senha.encode('utf-8') if senha else None, default_backend()
    )
    key = private_key[0]
    cert = private_key[1]

    root = etree.fromstring(xml_bytes)
    ns_nfe = 'http://www.portalfiscal.inf.br/nfe'

    infNFe = root.find(f'{{{ns_nfe}}}infNFe')
    if infNFe is None:
        raise ValueError('Tag infNFe nao encontrada no XML')

    id_value = infNFe.get('Id')
    if not id_value:
        raise ValueError('Atributo Id nao encontrado em infNFe')

    signed = XMLSigner(
        method=methods.enveloped,
        signature_algorithm='rsa-sha1',
        digest_algorithm='sha1',
        c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315',
    ).sign(
        root,
        key=key,
        cert=cert,
        reference_uri=f'#{id_value}',
    )

    return etree.tostring(signed, xml_declaration=True, encoding='UTF-8', pretty_print=True)


def assinar_evento(xml_bytes, certificado_path, senha):
    """Assina XML de evento (cancelamento, CC-e)"""
    if not certificado_path or not os.path.exists(certificado_path):
        raise FileNotFoundError(f'Certificado nao encontrado: {certificado_path}')

    with open(certificado_path, 'rb') as f:
        pkcs12 = f.read()

    private_key = serialization.pkcs12.load_key_and_certificates(
        pkcs12, senha.encode('utf-8') if senha else None, default_backend()
    )
    key = private_key[0]
    cert = private_key[1]

    root = etree.fromstring(xml_bytes)
    ns_nfe = 'http://www.portalfiscal.inf.br/nfe'

    infEvento = root.find(f'{{{ns_nfe}}}infEvento')
    if infEvento is None:
        raise ValueError('Tag infEvento nao encontrada')

    id_value = infEvento.get('Id')
    if not id_value:
        raise ValueError('Atributo Id nao encontrado em infEvento')

    signed = XMLSigner(
        method=methods.enveloped,
        signature_algorithm='rsa-sha1',
        digest_algorithm='sha1',
        c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315',
    ).sign(
        root,
        key=key,
        cert=cert,
        reference_uri=f'#{id_value}',
    )

    return etree.tostring(signed, xml_declaration=True, encoding='UTF-8', pretty_print=True)
