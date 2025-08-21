# tests/test_auth.py
from flask import session

def test_login_logout(client):
    """
    Testa o login usando o usuário 'testuser' e a senha 'testpassword',
    que são criados automaticamente para este ambiente de teste.
    """
    # Tenta fazer login com os dados de teste CORRETOS
    response_login = client.post('/admin/login', data={
        'username': 'testuser',
        'password': 'testpassword'
    }, follow_redirects=True)

    # 1. Verifica se a resposta foi bem-sucedida (status 200)
    assert response_login.status_code == 200
    # 2. Verifica se, após o login, a página contém a mensagem de boas-vindas
    assert b'Bem-vindo, testuser!' in response_login.data
    # 3. Garante que a mensagem de erro NÃO está na página
    assert b'Usuario ou senha invalidos.' not in response_login.data

    # Testa o logout
    response_logout = client.get('/admin/logout', follow_redirects=True)
    assert response_logout.status_code == 200
    # Verifica se a mensagem de logout (com a codificação correta para "Você") está presente
    assert b'Voc\xc3\xaa foi desconectado.' in response_logout.data


def test_login_wrong_password(client):
    """
    Testa a falha de login usando o usuário de teste com uma senha INCORRETA.
    """
    response = client.post('/admin/login', data={
        'username': 'testuser',
        'password': 'senhaerrada'
    }, follow_redirects=True)

    # 1. Verifica se a resposta foi bem-sucedida (ainda retorna a página de login)
    assert response.status_code == 200
    # 2. Verifica se a mensagem de erro (com a codificação correta para "Usuário" e "inválidos") está presente
    assert b'Usu\xc3\xa1rio ou senha inv\xc3\xa1lidos.' in response.data
    # 3. Garante que a mensagem de boas-vindas NÃO está na página
    assert b'Bem-vindo, testuser!' not in response.data