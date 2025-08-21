# portal/auth.py

import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from .models import db, User

bp = Blueprint('auth', __name__, url_prefix='/admin')

@bp.before_app_request
def load_logged_in_user():
    """
    Carrega os dados do usuário logado a partir da sessão antes de cada requisição.
    """
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = User.query.get(user_id)

def login_required(view):
    """
    Decorator que redireciona usuários não logados para a página de login.
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

def roles_required(roles):
    """
    Decorator que verifica se o usuário logado tem um dos papéis necessários.
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # --- CORREÇÃO APLICADA AQUI ---
            # A verificação agora é feita através do 'g.user', que é mais seguro
            # e confiável do que ler diretamente da sessão em todos os lugares.
            if g.user is None or g.user.role not in roles:
                flash('Você não tem permissão para acessar esta página.', 'warning')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@bp.route('/login', methods=('GET', 'POST'))
def login():
    """
    Processa o login do usuário.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        user = User.query.filter_by(username=username).first()

        if user is None or not check_password_hash(user.password_hash, password):
            error = 'Usuário ou senha inválidos.'
        
        if error is None:
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Bem-vindo, {user.username}!', 'success')
            return redirect(url_for('main.dashboard'))

        flash(error, 'danger')
    
    return render_template('admin_login.html')

@bp.route('/logout')
def logout():
    """
    Limpa a sessão atual para fazer logout.
    """
    session.clear()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('auth.login'))