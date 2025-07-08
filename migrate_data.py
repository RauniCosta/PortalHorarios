import json
from portal import create_app
from portal.models import db, Professor, Disciplina, Turma, Sala, User

# Carrega a aplicação Flask para ter o contexto do banco de dados
app = create_app()

def migrate():
    """
    Lê os dados do arquivo JSON e os insere no banco de dados.
    """
    with app.app_context():
        print("Iniciando migração de dados...")

        # Carrega os dados do arquivo JSON
        with open('dados.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Migrando Professores
        if 'professores' in data:
            for prof_id, prof_data in data['professores'].items():
                new_prof = Professor(id=prof_id, nome=prof_data['nome'], disponibilidade=prof_data.get('disponibilidade'))
                db.session.add(new_prof)
            print("Professores migrados com sucesso.")

        # Migrando Disciplinas
        if 'disciplinas' in data:
            for disc_id, disc_data in data['disciplinas'].items():
                new_disc = Disciplina(id=disc_id, nome=disc_data['nome'])
                db.session.add(new_disc)
            print("Disciplinas migradas com sucesso.")

        # Migrando Turmas
        if 'turmas' in data:
            for turma_id, turma_data in data['turmas'].items():
                new_turma = Turma(id=turma_id, nome=turma_data['nome'])
                db.session.add(new_turma)
            print("Turmas migradas com sucesso.")
            
        # Migrando Salas
        if 'salas' in data:
            for sala_id, sala_data in data['salas'].items():
                new_sala = Sala(id=sala_id, nome=sala_data['nome'])
                db.session.add(new_sala)
            print("Salas migradas com sucesso.")
            
        # Migrando Usuários
        if 'users' in data:
            for user_data in data['users']:
                # O hash da senha já está no formato correto
                new_user = User(username=user_data['username'], password_hash=user_data['password_hash'], role=user_data['role'])
                db.session.add(new_user)
            print("Usuários migrados com sucesso.")

        # Efetiva todas as inserções no banco de dados
        try:
            db.session.commit()
            print("\nMigração concluída com sucesso! Os dados estão no PostgreSQL.")
        except Exception as e:
            db.session.rollback()
            print(f"\nOcorreu um erro durante a migração: {e}")

if __name__ == '__main__':
    migrate()