from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Todos os modelos principais com chave primária (id) numérica
class Turma(db.Model):
    __tablename__ = 'turmas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    apelido = db.Column(db.String(50), nullable=False, unique=True)
    periodo = db.Column(db.String(50), nullable=True)
    categoria = db.Column(db.String(50), nullable=True)

class Professor(db.Model):
    __tablename__ = 'professores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)
    apelido = db.Column(db.String(50), nullable=False, unique=True)
    disponibilidade = db.Column(db.JSON, nullable=True)

class Disciplina(db.Model):
    __tablename__ = 'disciplinas'
    id = db.Column(db.Integer, primary_key=True)
    sigla = db.Column(db.String(50), nullable=False, unique=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)

class Sala(db.Model):
    __tablename__ = 'salas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False, unique=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='User')

class QuadroDeAulas(db.Model):
    __tablename__ = 'quadro_aulas'
    id = db.Column(db.Integer, primary_key=True)
    # Chaves estrangeiras numéricas
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professores.id'), nullable=False)
    aulas_semanais = db.Column(db.Integer, nullable=False)
    origem = db.Column(db.String(50), nullable=True)
    turma = db.relationship('Turma')
    disciplina = db.relationship('Disciplina')
    professor = db.relationship('Professor')

class HorarioAlocado(db.Model):
    __tablename__ = 'horarios_alocados'
    id = db.Column(db.Integer, primary_key=True)
    quadro_aula_id = db.Column(db.Integer, db.ForeignKey('quadro_aulas.id'), nullable=False)
    dia_semana = db.Column(db.String(50), nullable=False)
    horario = db.Column(db.String(50), nullable=False)
    
    # ===== A CORREÇÃO PRINCIPAL ESTÁ AQUI =====
    # sala_id agora é Integer para ser compatível com o 'id' da tabela 'salas'
    sala_id = db.Column(db.Integer, db.ForeignKey('salas.id'), nullable=False)

    quadro_aula = db.relationship('QuadroDeAulas', backref=db.backref('alocacoes', lazy='dynamic', cascade="all, delete-orphan"))
    sala = db.relationship('Sala')
    __table_args__ = (db.UniqueConstraint('sala_id', 'dia_semana', 'horario', name='_sala_dia_horario_uc'),)

class SabadoLetivo(db.Model):
    __tablename__ = 'sabados_letivos'
    # A data do sábado será a chave primária, no formato 'AAAA-MM-DD'
    id = db.Column(db.String(10), primary_key=True) 
    descricao = db.Column(db.String(200), nullable=False)
    # Armazena a grade de horários customizada para este sábado como JSON
    grade_horarios = db.Column(db.JSON, nullable=False)

class ReposicaoAlocada(db.Model):
    __tablename__ = 'reposicoes_alocadas'
    id = db.Column(db.Integer, primary_key=True)

    # A qual sábado esta reposição pertence
    sabado_id = db.Column(db.String(10), db.ForeignKey('sabados_letivos.id'), nullable=False)
    # A qual aula da matriz curricular ela se refere
    quadro_aula_id = db.Column(db.Integer, db.ForeignKey('quadro_aulas.id'), nullable=False)

    # Onde e quando ela acontece
    horario = db.Column(db.String(50), nullable=False) # Ex: "08:00-09:00"
    sala_id = db.Column(db.Integer, db.ForeignKey('salas.id'), nullable=False)

    # Relações
    sabado = db.relationship('SabadoLetivo', backref=db.backref('alocacoes', lazy='dynamic', cascade="all, delete-orphan"))
    quadro_aula = db.relationship('QuadroDeAulas')
    sala = db.relationship('Sala')