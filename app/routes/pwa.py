from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('pwa', __name__, url_prefix='/pwa')


@bp.route('/consulta')
def consulta():
    return render_template('pwa_consulta.html')