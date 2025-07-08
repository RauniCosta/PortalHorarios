# portal/auth.py

from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from werkzeug.security import check_password_hash
from functools import wraps
from .models import User # Importa o modelo de usuário do banco de dados

# Cria um Blueprint chamado 'auth'. Todas as rotas aqui definidas
# serão prefixadas com o que definirmos ao registrar, se quisermos.
bp = Blueprint('auth', __name__, url_prefix='/admin')

# --- DECORATORS DE AUTENTICAÇÃO ---
# Estes decorators garantem que o usuário está logado e tem a permissão correta.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login')) # Note o '.login' prefixado com o nome do blueprint
        return f(*args, **kwargs)
    return decorated_function

# Substitua a função inteira por esta versão correta

def roles_required(*roles):
    """
    Decorator que verifica se o usuário logado possui uma das permissões (roles) necessárias.
    """
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session:
                # Se por algum motivo 'role' não está na sessão, nega o acesso.
                flash('Sessão inválida. Por favor, faça login novamente.', 'warning')
                return redirect(url_for('auth.login'))

            if session['role'] not in roles:
                # Se a permissão do usuário não está na lista de permissões permitidas, nega o acesso.
                flash('Acesso não autorizado para esta funcionalidade.', 'danger')
                return redirect(url_for('main.dashboard'))

            # Se passou em todas as verificações, executa a rota original.
            return f(*args, **kwargs)

        # A função 'wrapper' deve retornar a 'decorated_function'
        return decorated_function

    # A função 'roles_required' deve retornar o 'wrapper'
    return wrapper


# --- ROTAS DE AUTENTICAÇÃO ---

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """ Rota de login do usuário. """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Lógica de banco de dados: Busca o usuário pelo username.
        user = User.query.filter_by(username=username).first()

        # Verifica se o usuário existe e se a senha está correta
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
            
    return render_template('admin_login.html')

@bp.route('/logout')
def logout():
    """ Rota de logout do usuário. """
    session.clear()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('auth.login'))