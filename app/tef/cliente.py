"""
Cliente TEF - Abstração para integração com maquininhas de cartão.
Suporta:
- Modo simulado (teste/homologação)
- Integração real: Rede, Cielo, GetNet, Stone, PagSeguro, Safrapay

Cada adquirente possui SDK específico. Esta classe abstrai a comunicação
e fornece interface unificada para o PDV.
"""
import json
import os
import platform
from datetime import datetime


class TEFCliente:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.modo_simulado = self.config.get('modo_simulado', True)
        self.adquirente = self.config.get('adquirente', 'simulada').lower()
        self.caminho_pinpad = self.config.get('caminho_pinpad', '')
        self.codigo_loja = self.config.get('codigo_loja', '')
        self.codigo_terminal = self.config.get('codigo_terminal', '001')

    def processar_pagamento(self, valor: float, forma: str = 'debito', parcelas: int = 1) -> dict:
        if self.modo_simulado:
            return self._simular_pagamento(valor, forma, parcelas)
        metodo = f'_pagamento_{self.adquirente}'
        metodo_pag = getattr(self, metodo, None)
        if metodo_pag:
            return metodo_pag(valor, forma, parcelas)
        return self._realizar_pagamento_generico(valor, forma, parcelas)

    def cancelar_transacao(self, nsu: str, valor: float) -> dict:
        if self.modo_simulado:
            return {'sucesso': True, 'nsu_cancelamento': f'CAN{nsu}', 'mensagem': 'Cancelamento simulado'}
        metodo = f'_cancelar_{self.adquirente}'
        metodo_can = getattr(self, metodo, None)
        if metodo_can:
            return metodo_can(nsu, valor)
        return {'sucesso': False, 'mensagem': 'Cancelamento não disponível para esta adquirente'}

    def _simular_pagamento(self, valor, forma, parcelas):
        from random import randint
        nsu = f'{randint(100000, 999999)}'
        bandeiras = {'debito': 'Débito Simulada', 'credito': 'Crédito Simulada', 'credito_parcelado': 'Crédito Simulada'}
        return {
            'sucesso': True,
            'nsu': nsu,
            'autorizacao': f'A{randint(100000, 999999)}',
            'bandeira': bandeiras.get(forma, 'Simulada'),
            'mensagem': 'Transação aprovada',
            'parcelas': parcelas,
            'valor': valor,
            'forma': forma,
            'data_hora': datetime.now().isoformat(),
        }

    # ── Integração Rede ─────────────────────────────────────────
    def _pagamento_rede(self, valor, forma, parcelas):
        try:
            if platform.system() != 'Windows':
                return self._fallback_sdk(valor, forma, parcelas, 'Rede')
            from ctypes import CDLL, c_char_p, c_double, c_int
            dll = CDLL(self.caminho_pinpad or 'C:\\TEF\\Rede\\tef.dll')
            dll.ProcessarPagamento.argtypes = [c_double, c_char_p, c_int, c_char_p, c_char_p]
            dll.ProcessarPagamento.restype = c_char_p
            resultado = dll.ProcessarPagamento(
                c_double(valor),
                c_char_p(forma.encode('utf-8')),
                c_int(parcelas),
                c_char_p(self.codigo_loja.encode('utf-8')),
                c_char_p(self.codigo_terminal.encode('utf-8')),
            )
            if resultado:
                return json.loads(resultado.decode('utf-8'))
            return {'sucesso': False, 'mensagem': 'Sem resposta da DLL Rede'}
        except Exception as e:
            return {'sucesso': False, 'mensagem': f'Erro Rede TEF: {str(e)}'}

    # ── Integração Cielo ────────────────────────────────────────
    def _pagamento_cielo(self, valor, forma, parcelas):
        try:
            if platform.system() != 'Windows':
                return self._fallback_sdk(valor, forma, parcelas, 'Cielo')
            from ctypes import CDLL
            dll = CDLL(self.caminho_pinpad or 'C:\\TEF\\Cielo\\Cielo.Tef.dll')
            dll.IniciarTransacao.argtypes = [c_char_p]
            dll.IniciarTransacao.restype = c_char_p
            dados = json.dumps({
                'valor': int(valor * 100),
                'tipo': forma,
                'parcelas': parcelas,
                'codigo_loja': self.codigo_loja,
                'terminal': self.codigo_terminal,
            })
            resultado = dll.IniciarTransacao(c_char_p(dados.encode('utf-8')))
            if resultado:
                return json.loads(resultado.decode('utf-8'))
            return {'sucesso': False, 'mensagem': 'Sem resposta da DLL Cielo'}
        except Exception as e:
            return {'sucesso': False, 'mensagem': f'Erro Cielo TEF: {str(e)}'}

    # ── Integração GetNet ────────────────────────────────────────
    def _pagamento_getnet(self, valor, forma, parcelas):
        try:
            return self._chamar_api_rest(
                'https://api.getnet.com.br/v1/payments/credit',
                {
                    'amount': int(valor * 100),
                    'currency': 'BRL',
                    'installments': parcelas,
                    'payment_type': 'debit' if forma == 'debito' else 'credit',
                    'terminal': self.codigo_terminal,
                }
            )
        except Exception as e:
            return {'sucesso': False, 'mensagem': f'Erro GetNet: {str(e)}'}

    # ── Integração Stone ────────────────────────────────────────
    def _pagamento_stone(self, valor, forma, parcelas):
        try:
            dados = {
                'amount': int(valor * 100),
                'type': forma,
                'installments': parcelas,
                'terminal_id': self.codigo_terminal,
            }
            return self._chamar_api_rest('https://api.stone.com.br/v1/transactions', dados)
        except Exception as e:
            return {'sucesso': False, 'mensagem': f'Erro Stone: {str(e)}'}

    # ── Integração PagSeguro ────────────────────────────────────
    def _pagamento_pagseguro(self, valor, forma, parcelas):
        try:
            dados = {
                'reference': datetime.now().strftime('%Y%m%d%H%M%S'),
                'amount': {'value': int(valor * 100), 'currency': 'BRL'},
                'payment_method': {'type': 'CREDIT_CARD' if 'credito' in forma else 'DEBIT_CARD'},
                'installments': parcelas,
            }
            return self._chamar_api_rest('https://api.pagseguro.com/charges', dados)
        except Exception as e:
            return {'sucesso': False, 'mensagem': f'Erro PagSeguro: {str(e)}'}

    # ── Integração Safrapay ─────────────────────────────────────
    def _pagamento_safrapay(self, valor, forma, parcelas):
        try:
            dados = {
                'valor': int(valor * 100),
                'tipo_transacao': 'debito' if forma == 'debito' else 'credito',
                'parcelas': parcelas,
                'terminal': self.codigo_terminal,
            }
            return self._chamar_api_rest('https://api.safrapay.com.br/v1/transacoes', dados)
        except Exception as e:
            return {'sucesso': False, 'mensagem': f'Erro Safrapay: {str(e)}'}

    # ── Genérico (fallback) ─────────────────────────────────────
    def _realizar_pagamento_generico(self, valor, forma, parcelas):
        return self._fallback_sdk(valor, forma, parcelas, self.adquirente)

    def _fallback_sdk(self, valor, forma, parcelas, adquirente):
        return {
            'sucesso': False,
            'mensagem': f'SDK {adquirente} não disponível no sistema operacional {platform.system()}',
            'modo_simulado': True,
        }

    def _chamar_api_rest(self, url, dados):
        """Chama API REST de adquirente via requests"""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.codigo_loja}',
            'X-Terminal': self.codigo_terminal,
        }
        resp = session.post(url, json=dados, headers=headers, timeout=15)
        if resp.ok:
            return {'sucesso': True, 'dados': resp.json(), 'nsu': resp.json().get('id', '')}
        return {'sucesso': False, 'mensagem': f'HTTP {resp.status_code}: {resp.text[:200]}'}
