# 🛒 ERP Supermercado

Sistema completo de gestão para supermercados — 100% nacional, foco em conformidade fiscal brasileira.

## Funcionalidades

### 🏪 PDV (Frente de Caixa)
- Venda rápida com busca por código de barras
- **PIX** com QR Code EMV (copia e cola)
- **TEF** real (Rede, Cielo, GetNet, Stone, PagSeguro, Safrapay)
- **Balança** serial (Toledo, Filizola, Líder)
- Promoções e desconto por item
- Mesas / Comandas
- Orçamentos e Devoluções
- Alerta de validade (lotes vencendo)

### 📦 Estoque
- Entrada / Saída / Saldo
- Lotes com validade
- Curva ABC
- Sugestão automática de compra (ABC + estoque mínimo)
- Kardex / Ficha de estoque
- Inventário
- Transferência entre filiais
- Impressão de etiquetas (gôndola, balança, código barras, A4)

### 💰 Financeiro
- Contas a Pagar / Receber
- Fluxo de caixa
- Boletos registrados
- Conciliação bancária (importar extrato)
- Cheques (em carteira, depositar, compensar, devolver)
- Gestão de ativos

### 📄 Fiscal
- **NFC-e** (modelo 65) — geração XML + assinatura A1 + transmissão SEFAZ
- **NF-e** (modelo 55) — completa com devolução
- **SAT** (CF-e) — emissor com DLL
- **NFS-e** — nota fiscal de serviço
- **SPED Fiscal** — geração arquivo
- **TEF** — integração com múltiplas credenciadoras

### 👥 RH
- Funcionários, Cargos, Setores
- Folha de pagamento
- Ponto eletrônico
- **eSocial** (S-1000, S-2200, S-2299, S-1200)
- **CAGED** — admissão / desligamento
- Metas e comissão de vendedores

### 📊 Relatórios
- Dashboard Gerencial (gráficos vendas, margem, ticket)
- **Tempo real** via WebSocket
- Vendas por período/vendedor/produto
- Margem por categoria
- Giro de estoque
- DRE
- Comparativo ano vs ano
- Meta vs Real

### 📈 CRM / Fidelidade
- Pontos fideliade (configurável)
- Aniversário, histórico de compras
- Metas de vendas

### 📋 Compras
- Pedidos de compra
- Cotação automática com fornecedores (via email)

### 🏗️ Produção
- Ordem de produção (açougue, padaria, hortifruti)
- Controle previsto vs produzido

### 🧾 Contabilidade
- Plano de contas (37 contas padrão)
- Lançamentos contábeis
- ECD / ECF — geração automática

### 🏢 Multi-filial
- Cadastro de filiais
- Transferência de estoque entre lojas

### 🔒 Segurança
- Login com senha forte (8+ chars, maiúscula, número, especial)
- Rate limiting (5 tentativas / 5 min)
- CSRF automático
- Headers de segurança (HSTS, X-Frame-Options, etc.)
- Auditoria com diff (valores anteriores vs novos)
- **Biometria facial** (login por reconhecimento facial)

### 📱 Mobile
- PWA (consulta preço/estoque pelo celular)
- API REST completa

### 🔗 Integrações
- **WhatsApp** — notificações e cobrança
- **Email** — SMTP configurável (cotação, boletos)
- **CSV** — importar/exportar produtos e clientes

## Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11+ / Flask |
| Banco | PostgreSQL |
| ORM | SQLAlchemy |
| Auth | Flask-Login + Werkzeug |
| Tempo Real | Flask-SocketIO |
| Frontend | Jinja2 + Bootstrap 5 + Chart.js |
| NFC-e/NF-e | lxml + signxml + zeep + requests-pkcs12 |
| SAT | DLL nativa (Windows) |
| TEF | DLL nativa + REST |
| PIX | QR Code (qrcode[crcmod]) |
| Biometria | OpenCV (Haar + LBPH) |
| Balança | pyserial |
| Relatórios | WeasyPrint (PDF) |

## Requisitos

- Python 3.11+
- PostgreSQL 15+
- Windows (para SAT DLL, TEF DLL, balança serial)
- Certificado digital A1 (PKCS#12) para NFC-e/NF-e

## Instalação

```bash
# Clone
git clone https://github.com/lucbruna/ErpSupermercado.git
cd ErpSupermercado/backend

# Ambiente virtual
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux

# Dependências
pip install -r requirements.txt

# Configurar .env (copie .env.example)
cp .env.example .env
# Edite .env com suas credenciais do PostgreSQL

# Iniciar
python run.py
```

Acesse `http://localhost:5000` — login: `admin` — senha: `Admin@123`

## Variáveis de Ambiente (.env)

```env
SECRET_KEY=chave_secreta_aqui
DB_HOST=localhost
DB_PORT=5432
DB_USER=seu_usuario
DB_PASS=sua_senha
DB_NAME=erp_supermercado
FLASK_DEBUG=False
SESSION_COOKIE_SECURE=False
```

## Estrutura do Projeto

```
backend/
├── run.py                    # Ponto de entrada
├── migrate.py                # Migrações (ALTER TABLE)
├── init_db.py                # Inicialização banco
├── backup_db.py              # Backup automático
├── .env                      # Configurações sensíveis
├── app/
│   ├── __init__.py           # App factory, CSRF, rate limit
│   ├── audit.py              # Auditoria
│   ├── print_utils.py        # DANFE, cupom PDF
│   ├── socketio_events.py    # WebSockets tempo real
│   ├── models/
│   │   └── models.py         # 40+ modelos SQLAlchemy
│   ├── routes/               # 37 blueprints
│   │   ├── auth.py, pdv.py, estoque.py, ...
│   │   ├── nfe.py, nfse.py, fiscal.py
│   │   ├── biometria.py, dashboard_real.py
│   │   └── ... (37 arquivos)
│   ├── nfe/                  # NFC-e / NF-e
│   │   ├── xml_generator.py  # Geração XML (NFC-e + NF-e)
│   │   ├── signer.py         # Assinatura A1
│   │   ├── transmitter.py    # Transmissão SEFAZ
│   │   └── utils.py          # Chave 44 dígitos, URLs SEFAZ
│   ├── sat/                  # SAT
│   ├── tef/                  # TEF
│   ├── pix/                  # PIX
│   ├── balanca/              # Balança serial
│   ├── biometria/            # Reconhecimento facial
│   ├── contabilidade/        # ECD, ECF, seed
│   ├── esocial/              # eSocial
│   ├── sped/                 # SPED Fiscal
│   ├── templates/            # 100+ Jinja2
│   └── static/               # CSS, JS, PWA
└── requirements.txt
```

## Blueprints (37)

`auth`, `cadastros`, `estoque`, `pdv`, `usuarios`, `compras`, `rh`, `financeiro`, `fiscal`, `precos`, `relatorios`, `auditoria`, `notificacoes`, `backup`, `orcamentos`, `devolucao`, `imprimir`, `sped`, `tef`, `contabilidade`, `pix`, `cotacoes`, `config_email`, `transferencias`, `crm`, `api`, `csv_import`, `producao`, `mesas`, `cheques`, `ativos`, `nfse`, `config_whatsapp`, `pwa`, `nfe`, `biometria`, `dashboard_real`

## Licença

**Business Source License 1.1** — Uso comercial permitido apenas com licença do autor.

- **Uso não-comercial**: permitido (estudo, teste, educação)
- **Uso comercial**: requer licença comercial com o licenciante
- **A partir de 16/06/2029**: converte automaticamente para GPL v3

Veja o arquivo [LICENSE](LICENSE) para detalhes completos.
