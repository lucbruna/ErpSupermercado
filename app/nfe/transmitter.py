from lxml import etree
from zeep import Client
from zeep.transports import Transport
from requests import Session
from requests_pkcs12 import Pkcs12Adapter
import os


def _get_session(certificado_path, senha):
    """Cria sessao requests com certificado A1 para comunicacao SSL"""
    if not certificado_path or not os.path.exists(certificado_path):
        raise FileNotFoundError(f'Certificado nao encontrado: {certificado_path}')

    session = Session()
    session.mount('https://', Pkcs12Adapter(
        pkcs12_filename=certificado_path,
        pkcs12_password=senha,
    ))
    return session


def transmitir_nfce(xml_assinado, config, empresa):
    """Transmite NFC-e para SEFAZ via SOAP - ambiente real"""
    from app.nfe.utils import UF_CODIGOS
    uf = empresa.uf or 'SP'
    cod_uf = UF_CODIGOS.get(uf, '35')
    amb = config.ambiente

    urls = _get_urls_nfce(cod_uf, amb)
    if not urls:
        raise ValueError(f'URL de autorizacao nao configurada para UF {uf} ambiente {amb}')

    session = _get_session(config.certificado_digital, config.certificado_senha)
    transport = Transport(session=session)

    client = Client(urls['wsdl'], transport=transport)

    # Monta o envelope SOAP conforme leiaute da SEFAZ
    nfe_dados_msg = xml_assinado.decode('utf-8')

    try:
        result = client.service.nfeAutorizacaoLote(
            versao='4.00',
            idLote=str(config.proximo_numero_nfce - 1).zfill(15),
            envio={
                'NFe': nfe_dados_msg,
            }
        )
        return _processar_retorno(result)
    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e),
            'protocolo': None,
            'status': '99',
        }


def transmitir_cancelamento(xml_evento_assinado, config, empresa, chave):
    """Transmite evento de cancelamento para SEFAZ"""
    from app.nfe.utils import UF_CODIGOS
    uf = empresa.uf or 'SP'
    cod_uf = UF_CODIGOS.get(uf, '35')
    amb = config.ambiente

    urls = _get_urls_evento(cod_uf, amb)
    if not urls:
        raise ValueError(f'URL de evento nao configurada para UF {uf} ambiente {amb}')

    session = _get_session(config.certificado_digital, config.certificado_senha)
    transport = Transport(session=session)
    client = Client(urls['wsdl'], transport=transport)

    try:
        result = client.service.nfeRecepcaoEvento(
            versao='1.00',
            envio={
                'idLote': '1',
                'evento': xml_evento_assinado.decode('utf-8'),
            }
        )
        return _processar_retorno_cancelamento(result)
    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e),
            'protocolo': None,
        }


def _get_urls_nfce(cod_uf, ambiente):
    """Retorna URLs do webservice NFC-e por UF/ambiente"""
    from app.nfe.utils import SEFAZ_URLS
    uf_config = SEFAZ_URLS.get(cod_uf)
    if not uf_config:
        return None
    nfce = uf_config.get('nfc_e', {})
    url = nfce.get(ambiente)
    if not url:
        return None
    return {
        'wsdl': url.replace('?wsdl', '') + '?wsdl',
        'url': url,
    }


def transmitir_nfe(xml_assinado, config, empresa):
    """Transmite NF-e para SEFAZ via SOAP"""
    from app.nfe.utils import UF_CODIGOS
    uf = empresa.uf or 'SP'
    cod_uf = UF_CODIGOS.get(uf, '35')
    amb = config.ambiente

    urls = _get_urls_nfe(cod_uf, amb)
    if not urls:
        raise ValueError(f'URL de autorizacao NF-e nao configurada para UF {uf} ambiente {amb}')

    session = _get_session(config.certificado_digital, config.certificado_senha)
    transport = Transport(session=session)
    client = Client(urls['wsdl'], transport=transport)

    nfe_dados_msg = xml_assinado.decode('utf-8')

    try:
        result = client.service.nfeAutorizacaoLote(
            versao='4.00',
            idLote=str(config.proximo_numero_nfe - 1).zfill(15),
            envio={'NFe': nfe_dados_msg}
        )
        return _processar_retorno(result)
    except Exception as e:
        return {
            'sucesso': False,
            'erro': str(e),
            'protocolo': None,
            'status': '99',
        }


def _get_urls_nfe(cod_uf, ambiente):
    """Retorna URLs do webservice NF-e por UF/ambiente"""
    from app.nfe.utils import SEFAZ_URLS
    uf_config = SEFAZ_URLS.get(cod_uf)
    if not uf_config:
        return None
    url = uf_config.get(ambiente)
    if not url:
        return None
    return {
        'wsdl': url.replace('?wsdl', '') + '?wsdl',
        'url': url,
    }


def _get_urls_evento(cod_uf, ambiente):
    """Retorna URLs do webservice de evento por UF/ambiente"""
    from app.nfe.utils import SEFAZ_URLS
    uf_config = SEFAZ_URLS.get(cod_uf)
    if not uf_config:
        return None
    url = uf_config.get(ambiente)
    if not url:
        return None
    # URL de evento geralmente difere da autorizacao
    url_evento = url.replace('nfeAutorizacao', 'nfeRecepcaoEvento')
    return {
        'wsdl': url_evento + '?wsdl',
        'url': url_evento,
    }


def _processar_retorno(result):
    """Processa o retorno XML da SEFAZ e extrai protocolo/status"""
    try:
        if hasattr(result, 'retEnviNFe'):
            ret = result.retEnviNFe
        else:
            ret = result

        prot = None
        status = '04'
        motivo = None

        if hasattr(ret, 'protNFe'):
            prot_info = ret.protNFe
            if hasattr(prot_info, 'infProt'):
                prot = prot_info.infProt.nProt
                status = prot_info.infProt.cStat
                motivo = prot_info.infProt.xMotivo

        return {
            'sucesso': status in ('100', '150', '101'),
            'protocolo': prot,
            'status': '04' if status in ('100', '150', '101') else '99',
            'codigo_sefaz': status,
            'motivo': motivo,
        }

    except Exception as e:
        return {
            'sucesso': False,
            'erro': f'Erro ao processar retorno SEFAZ: {str(e)}',
            'protocolo': None,
            'status': '99',
        }


def _processar_retorno_cancelamento(result):
    """Processa retorno do evento de cancelamento"""
    try:
        if hasattr(result, 'retEnvEvento'):
            ret = result.retEnvEvento
        else:
            ret = result

        prot = None
        status = None
        motivo = None

        if hasattr(ret, 'retEvento'):
            ev = ret.retEvento
            if hasattr(ev, 'infEvento'):
                inf = ev.infEvento
                prot = inf.nProt
                status = inf.cStat
                motivo = inf.xMotivo

        return {
            'sucesso': status == '135',
            'protocolo': prot,
            'codigo_sefaz': status,
            'motivo': motivo,
        }

    except Exception as e:
        return {
            'sucesso': False,
            'erro': f'Erro processar cancelamento SEFAZ: {str(e)}',
            'protocolo': None,
        }
