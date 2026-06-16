"""
Driver de integração com balanças comerciais.
Suporta protocolos:
- Toledo: protocolo 858 (mais comum)
- Filizola: protocolo contínuo
- Líder: protocolo padrão RS-232
"""
import serial
import serial.tools.list_ports
import re
import time


class BalancaDriver:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.modelo = self.config.get('modelo', 'toledo').lower()
        self.porta = self.config.get('porta', 'COM1')
        self.baudrate = int(self.config.get('baudrate', 9600))
        self.bytesize = int(self.config.get('bytesize', 8))
        self.parity = self.config.get('parity', 'N')
        self.stopbits = int(self.config.get('stopbits', 1))
        self.timeout = int(self.config.get('timeout', 5))
        self.prefixo = self.config.get('prefixo', '')
        self.sufixo = self.config.get('sufixo', '')
        self._serial = None

    def conectar(self):
        try:
            self._serial = serial.Serial(
                port=self.porta,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
            )
            return True
        except serial.SerialException as e:
            raise ConnectionError(f'Falha ao conectar na balança {self.modelo} na porta {self.porta}: {e}')

    def desconectar(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None

    def ler_peso(self) -> dict:
        if not self._serial or not self._serial.is_open:
            self.conectar()

        if self.modelo == 'toledo':
            return self._ler_toledo()
        elif self.modelo == 'filizola':
            return self._ler_filizola()
        elif self.modelo == 'lider':
            return self._ler_lider()
        else:
            raise ValueError(f'Modelo de balança não suportado: {self.modelo}')

    def _limpar_buffer(self):
        if self._serial and self._serial.is_open:
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()

    def _parse_peso(self, valor_str: str) -> dict:
        """Converte string de peso para valor numérico"""
        valor_str = valor_str.strip()
        if not valor_str:
            return {'sucesso': False, 'erro': 'Balança sem resposta'}
        valor_str = re.sub(r'[^0-9.,\-]', '', valor_str)
        valor_str = valor_str.replace(',', '.')
        try:
            peso = float(valor_str)
            return {
                'sucesso': True,
                'peso': peso,
                'peso_str': f'{peso:.3f}',
                'unidade': 'kg',
            }
        except ValueError:
            return {'sucesso': False, 'erro': f'Peso inválido lido: {valor_str}', 'raw': valor_str}

    def _ler_toledo(self) -> dict:
        """Protocolo Toledo 858 - Standard"""
        self._limpar_buffer()
        comando = b'\x05'  # ENQ - solicita peso
        self._serial.write(comando)
        time.sleep(0.3)
        resposta = self._serial.read(20)
        if not resposta:
            return {'sucesso': False, 'erro': 'Sem resposta da balança Toledo'}
        try:
            resposta_str = resposta.decode('ascii', errors='ignore')
            peso_match = re.search(r'(\d+\.?\d*)', resposta_str)
            if peso_match:
                return self._parse_peso(peso_match.group(1))
        except Exception as e:
            return {'sucesso': False, 'erro': f'Erro lendo Toledo: {e}'}
        return {'sucesso': False, 'erro': f'Resposta não reconhecida: {resposta.hex()}'}

    def _ler_filizola(self) -> dict:
        """Protocolo Filizola - modo contínuo"""
        self._limpar_buffer()
        time.sleep(0.2)
        resposta = self._serial.read(25)
        if not resposta:
            return {'sucesso': False, 'erro': 'Sem resposta da balança Filizola'}
        try:
            resposta_str = resposta.decode('ascii', errors='ignore')
            peso_match = re.search(r'(\d+\.?\d*)', resposta_str)
            if peso_match:
                return self._parse_peso(peso_match.group(1))
        except Exception as e:
            return {'sucesso': False, 'erro': f'Erro lendo Filizola: {e}'}
        return {'sucesso': False, 'erro': f'Resposta não reconhecida: {resposta.hex()}'}

    def _ler_lider(self) -> dict:
        """Protocolo Líder - RS-232 padrão"""
        self._limpar_buffer()
        comando = b'W\r\n'
        self._serial.write(comando)
        time.sleep(0.3)
        resposta = self._serial.read(30)
        if not resposta:
            return {'sucesso': False, 'erro': 'Sem resposta da balança Líder'}
        try:
            resposta_str = resposta.decode('ascii', errors='ignore')
            peso_match = re.search(r'(\d+\.?\d*)', resposta_str)
            if peso_match:
                return self._parse_peso(peso_match.group(1))
        except Exception as e:
            return {'sucesso': False, 'erro': f'Erro lendo Líder: {e}'}
        return {'sucesso': False, 'erro': f'Resposta não reconhecida: {resposta.hex()}'}

    @staticmethod
    def listar_portas() -> list:
        """Lista portas seriais disponíveis no sistema"""
        portas = []
        try:
            for p in serial.tools.list_ports.comports():
                portas.append({
                    'dispositivo': p.device,
                    'descricao': p.description,
                    'fabricante': p.manufacturer or '',
                })
        except Exception:
            pass
        return portas

    @staticmethod
    def testar_conexao(modelo, porta, baudrate=9600) -> dict:
        """Testa conexão com a balança"""
        cfg = {'modelo': modelo, 'porta': porta, 'baudrate': baudrate}
        driver = BalancaDriver(cfg)
        try:
            resultado = driver.ler_peso()
            driver.desconectar()
            return resultado
        except Exception as e:
            return {'sucesso': False, 'erro': str(e)}
