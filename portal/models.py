from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Professor(db.Model):
    __tablename__ = 'professores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), unique=True, nullable=False)
    apelido = db.Column(db.String(50), unique=True, nullable=False, index=True)
    disponibilidade = db.Column(db.JSON)
    # RELACIONAMENTO: Se um professor for deletado, todas as suas aulas na matriz também serão.
    quadro_aulas = db.relationship('QuadroDeAulas', back_populates='professor', cascade="all, delete-orphan")

class Disciplina(db.Model):
    __tablename__ = 'disciplinas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), unique=True, nullable=False)
    sigla = db.Column(db.String(20), unique=True, nullable=False, index=True)
    # RELACIONAMENTO: Se uma disciplina for deletada, todas as suas aulas na matriz também serão.
    quadro_aulas = db.relationship('QuadroDeAulas', back_populates='disciplina', cascade="all, delete-orphan")

class Turma(db.Model):
    __tablename__ = 'turmas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), unique=True, nullable=False)
    apelido = db.Column(db.String(20), unique=True, nullable=False, index=True)
    categoria = db.Column(db.String(50), nullable=False)
    periodo = db.Column(db.String(20), nullable=False)
    # RELACIONAMENTO: Se uma turma for deletada, todas as suas aulas na matriz também serão.
    quadro_aulas = db.relationship('QuadroDeAulas', back_populates='turma', cascade="all, delete-orphan")

class Sala(db.Model):
    __tablename__ = 'salas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False, index=True)
    # RELACIONAMENTO: Define a relação com as aulas alocadas.
    horarios_alocados = db.relationship('HorarioAlocado', back_populates='sala')
    reposicoes_alocadas = db.relationship('ReposicaoAlocada', back_populates='sala')

class QuadroDeAulas(db.Model):
    __tablename__ = 'quadro_aulas'
    id = db.Column(db.Integer, primary_key=True)
    turma_id = db.Column(db.Integer, db.ForeignKey('turmas.id'), nullable=False)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplinas.id'), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey('professores.id'), nullable=False)
    aulas_semanais = db.Column(db.Integer, nullable=False)
    origem = db.Column(db.String(100))
    
    # RELACIONAMENTOS
    turma = db.relationship('Turma', back_populates='quadro_aulas')
    disciplina = db.relationship('Disciplina', back_populates='quadro_aulas')
    professor = db.relationship('Professor', back_populates='quadro_aulas')
    
    horarios_alocados = db.relationship('HorarioAlocado', back_populates='quadro_aula', cascade="all, delete-orphan")
    reposicoes_alocadas = db.relationship('ReposicaoAlocada', back_populates='quadro_aula', cascade="all, delete-orphan")

class HorarioAlocado(db.Model):
    __tablename__ = 'horarios_alocados'
    id = db.Column(db.Integer, primary_key=True)
    # REFINAMENTO: Garante que uma alocação não pode existir sem estar ligada a uma aula da matriz e a uma sala.
    quadro_aula_id = db.Column(db.Integer, db.ForeignKey('quadro_aulas.id'), nullable=False)
    sala_id = db.Column(db.Integer, db.ForeignKey('salas.id'), nullable=False)
    dia_semana = db.Column(db.String(20), nullable=False)
    horario = db.Column(db.String(50), nullable=False)

    quadro_aula = db.relationship('QuadroDeAulas', back_populates='horarios_alocados')
    sala = db.relationship('Sala', back_populates='horarios_alocados')

class SabadoLetivo(db.Model):
    __tablename__ = 'sabados_letivos'
    id = db.Column(db.String(10), primary_key=True) # Data no formato YYYY-MM-DD
    descricao = db.Column(db.String(200), nullable=False)
    grade_horarios = db.Column(db.JSON)
    
    reposicoes_alocadas = db.relationship('ReposicaoAlocada', back_populates='sabado_letivo', cascade="all, delete-orphan")

class ReposicaoAlocada(db.Model):
    __tablename__ = 'reposicoes_alocadas'
    id = db.Column(db.Integer, primary_key=True)
    sabado_id = db.Column(db.String(10), db.ForeignKey('sabados_letivos.id'), nullable=False)
    quadro_aula_id = db.Column(db.Integer, db.ForeignKey('quadro_aulas.id'), nullable=False)
    sala_id = db.Column(db.Integer, db.ForeignKey('salas.id'), nullable=False)
    horario = db.Column(db.String(50), nullable=False)
    
    sabado_letivo = db.relationship('SabadoLetivo', back_populates='reposicoes_alocadas')
    quadro_aula = db.relationship('QuadroDeAulas', back_populates='reposicoes_alocadas')
    sala = db.relationship('Sala', back_populates='reposicoes_alocadas')
# Adicione estas duas novas classes no início do arquivo, logo após User.

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False) # Ex: "Ensino Médio"

    # Relacionamento: Uma Categoria pode ter várias Grades de Horário
    grades_horario = db.relationship('GradeHorario', back_populates='categoria', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Categoria {self.nome}>'

class Periodo(db.Model):
    __tablename__ = 'periodos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False) # Ex: "Manhã"

    # Relacionamento: Um Período pode ter várias Grades de Horário
    grades_horario = db.relationship('GradeHorario', back_populates='periodo', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Periodo {self.nome}>'

# Agora, substitua a classe GradeHorario existente por esta versão atualizada.

class GradeHorario(db.Model):
    __tablename__ = 'grade_horarios'
    id = db.Column(db.Integer, primary_key=True)
    
    # Chaves estrangeiras que conectam à Categoria e ao Período
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    periodo_id = db.Column(db.Integer, db.ForeignKey('periodos.id'), nullable=False)
    
    # Dados do horário
    apelido = db.Column(db.String(50), nullable=False)   # Ex: "1º Horário"
    inicio = db.Column(db.String(5), nullable=False)     # Ex: "07:10"
    fim = db.Column(db.String(5), nullable=False)        # Ex: "08:00"

    # Relacionamentos para buscar os nomes facilmente
    categoria = db.relationship('Categoria', back_populates='grades_horario')
    periodo = db.relationship('Periodo', back_populates='grades_horario')

    # Garante que não teremos duas "1ª Aulas" para a mesma categoria/período
    __table_args__ = (db.UniqueConstraint('categoria_id', 'periodo_id', 'apelido', name='_categoria_periodo_apelido_uc'),)

    def __repr__(self):
        return f'<Grade {self.categoria.nome} - {self.periodo.nome} - {self.apelido}>'
    
    