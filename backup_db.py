"""
Script de backup automático do banco PostgreSQL.
Uso:
  python backup_db.py                    # backup agora
  python backup_db.py --agendar          # agenda backups diarios via Windows Task Scheduler
"""
import os
import sys
import subprocess
import datetime
import argparse
import shutil

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
DB_NAME = 'erp_supermercado'
DB_USER = 'openpg'
DB_HOST = 'localhost'
DB_PORT = '5432'
RETENTION_DAYS = 30  # remove backups mais antigos que 30 dias


def criar_pasta():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)


def fazer_backup():
    criar_pasta()
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backup_{DB_NAME}_{timestamp}.sql'
    filepath = os.path.join(BACKUP_DIR, filename)

    # Compactar com gzip
    filepath_gz = filepath + '.gz'

    # Usa PGPASSWORD para evitar prompt de senha
    env = os.environ.copy()
    env['PGPASSWORD'] = 'openpgpwd'

    cmd = [
        'pg_dump',
        '-h', DB_HOST,
        '-p', DB_PORT,
        '-U', DB_USER,
        '-d', DB_NAME,
        '--no-owner',
        '--no-acl',
        '--format=c',  # formato custom (compressão nativa)
        '-f', filepath,
    ]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            print(f'[OK] Backup criado: {filename}')
            limpar_antigos()
            return filepath
        else:
            print(f'[ERRO] Falha no backup: {result.stderr}', file=sys.stderr)
            return None
    except FileNotFoundError:
        print('[ERRO] pg_dump não encontrado. Instale o PostgreSQL e adicione ao PATH.', file=sys.stderr)
        return None


def limpar_antigos():
    hoje = datetime.datetime.now()
    for f in os.listdir(BACKUP_DIR):
        fpath = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fpath):
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(fpath))
            if (hoje - mod_time).days > RETENTION_DAYS:
                os.remove(fpath)
                print(f'  Removido backup antigo: {f}')


def listar_backups():
    criar_pasta()
    backups = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        fpath = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            mod = datetime.datetime.fromtimestamp(os.path.getmtime(fpath))
            backups.append({
                'nome': f,
                'tamanho': f'{size / 1024 / 1024:.1f} MB',
                'data': mod.strftime('%d/%m/%Y %H:%M'),
                'caminho': fpath,
            })
    return backups


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backup do banco ERP Supermercado')
    parser.add_argument('--agendar', action='store_true', help='Criar tarefa agendada no Windows')
    args = parser.parse_args()

    if args.agendar:
        import platform
        if platform.system() == 'Windows':
            script_path = os.path.abspath(__file__)
            python_path = sys.executable
            task_name = 'ERP_Supermercado_Backup'
            cmd_create = [
                'schtasks', '/Create', '/SC', 'DAILY', '/TN', task_name,
                '/TR', f'"{python_path}" "{script_path}"',
                '/ST', '03:00', '/F'
            ]
            try:
                subprocess.run(cmd_create, check=True)
                print(f'[OK] Tarefa agendada "{task_name}" criada para 03:00 diariamente.')
            except subprocess.CalledProcessError as e:
                print(f'[ERRO] Falha ao criar tarefa: {e}', file=sys.stderr)
        else:
            print('Agendamento automático disponível apenas no Windows.')
    else:
        fazer_backup()
