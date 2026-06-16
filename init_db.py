"""
Script de inicialização do banco de dados.
Use apenas em ambiente de desenvolvimento.
Em produção, crie o banco manualmente com permissões adequadas.
"""
import os
import psycopg2

DB_USER = os.environ.get('DB_USER', 'openpg')
DB_PASS = os.environ.get('DB_PASS', 'openpgpwd')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'erp_supermercado')

conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname='postgres')
conn.autocommit = True
cur = conn.cursor()
cur.execute(
    f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'"
)
if not cur.fetchone():
    cur.execute(f"CREATE DATABASE {DB_NAME} ENCODING 'UTF8'")
    print(f'Banco {DB_NAME} criado!')
else:
    print(f'Banco {DB_NAME} já existe.')
cur.close()
conn.close()
