# portal/config.py

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'uma-chave-secreta-muito-segura')
    
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'Etec.ind25*') # <-- ATENÇÃO AQUI!
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'portalhorarios_db')
    
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GRADE_HORARIOS_FIXOS_POR_CATEGORIA = {
        # ... (suas constantes de horários aqui) ...
    }
    PERIODO_MAP = {"1": "Manhã", "2": "Tarde", "3": "Noturno", "4": "Integral"}
    CATEGORIAS_CURSO = ["Ensino Médio", "Curso Técnico"]