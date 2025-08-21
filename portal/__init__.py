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
from .config import Config
from .models import db

def create_app(test_config=None):  # <-- MUDANÇA AQUI
    """
    Função Application Factory. Cria e configura a instância da aplicação Flask.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Carrega a configuração. Se uma config de teste for passada, ela tem prioridade.
    if test_config is None:
        # Carrega a configuração normal a partir da classe Config
        app.config.from_object(Config)
    else:
        # Carrega a configuração de teste passada para a função
        app.config.from_mapping(test_config)

    # O resto da função continua exatamente igual...
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import routes
    app.register_blueprint(routes.bp)
    
    app.add_url_rule('/', endpoint='index')

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
        
    print("Aplicação criada e configurada com sucesso!")
    
    return app