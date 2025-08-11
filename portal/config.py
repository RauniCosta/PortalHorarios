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
        "Ensino Médio": {
            "Manhã": {"07:10 - 08:00": "1º", "08:00 - 08:50": "2º", "08:50 - 09:40": "3º", "09:40 - 10:00": "INTERVALO", "10:00 - 10:50": "4º", "10:50 - 11:40": "5º", "11:40 - 12:30": "6º"},
            "Tarde": {"12:40 - 13:30": "1º Tarde", "13:30 - 14:20": "2º Tarde", "14:20 - 15:10": "3º Tarde", "15:10 - 15:30": "INTERVALO", "15:30 - 16:20": "4º Tarde", "16:20 - 17:10": "5º Tarde", "17:10 - 18:00": "6º Tarde"},
            "Noturno": {"18:20 - 19:10": "3º Noturno", "19:10 - 20:00": "4º Noturno", "20:00 - 20:50": "5º Noturno", "20:50 - 21:05": "INTERVALO", "21:05 - 21:55": "6º Noturno", "21:55 - 22:45": "7º Noturno"},
            "Integral": {"07:10 - 08:00": "1º", "08:00 - 08:50": "2º", "08:50 - 09:40": "3º", "09:40 - 10:00": "INTERVALO", "10:00 - 10:50": "4º", "10:50 - 11:40": "5º", "11:40 - 12:40": "Almoço", "12:40 - 13:30": "1º Tarde", "13:30 - 14:20": "2º Tarde", "14:20 - 15:10": "3º Tarde", "15:10 - 15:30": "INTERVALO"}
        },
        "Curso Técnico": {
            "Manhã": {"07:10 - 08:00": "1º", "08:00 - 08:50": "2º", "08:50 - 09:40": "3º", "09:40 - 10:00": "INTERVALO", "10:00 - 10:50": "4º", "10:50 - 11:40": "5º", "11:40 - 12:30": "6º"},
            "Tarde": {"12:40 - 13:30": "1º Tarde", "13:30 - 14:20": "2º Tarde", "14:20 - 15:10": "3º Tarde", "15:10 - 15:30": "INTERVALO", "15:30 - 16:20": "4º Tarde", "16:20 - 17:10": "5º Tarde", "17:10 - 18:00": "6º Tarde"},
            "Noturno": {"19:00 - 20:55": "1º Bloco", "20:55 - 21:05": "INTERVALO", "21:05 - 23:00": "2º Bloco"}
        }
    }
    PERIODO_MAP = {"1": "Manhã", "2": "Tarde", "3": "Noturno", "4": "Integral"}
    CATEGORIAS_CURSO = ["Ensino Médio", "Curso Técnico"]