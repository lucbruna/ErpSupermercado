import hashlib

def digito_verificador(chave_sem_dv):
    """Calcula o DV da chave de 44 digitos modulo 11"""
    soma = 0
    peso = 2
    for i in range(len(chave_sem_dv) - 1, -1, -1):
        soma += int(chave_sem_dv[i]) * peso
        peso += 1
        if peso > 9:
            peso = 2
    resto = soma % 11
    dv = 0 if resto < 2 else 11 - resto
    return str(dv)


def gerar_chave(cnpj, modelo, serie, numero, uf='35', ambiente='2'):
    """Gera chave de 44 posicoes conforme manual NFe"""
    cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
    from datetime import datetime
    agora = datetime.now()
    aamm = agora.strftime('%y%m')
    tipo_emissao = '1'
    chave = f'{uf}{aamm}{cnpj_limpo}{modelo}{str(serie).zfill(3)}{str(numero).zfill(9)}{tipo_emissao}'
    chave += digito_verificador(chave)
    return chave


def format_cnpj(n):
    return n.replace('.', '').replace('/', '').replace('-', '') if n else ''


def format_cpf(n):
    return n.replace('.', '').replace('-', '') if n else ''


def format_telefone(tel):
    if not tel:
        return ''
    t = tel.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
    return t


UF_CODIGOS = {
    'AC': '12', 'AL': '27', 'AP': '16', 'AM': '13', 'BA': '29',
    'CE': '23', 'DF': '53', 'ES': '32', 'GO': '52', 'MA': '21',
    'MT': '51', 'MS': '50', 'MG': '31', 'PA': '15', 'PB': '25',
    'PR': '41', 'PE': '26', 'PI': '22', 'RJ': '33', 'RN': '24',
    'RS': '43', 'RO': '11', 'RR': '14', 'SC': '42', 'SP': '35',
    'SE': '28', 'TO': '17',
}


SEFAZ_URLS = {
    '35': {
        '1': 'https://nfe.fazenda.sp.gov.br/ws/nfeAutorizacao.asmx',
        '2': 'https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeAutorizacao.asmx',
        'nfc_e': {
            '1': 'https://nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx',
            '2': 'https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx',
        }
    },
    # Adicionar outros estados conforme necessidade
}
