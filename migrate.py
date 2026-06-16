"""
Script de migração para adicionar colunas novas às tabelas existentes.
Executar UMA VEZ: py migrate.py
"""
import sys
import os
from dotenv import load_dotenv
sys.path.insert(0, '.')
load_dotenv()

from app import create_app, db
from sqlalchemy import text

app = create_app()

MIGRACOES = [
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ultimo_login TIMESTAMP",
    "ALTER TABLE empresa ADD COLUMN IF NOT EXISTS cidade_ibge VARCHAR(10)",
    "ALTER TABLE config_fiscal ADD COLUMN IF NOT EXISTS caminho_dll_sat VARCHAR(500)",
    "ALTER TABLE config_fiscal ADD COLUMN IF NOT EXISTS codigo_ativacao_sat VARCHAR(50)",
    "ALTER TABLE config_fiscal ADD COLUMN IF NOT EXISTS cnpj_software_house VARCHAR(18)",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS data_aniversario DATE",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS pontos_fidelidade INTEGER DEFAULT 0",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS ultima_compra TIMESTAMP",
    "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS total_compras NUMERIC(10,2) DEFAULT 0",
    "ALTER TABLE plano_contas ALTER COLUMN tipo TYPE VARCHAR(2)",
]

with app.app_context():
    for sql in MIGRACOES:
        try:
            db.session.execute(text(sql))
            print(f'OK: {sql.split("ADD")[0].strip()}')
        except Exception as e:
            print(f'ERRO: {sql}\n  {e}')
            db.session.rollback()
    db.session.commit()
    print('\nMigrações concluídas!')

    # Recria as novas tabelas (LoginAttempt, Promocao, etc.)
    db.create_all()
    print('Novas tabelas criadas com sucesso!')
