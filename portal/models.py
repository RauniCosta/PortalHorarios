# portal/models.py

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Todas as chaves primárias (id) são definidas como String,
# pois usamos apelidos como "1A-EM", "MAT", "AB", etc.
class Turma(db.Model):
    __tablename__ = 'turmas'
    id = db.Column(db.String(50), primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    # Adicionei os outros campos que usamos na importação
    apelido = db.Column(db.String(50), nullable=False, unique=True)
    periodo = db.Column(db.String(50), nullable=True)
    categoria = db.Column(db.String(50), nullable=True)

class Professor(db.Model):
    __tablename__ = 'professores'
    id = db.Column(db.String(50), primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    disponibilidade = db.Column(db.JSON, nullable=True)

class Disciplina(db.Model):
    __tablename__ = 'disciplinas'
    id = db.Column(db.String(50), primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)

class Sala(db.Model):
    __tablename__ = 'salas'
    id = db.Column(db.String(50), primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True) # User ID pode ser um número
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='User')

class QuadroDeAulas(db.Model):
    __tablename__ = 'quadro_aulas'
    id = db.Column(db.Integer, primary_key=True) # ID numérico para a entrada da matriz

    # CORREÇÃO CRÍTICA: Todas as chaves estrangeiras devem ser String para
    # corresponder às chaves primárias das outras tabelas.
    turma_id = db.Column(db.String(50), db.ForeignKey('turmas.id'), nullable=False)
    disciplina_id = db.Column(db.String(50), db.ForeignKey('disciplinas.id'), nullable=False)
    professor_id = db.Column(db.String(50), db.ForeignKey('professores.id'), nullable=False)
    
    aulas_semanais = db.Column(db.Integer, nullable=False)
    origem = db.Column(db.String(50), nullable=True)

    turma = db.relationship('Turma')
    disciplina = db.relationship('Disciplina')
    professor = db.relationship('Professor')

    __table_args__ = (db.UniqueConstraint('turma_id', 'disciplina_id', 'professor_id', 'origem', name='_turma_disciplina_professor_uc'),)
    
    