import click
from flask.cli import with_appcontext
from werkzeug.security import generate_password_hash

# Importa o objeto 'db' e o modelo 'User' da nossa aplicação
from portal.models import db, User

# O decorator @click.command define uma nova função como um comando de terminal.
# Damos um nome para o comando, por exemplo, 'create-admin'.
@click.command('create-admin')
# Adicionamos opções para passar o username, password e role via terminal.
@click.option('--username', prompt=True, help='O nome de usuário para o novo administrador.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='A senha para o novo administrador.')
@click.option('--role', default='Full', type=click.Choice(['Full', 'Supervisor', 'User'], case_sensitive=False), help='A permissão do usuário.')
# @with_appcontext garante que temos acesso ao contexto da aplicação (como o banco de dados).
@with_appcontext
def create_admin_command(username, password, role):
    """Cria um novo usuário administrativo com a permissão especificada."""

    # Verifica se o usuário já existe para não criar duplicatas
    if User.query.filter_by(username=username).first():
        click.echo(f"Erro: O usuário '{username}' já existe.")
        return

    # Cria o hash da senha de forma segura
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    # Cria a nova instância do usuário
    new_admin = User(
        username=username,
        password_hash=hashed_password,
        role=role
    )

    # Adiciona ao banco de dados e salva
    db.session.add(new_admin)
    db.session.commit()

    # Imprime uma mensagem de sucesso no terminal
    click.echo(f"Usuário '{username}' com permissão '{role}' criado com sucesso!")