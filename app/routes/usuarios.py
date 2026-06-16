from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db, validar_senha
from app.models.models import Usuario, Setor
from functools import wraps
from app.audit import log_auditoria

bp = Blueprint('usuarios', __name__)


def papel_required(*papeis):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if current_user.papel not in papeis:
                flash('Acesso negado!', 'danger')
                return redirect(url_for('cadastros.dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


@bp.route('/usuarios')
@login_required
def lista():
    if current_user.papel == 'admin':
        usuarios = Usuario.query.order_by(Usuario.nome).all()
    elif current_user.papel == 'chefe_setor':
        usuarios = Usuario.query.filter_by(setor_id=current_user.setor_id).order_by(Usuario.nome).all()
    else:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('cadastros.dashboard'))
    setores = Setor.query.filter_by(ativo=True).all()
    return render_template('usuarios_lista.html', usuarios=usuarios, setores=setores)


@bp.route('/usuarios/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if current_user.papel not in ('admin', 'chefe_setor'):
        flash('Acesso negado!', 'danger')
        return redirect(url_for('cadastros.dashboard'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        login = request.form.get('login')
        senha = request.form.get('senha')
        papel = request.form.get('papel')
        setor_id = request.form.get('setor_id') or None

        if not nome or not login or not senha:
            flash('Preencha todos os campos obrigatórios!', 'danger')
            return render_template('usuarios_form.html', setores=Setor.query.filter_by(ativo=True).all())

        erros_senha = validar_senha(senha)
        if erros_senha:
            for e in erros_senha:
                flash(f'Senha fraca: {e}', 'danger')
            return render_template('usuarios_form.html', setores=Setor.query.filter_by(ativo=True).all())

        if Usuario.query.filter_by(login=login).first():
            flash('Login já existe!', 'danger')
            return render_template('usuarios_form.html', setores=Setor.query.filter_by(ativo=True).all())

        if current_user.papel == 'chefe_setor':
            papel = 'funcionario'
            setor_id = current_user.setor_id

        usuario = Usuario(
            nome=nome, login=login,
            senha=generate_password_hash(senha),
            papel=papel, setor_id=setor_id,
            criado_por_id=current_user.id
        )
        db.session.add(usuario)
        db.session.commit()
        log_auditoria(f'Criou usuário: {nome}', 'Usuario', usuario.id)
        flash(f'Usuario {nome} criado com sucesso!', 'success')
        return redirect(url_for('usuarios.lista'))

    setores = Setor.query.filter_by(ativo=True).all()
    return render_template('usuarios_form.html', setores=setores)


@bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    usuario = Usuario.query.get_or_404(id)
    if current_user.papel == 'admin':
        pass
    elif current_user.papel == 'chefe_setor' and usuario.setor_id == current_user.setor_id and usuario.papel == 'funcionario':
        pass
    else:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('usuarios.lista'))

    if request.method == 'POST':
        from app.audit import model_to_dict
        campos = ['nome', 'papel', 'ativo']
        ant = model_to_dict(usuario, campos)
        usuario.nome = request.form.get('nome')
        senha = request.form.get('senha')
        if senha:
            usuario.senha = generate_password_hash(senha)
        if current_user.papel == 'admin':
            usuario.papel = request.form.get('papel')
            usuario.setor_id = request.form.get('setor_id') or None
        usuario.ativo = 'ativo' in request.form
        db.session.commit()
        novos = model_to_dict(usuario, campos)
        log_auditoria(f'Editou usuário: {usuario.nome}', 'Usuario', usuario.id, valores_anteriores=ant, valores_novos=novos)
        flash('Usuario atualizado!', 'success')
        return redirect(url_for('usuarios.lista'))

    setores = Setor.query.filter_by(ativo=True).all()
    return render_template('usuarios_form.html', usuario=usuario, setores=setores)


@bp.route('/setores')
@login_required
@papel_required('admin')
def lista_setores():
    setores = Setor.query.order_by(Setor.nome).all()
    return render_template('setores_lista.html', setores=setores)


@bp.route('/setores/novo', methods=['POST'])
@login_required
@papel_required('admin')
def novo_setor():
    nome = request.form.get('nome')
    if not nome:
        flash('Nome do setor obrigatorio!', 'danger')
        return redirect(url_for('usuarios.lista_setores'))
    if Setor.query.filter_by(nome=nome).first():
        flash('Setor ja existe!', 'danger')
        return redirect(url_for('usuarios.lista_setores'))
    setor = Setor(nome=nome)
    db.session.add(setor)
    db.session.commit()
    log_auditoria(f'Criou setor: {nome}', 'Setor', setor.id)
    flash(f'Setor {nome} criado!', 'success')
    return redirect(url_for('usuarios.lista_setores'))


@bp.route('/usuarios/desativar/<int:id>')
@login_required
def desativar(id):
    u = Usuario.query.get_or_404(id)
    if current_user.papel == 'admin':
        pass
    elif current_user.papel == 'chefe_setor' and u.setor_id == current_user.setor_id and u.papel == 'funcionario':
        pass
    else:
        flash('Acesso negado!', 'danger')
        return redirect(url_for('usuarios.lista'))
    u.ativo = not u.ativo
    db.session.commit()
    log_auditoria(f'{"Ativou" if u.ativo else "Desativou"} usuário: {u.nome}', 'Usuario', u.id)
    flash(f'Usuario {"ativado" if u.ativo else "desativado"}!', 'success')
    return redirect(url_for('usuarios.lista'))


@bp.route('/setores/editar/<int:id>', methods=['POST'])
@login_required
@papel_required('admin')
def editar_setor(id):
    setor = Setor.query.get_or_404(id)
    setor.nome = request.form.get('nome')
    setor.ativo = 'ativo' in request.form
    db.session.commit()
    log_auditoria(f'Editou setor: {setor.nome}', 'Setor', setor.id)
    flash('Setor atualizado!', 'success')
    return redirect(url_for('usuarios.lista_setores'))
