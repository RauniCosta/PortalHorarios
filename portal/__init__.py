# =============================================================================
#                        PORTAL DE HORÁRIOS - V1.4
# =============================================================================
#
#  Autor: RAUNI SERGIO COSTA
#  Email: rauni.costa@outlook.com.br
#  Data de Criação: 2025-06-01
#  Última Modificação: 2025-06-14
#  Versão: 1.4
#
#  Descrição:
#  Este script é o servidor backend para a aplicação "Portal de Horários".
#  Ele utiliza o framework Flask para fornecer uma API RESTful e renderizar
#  as páginas do painel público e da área administrativa. O sistema permite
#  a visualização e gerenciamento completo de horários escolares, incluindo
#  turmas, professores, disciplinas e alocação de salas.
#
# =============================================================================

# -*- coding: utf-8 -*-
# =============================================================================
# 1. IMPORTAÇÕES E CONFIGURAÇÃO INICIAL
# =============================================================================
# portal/__init__.py

import os
from flask import Flask
from .config import Config      # Importa a classe de configuração
from .models import db          # Importa o objeto db dos nossos modelos

def create_app():
    """
    Função Application Factory. Cria e configura a instância da aplicação Flask.
    """
    app = Flask(__name__, instance_relative_config=True)

    # 1. Carrega a configuração a partir do nosso arquivo/classe de configuração.
    app.config.from_object(Config)

    # 2. Inicializa as extensões do Flask (neste caso, o banco de dados).
    db.init_app(app)

    # 3. Importa e registra os Blueprints (nossos conjuntos de rotas).
    from . import auth
    app.register_blueprint(auth.bp)

    from . import routes
    app.register_blueprint(routes.bp)
    
    # Torna o endpoint 'index' disponível como 'main.index' para consistência.
    app.add_url_rule('/', endpoint='index')

    # 4. Tenta criar a pasta da instância, se não existir.
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
        
    print("Aplicação criada e configurada com sucesso!")
    
    return app