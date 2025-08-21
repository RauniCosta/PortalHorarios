# tests/conftest.py
import pytest
from portal import create_app
from portal.models import db, User
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    """Cria e configura uma nova instância da aplicação para cada teste."""
    # Configura a aplicação para usar um banco de dados SQLite em memória
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False, # Desabilita CSRF para facilitar os testes de formulário
        'SECRET_KEY': 'test'
    })

    with app.app_context():
        # Cria todas as tabelas do banco de dados
        db.create_all()
        # Cria um usuário de teste inicial
        hashed_password = generate_password_hash('testpassword')
        test_user = User(username='testuser', password_hash=hashed_password, role='Full')
        db.session.add(test_user)
        db.session.commit()

    yield app

    # A limpeza (drop_all) acontece implicitamente ao usar um banco em memória

@pytest.fixture
def client(app):
    """Um cliente de teste para a aplicação."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Um executor de comandos para a CLI do Flask."""
    return app.test_cli_runner()