import os
import sys
from datetime import datetime
from flask import Blueprint, render_template, flash, redirect, url_for, send_file, abort
from flask_login import login_required

bp = Blueprint('backup', __name__, url_prefix='/backup')

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups')


def _sanitizar_nome(nome):
    """Remove path traversal e caracteres perigosos do nome do arquivo"""
    nome = os.path.basename(nome)  # remove qualquer path
    nome = ''.join(c for c in nome if c.isalnum() or c in '._-')
    return nome


@bp.route('/')
@login_required
def lista():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    backups = []
    for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
        fpath = os.path.join(BACKUP_DIR, f)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            mod = os.path.getmtime(fpath)
            backups.append({
                'nome': f,
                'tamanho': f'{size / 1024 / 1024:.1f} MB',
                'data': datetime.fromtimestamp(mod).strftime('%d/%m/%Y %H:%M'),
            })
    return render_template('backup_lista.html', backups=backups)


@bp.route('/executar')
@login_required
def executar():
    try:
        import subprocess
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_port = os.environ.get('DB_PORT', '5432')
        db_name = os.environ.get('DB_NAME', 'erp_supermercado')
        db_user = os.environ.get('DB_USER', 'openpg')
        db_pass = os.environ.get('DB_PASS', 'openpgpwd')

        env = os.environ.copy()
        env['PGPASSWORD'] = db_pass
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        filepath = os.path.join(BACKUP_DIR, f'backup_erp_supermercado_{timestamp}.sql')
        cmd = [
            'pg_dump', '-h', db_host, '-p', db_port,
            '-U', db_user, '-d', db_name,
            '--no-owner', '--no-acl', '--format=c', '-f', filepath
        ]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            flash('Backup criado com sucesso!', 'success')
        else:
            flash(f'Erro no backup: {result.stderr[:200]}', 'danger')
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('backup.lista'))


@bp.route('/baixar/<nome>')
@login_required
def baixar(nome):
    nome = _sanitizar_nome(nome)
    fpath = os.path.join(BACKUP_DIR, nome)
    if not os.path.exists(fpath) or not fpath.startswith(os.path.abspath(BACKUP_DIR)):
        abort(404)
    return send_file(fpath, as_attachment=True)


@bp.route('/excluir/<nome>')
@login_required
def excluir(nome):
    nome = _sanitizar_nome(nome)
    fpath = os.path.join(BACKUP_DIR, nome)
    if os.path.exists(fpath) and fpath.startswith(os.path.abspath(BACKUP_DIR)):
        os.remove(fpath)
        flash('Backup excluído!', 'success')
    else:
        flash('Arquivo não encontrado!', 'danger')
    return redirect(url_for('backup.lista'))


@bp.route('/agendar')
@login_required
def agendar():
    try:
        import subprocess
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backup_db.py')
        python_path = sys.executable
        task_name = 'ERP_Supermercado_Backup'
        cmd = [
            'schtasks', '/Create', '/SC', 'DAILY', '/TN', task_name,
            '/TR', f'"{python_path}" "{script_path}"',
            '/ST', '03:00', '/F'
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        flash(f'Tarefa agendada "{task_name}" criada para 03:00 diariamente!', 'success')
    except subprocess.CalledProcessError as e:
        flash(f'Erro ao agendar: {e.stderr.decode() if e.stderr else str(e)}', 'danger')
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('backup.lista'))
