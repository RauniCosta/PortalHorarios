# gerar_hash.py
from werkzeug.security import generate_password_hash
from getpass import getpass

# Usamos getpass para que a senha não seja exibida no terminal ao digitar
senha = getpass("Digite a nova senha de admin: ")
senha_confirmacao = getpass("Confirme a nova senha: ")

if senha != senha_confirmacao:
    print("\nAs senhas não coincidem. Operação cancelada.")
elif not senha:
    print("\nA senha não pode ser vazia. Operação cancelada.")
else:
    # Gera o hash usando o mesmo método que a sua aplicação utiliza
    hash_gerado = generate_password_hash(senha)
    print("\nSenha válida. Seu novo hash é:\n")
    print(hash_gerado)
    print("\nCopie a linha acima e cole no arquivo dados.json.")