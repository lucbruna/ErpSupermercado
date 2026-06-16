from flask import Blueprint, render_template, request, Response
from flask_login import login_required
from app.sped.gerador import gerar_sped_efd

bp = Blueprint('sped', __name__, url_prefix='/sped')


@bp.route('/')
@login_required
def index():
    return render_template('sped_index.html')


@bp.route('/gerar')
@login_required
def gerar():
    competencia = request.args.get('competencia', '')
    if not competencia or '/' not in competencia:
        competencia = ''

    if not competencia:
        return render_template('sped_index.html', erro='Informe a competência (MM/AAAA)')

    conteudo = gerar_sped_efd(competencia)
    if not conteudo:
        return render_template('sped_index.html', erro='Nenhum dado encontrado para esta competência')

    return Response(
        conteudo,
        mimetype='text/plain; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename=SPED_EFD_{competencia.replace("/", "")}.txt'
        }
    )
