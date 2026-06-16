from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import Usuario
from app.biometria.reconhecedor import capturar_rosto, treinar, reconhecer
import base64
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

bp = Blueprint('biometria', __name__, url_prefix='/biometria')


@bp.route('/')
@login_required
def dashboard():
    usuarios = Usuario.query.filter_by(ativo=True).order_by(Usuario.nome).all()
    return render_template('bio_dashboard.html', usuarios=usuarios)


@bp.route('/cadastrar/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
def cadastrar(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if request.method == 'POST':
        from app.biometria.reconhecedor import DATA_DIR
        import os
        fotos = [f for f in os.listdir(DATA_DIR) if f.startswith(f'user_{usuario_id}_') and f.endswith('.jpg')]
        if fotos:
            flash(f'Biometria ja cadastrada para {usuario.nome}!', 'info')
            return redirect(url_for('biometria.dashboard'))
        return render_template('bio_capture.html', usuario=usuario)
    return render_template('bio_capture.html', usuario=usuario)


@bp.route('/salvar_capture', methods=['POST'])
@login_required
def salvar_capture():
    usuario_id = request.form.get('usuario_id')
    imagem_b64 = request.form.get('imagem')
    if not usuario_id or not imagem_b64:
        flash('Dados incompletos!', 'danger')
        return redirect(url_for('biometria.dashboard'))

    try:
        img_data = base64.b64decode(imagem_b64.split(',')[1] if ',' in imagem_b64 else imagem_b64)
        np_arr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        rosto_gray, rosto_color, _ = capturar_rosto(frame)
        if rosto_color is None:
            flash('Nenhum rosto detectado na foto! Tente novamente com melhor iluminação.', 'danger')
            return redirect(url_for('biometria.cadastrar', usuario_id=usuario_id))
        ok = treinar(int(usuario_id), rosto_color)
        if ok:
            flash('Rosto cadastrado com sucesso!', 'success')
        else:
            flash('Erro ao cadastrar rosto.', 'danger')
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
    return redirect(url_for('biometria.dashboard'))


@bp.route('/verificar', methods=['POST'])
def verificar():
    imagem_b64 = request.form.get('imagem')
    if not imagem_b64:
        return jsonify({'ok': False, 'erro': 'Imagem nao enviada'})

    try:
        img_data = base64.b64decode(imagem_b64.split(',')[1] if ',' in imagem_b64 else imagem_b64)
        np_arr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        rosto_gray, rosto_color, _ = capturar_rosto(frame)
        if rosto_color is None:
            return jsonify({'ok': False, 'erro': 'Nenhum rosto detectado'})
        label, conf = reconhecer(rosto_color)
        if label is None:
            return jsonify({'ok': False, 'erro': 'Rosto nao reconhecido'})
        usuario = Usuario.query.get(int(label))
        if not usuario or not usuario.ativo:
            return jsonify({'ok': False, 'erro': 'Usuario nao encontrado ou inativo'})
        return jsonify({'ok': True, 'usuario_id': usuario.id, 'nome': usuario.nome})
    except Exception as e:
        return jsonify({'ok': False, 'erro': str(e)})


@bp.route('/login_facial', methods=['GET'])
def login_facial():
    return render_template('bio_login.html')
