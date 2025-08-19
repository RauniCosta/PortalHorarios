# app.py
from flask import Flask
import os
from waitress import serve
from portal import create_app
from commands import create_admin_command

# Cria a instância da aplicação
app = create_app()
# Registra o comando na interface de linha de comando (CLI) do Flask
app.cli.add_command(create_admin_command)

if __name__ == '__main__':
    # Verifica a variável de ambiente FLASK_ENV
    # Se for 'production', usa o servidor Waitress.
    # Caso contrário, usa o servidor de debug do Flask.
    is_production = os.getenv('FLASK_ENV') == 'production'

    if is_production:
        # --- MODO DE PRODUÇÃO ---
        print("Servidor iniciando em modo de PRODUÇÃO com Waitress.")
        # O waitress escuta por padrão em todas as interfaces (0.0.0.0) na porta 8080
        # Você pode ajustar host e port conforme necessário.
        serve(app, host='0.0.0.0', port=8080)
    else:
        # --- MODO DE DESENVOLVIMENTO ---
        print("Servidor iniciando em modo de DESENVOLVIMENTO com o servidor de debug do Flask.")
        # Use a porta 5000 para desenvolvimento para não conflitar com a porta de produção
        app.run(host='0.0.0.0', port=5000, debug=True)