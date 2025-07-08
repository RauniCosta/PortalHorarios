# portal/routes.py
from sqlalchemy import or_

import json 
import csv
import io
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
)
from werkzeug.security import generate_password_hash
from .auth import login_required, roles_required # Importa os decorators do nosso novo arquivo de auth
from .models import db, Professor, Disciplina, Turma, Sala, User, QuadroDeAulas
#from .scheduler_engine import resolver_horario # Importa o motor de agendamento


# Cria um novo Blueprint chamado 'main' para as rotas principais.
bp = Blueprint('main', __name__)


# --- ROTA PÚBLICA ---
@bp.route('/')
def index():
    """ Rota para a página inicial pública. """
    # Busca a nossa constante de horários diretamente da configuração da aplicação.
    grade_horarios = current_app.config['GRADE_HORARIOS_FIXOS_POR_CATEGORIA']

    # Passa a variável para o template com o nome exato que ele espera.
    return render_template(
        'index.html', 
        grade_horarios_fixos_por_categoria=grade_horarios
    )


@bp.route('/admin/importar', methods=['POST'])
@login_required
@roles_required('Full')
def importar_quadro_aulas_csv():
    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        flash('Formato de arquivo inválido. Por favor, envie um arquivo .csv', 'danger')
        return redirect(url_for('main.dashboard'))

    professores_cache = {}
    disciplinas_cache = {}
    turmas_cache = {}
    summary = {"processed": 0, "skipped": 0}
    skipped_rows_details = []

    try:
        # Limpa apenas a matriz antiga para uma nova importação
        db.session.query(QuadroDeAulas).delete()
        
        stream = io.StringIO(file.stream.read().decode("UTF-8-sig"), newline=None)
        reader = csv.DictReader(stream, delimiter=';')

        for i, row in enumerate(reader, start=2):
            # Usamos um 'try...except' por linha para capturar erros de dados
            # e pular a linha problemática, sem invalidar a transação inteira.
            try:
                # Extração e validação dos dados da linha
                turma_apelido = row.get("Turma Apelido", "").strip()
                disciplina_sigla = row.get("Sigla", "").strip()
                prof_apelido = row.get("Professor Apelido", "").strip()
                
                # ... (resto da lógica de extração e validação) ...
                disciplina_nome = row.get("Componente", "").strip()
                prof_nome = row.get("Professor Ministrando", "").strip()

                if not all([turma_apelido, disciplina_sigla, disciplina_nome, prof_apelido, prof_nome]):
                    raise ValueError("Colunas essenciais (Turma, Disciplina, Professor) estão vazias.")

                # Lógica "Encontre ou Crie" robusta
                if prof_apelido not in professores_cache:
                    professor = Professor.query.filter(or_(Professor.id == prof_apelido, Professor.nome == prof_nome)).first()
                    if not professor:
                        professor = Professor(id=prof_apelido, nome=prof_nome)
                        db.session.add(professor)
                    professores_cache[prof_apelido] = professor
                
                if disciplina_sigla not in disciplinas_cache:
                    disciplina = Disciplina.query.filter(or_(Disciplina.id == disciplina_sigla, Disciplina.nome == disciplina_nome)).first()
                    if not disciplina:
                        disciplina = Disciplina(id=disciplina_sigla, nome=disciplina_nome)
                        db.session.add(disciplina)
                    disciplinas_cache[disciplina_sigla] = disciplina
                
                if turma_apelido not in turmas_cache:
                    turma = Turma.query.get(turma_apelido)
                    if not turma:
                        turma = Turma(id=turma_apelido, apelido=turma_apelido, nome=row.get("Turma", "").strip())
                        db.session.add(turma)
                    turmas_cache[turma_apelido] = turma

                # Cria a entrada na Matriz Curricular
                qtde_aulas = int(float(row.get("Qtde Aulas", "0").strip().replace(',', '.')))
                nova_entrada = QuadroDeAulas(
                    turma_id=turmas_cache[turma_apelido].id,
                    disciplina_id=disciplinas_cache[disciplina_sigla].id,
                    professor_id=professores_cache[prof_apelido].id,
                    aulas_semanais=qtde_aulas,
                    origem=row.get("Origem", "").strip()
                )
                db.session.add(nova_entrada)
                
                # Para forçar a verificação de FKs a cada linha, usamos flush.
                # Se algo estiver errado (como um ID de turma que não foi criado),
                # o erro acontecerá aqui e será capturado pelo nosso except.
                db.session.flush()

                summary["processed"] += 1

            except Exception as row_error:
                # CORREÇÃO: REMOVEMOS o `db.session.rollback()` daqui!
                # Apenas registramos a linha que falhou e continuamos.
                summary["skipped"] += 1
                skipped_rows_details.append({"line_number": i, "data": row, "reason": str(row_error)})
        
        # Se o loop terminar, comitamos a transação inteira com todas as linhas válidas.
        db.session.commit()
        flash(f'Importação concluída! Processados: {summary["processed"]}, Ignorados: {summary["skipped"]}.', 'success')

    except Exception as e:
        # Este rollback só acontece se um erro muito grave e inesperado ocorrer.
        db.session.rollback()
        flash(f'Ocorreu um erro crítico durante a importação. Nenhuma alteração foi salva. Erro: {e}', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_template('admin_import_report.html', summary=summary, skipped_rows=skipped_rows_details)



# --- ROTAS DO PAINEL DE ADMINISTRAÇÃO ---

@bp.route('/admin/dashboard')
@login_required
def dashboard():
    """ Página principal do painel administrativo. """
    return render_template('admin_dashboard.html')


# --- ROTAS DE GERENCIAMENTO DE USUÁRIOS ---

@bp.route('/admin/users')
@login_required
@roles_required('Full')
def users_list():
    """ Lista todos os usuários do sistema. """
    # Lógica de DB: Pega todos os usuários, ordenados pelo nome.
    users = User.query.order_by(User.username).all()
    return render_template('admin_users_list.html', users=users)

@bp.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@roles_required('Full')
def user_add():
    """ Adiciona um novo usuário. """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        # Lógica de DB: Verifica se o usuário já existe.
        if User.query.filter_by(username=username).first():
            flash('Nome de usuário já existe.', 'danger')
        else:
            # Lógica de DB: Cria um novo usuário e o salva no banco.
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password_hash=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash('Usuário adicionado com sucesso!', 'success')
            return redirect(url_for('main.users_list'))
            
    return render_template('admin_user_form.html', action='add')

@bp.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full')
def user_edit(user_id):
    """
    Rota para editar um usuário existente.
    <int:user_id> na URL captura o ID do usuário e o passa como argumento para a função.
    """
    # Usar get_or_404 é uma melhor prática do Flask. Ele busca o usuário pelo ID
    # e, se não encontrar, automaticamente retorna uma página de erro 404 (Not Found).
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        # Pega os dados do formulário enviado
        username = request.form['username']
        role = request.form['role']
        password = request.form['password']

        # Verifica se o novo nome de usuário já está em uso por OUTRO usuário.
        user_existente = User.query.filter(User.username == username, User.id != user_id).first()
        if user_existente:
            flash('Este nome de usuário já está em uso por outra conta.', 'danger')
            return redirect(url_for('main.user_edit', user_id=user_id))

        # Atualiza os dados do objeto 'user' que buscamos do banco
        user.username = username
        user.role = role

        # Apenas atualiza a senha se um novo valor foi digitado.
        # Se o campo senha vier vazio, a senha atual é mantida.
        if password:
            user.password_hash = generate_password_hash(password)

        # Efetiva as alterações no banco de dados.
        db.session.commit()
        
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('main.users_list'))

    # Se o método for GET, simplesmente exibe o formulário pré-preenchido
    # com os dados atuais do usuário.
    return render_template('admin_user_form.html', action='edit', user=user)


@bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@roles_required('Full')
def user_delete(user_id):
    """
    Rota para deletar um usuário.
    É crucial que esta rota aceite apenas o método POST para evitar exclusões acidentais
    através de links (que são requisições GET).
    """
    user = User.query.get_or_404(user_id)
    
    # Uma verificação de segurança importante: não permitir que um usuário delete a si mesmo.
    if user.id == session.get('user_id'):
        flash('Você não pode deletar sua própria conta de usuário.', 'danger')
        return redirect(url_for('main.users_list'))

    # Lógica de exclusão: remove o usuário da sessão do banco de dados
    db.session.delete(user)
    # Efetiva a exclusão no banco de dados.
    db.session.commit()
    
    flash('Usuário deletado com sucesso!', 'success')
    return redirect(url_for('main.users_list'))


# --- ROTAS DE GERENCIAMENTO DE PROFESSORES ---

@bp.route('/admin/professores')
@login_required
@roles_required('Full', 'Supervisor')
def professores_list():
    """
    Rota para listar todos os professores cadastrados. 
    O nome desta função, 'professores_list', gera o endpoint 'main.professores_list'.
    """
    professores = Professor.query.order_by(Professor.nome).all()
    return render_template('admin_view_data.html', 
                           data=professores, 
                           title="Professores", 
                           data_type="professores")

@bp.route('/admin/professores/add', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def professor_add():
    """ Rota para adicionar um novo professor. """
    if request.method == 'POST':
        prof_id = request.form['id']
        nome = request.form['nome']

        # Validação: Verifica se o ID (chave primária) já existe no banco
        if Professor.query.get(prof_id):
            flash(f'O ID "{prof_id}" já está em uso. Por favor, escolha outro.', 'danger')
        else:
            # Cria a nova instância do modelo e salva no banco
            novo_professor = Professor(id=prof_id, nome=nome, disponibilidade={}) # Começa com disponibilidade vazia
            db.session.add(novo_professor)
            db.session.commit()
            flash('Professor adicionado com sucesso!', 'success')
            return redirect(url_for('main.professores_list'))
    
    # Se for GET, apenas renderiza o formulário de adição
    return render_template('admin_professor_form.html', action='add', title="Adicionar Professor")


@bp.route('/admin/professores/edit/<string:prof_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def professor_edit(prof_id):
    """ Rota para editar os dados básicos de um professor (como o nome). """
    # Busca o professor pelo ID ou retorna erro 404 se não encontrar
    professor = Professor.query.get_or_404(prof_id)

    if request.method == 'POST':
        # O ID não é editável, apenas o nome
        professor.nome = request.form['nome']
        db.session.commit()
        flash('Nome do professor atualizado com sucesso!', 'success')
        return redirect(url_for('main.professores_list'))

    # Se for GET, renderiza o formulário com os dados do professor
    return render_template('admin_professor_form.html', action='edit', title="Editar Professor", professor=professor)


@bp.route('/admin/professores/disponibilidade/<string:prof_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def professor_disponibilidade(prof_id):
    """ Rota para editar a disponibilidade de um professor. """
    professor = Professor.query.get_or_404(prof_id)
    
    # As constantes de horários vêm do arquivo de configuração
    grade_horarios = current_app.config['GRADE_HORARIOS_FIXOS_POR_CATEGORIA']

    if request.method == 'POST':
        nova_disponibilidade = {}
        # A lógica para extrair os dados do formulário de disponibilidade
        # é complexa e específica. Vamos assumir que o formulário envia
        # os dados de forma que possam ser processados aqui.
        # Exemplo: 'disponibilidade-Segunda-1' pode ser um campo do form.
        for categoria, turnos in grade_horarios.items():
            nova_disponibilidade[categoria] = {}
            for turno, horarios in turnos.items():
                nova_disponibilidade[categoria][turno] = {}
                for horario, desc in horarios.items():
                    if desc != "INTERVALO" and desc != "Almoço":
                        key = f"disponibilidade-{categoria}-{turno}-{horario}"
                        nova_disponibilidade[categoria][turno][horario] = 'disponivel' if key in request.form else 'indisponivel'
        
        professor.disponibilidade = nova_disponibilidade
        db.session.commit()
        flash(f'Disponibilidade do professor {professor.nome} atualizada.', 'success')
        return redirect(url_for('main.professores_list'))

    # Para o método GET, usamos o template que já existia
    return render_template('admin_professor_disponibilidade.html', professor=professor, grade_horarios=grade_horarios)


@bp.route('/admin/professores/delete/<string:prof_id>', methods=['POST'])
@login_required
@roles_required('Full')
def professor_delete(prof_id):
    """ Rota para deletar um professor. Requer método POST por segurança. """
    professor = Professor.query.get_or_404(prof_id)

    # Ponto de Atenção (Lógica de Negócio):
    # Antes de deletar, o ideal seria verificar se este professor não está
    # alocado em nenhum quadro de aulas. Se estiver, a exclusão deveria ser
    # bloqueada para manter a integridade dos dados dos horários.
    # Esta verificação pode ser adicionada no futuro.

    db.session.delete(professor)
    db.session.commit()
    flash('Professor deletado com sucesso!', 'success')
    return redirect(url_for('main.professores_list'))

# --- ROTAS DE GERENCIAMENTO DE SALAS ---

@bp.route('/admin/salas')
@login_required
@roles_required('Full', 'Supervisor')
def salas_list():
    """ Lista todas as salas cadastradas. (Rota Read) """
    salas = Sala.query.order_by(Sala.nome).all()
    return render_template('admin_view_data.html', data=salas, title="Salas", data_type="salas")

@bp.route('/admin/salas/add', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def sala_add():
    """ Rota para adicionar uma nova sala. (Rota Create) """
    if request.method == 'POST':
        sala_id = request.form['id']
        nome = request.form['nome']

        if Sala.query.get(sala_id):
            flash(f'O ID de sala "{sala_id}" já existe.', 'danger')
        else:
            nova_sala = Sala(id=sala_id, nome=nome)
            db.session.add(nova_sala)
            db.session.commit()
            flash('Sala adicionada com sucesso!', 'success')
            return redirect(url_for('main.salas_list'))
    
    return render_template('admin_sala_form.html', action='add', title="Adicionar Sala")


@bp.route('/admin/salas/edit/<string:sala_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def sala_edit(sala_id):
    """ Rota para editar uma sala existente. (Rota Update) """
    sala = Sala.query.get_or_404(sala_id)

    if request.method == 'POST':
        sala.nome = request.form['nome']
        db.session.commit()
        flash('Sala atualizada com sucesso!', 'success')
        return redirect(url_for('main.salas_list'))

    return render_template('admin_sala_form.html', action='edit', title="Editar Sala", sala=sala)


@bp.route('/admin/salas/delete/<string:sala_id>', methods=['POST'])
@login_required
@roles_required('Full')
def sala_delete(sala_id):
    """ Rota para deletar uma sala. (Rota Delete) """
    sala = Sala.query.get_or_404(sala_id)

    # Lógica de Negócio: Antes de deletar, o ideal é verificar se a sala
    # está sendo usada em algum horário para não quebrar a alocação.

    db.session.delete(sala)
    db.session.commit()
    flash('Sala deletada com sucesso!', 'success')
    return redirect(url_for('main.salas_list'))


# --- ROTAS DE GERENCIAMENTO DE DISCIPLINAS ---

@bp.route('/admin/disciplinas')
@login_required
@roles_required('Full', 'Supervisor')
def disciplinas_list():
    """ Lista todas as disciplinas cadastradas. (Rota Read) """
    disciplinas = Disciplina.query.order_by(Disciplina.nome).all()
    return render_template('admin_view_data.html', data=disciplinas, title="Disciplinas", data_type="disciplinas")

@bp.route('/admin/disciplinas/add', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def disciplina_add():
    """ Rota para adicionar uma nova disciplina. (Rota Create) """
    if request.method == 'POST':
        disciplina_id = request.form['id']
        nome = request.form['nome']

        if Disciplina.query.get(disciplina_id):
            flash(f'O ID de disciplina "{disciplina_id}" já existe.', 'danger')
        else:
            nova_disciplina = Disciplina(id=disciplina_id, nome=nome)
            db.session.add(nova_disciplina)
            db.session.commit()
            flash('Disciplina adicionada com sucesso!', 'success')
            return redirect(url_for('main.disciplinas_list'))
    
    return render_template('admin_disciplina_form.html', action='add', title="Adicionar Disciplina")


@bp.route('/admin/disciplinas/edit/<string:disciplina_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def disciplina_edit(disciplina_id):
    """ Rota para editar uma disciplina existente. (Rota Update) """
    disciplina = Disciplina.query.get_or_404(disciplina_id)

    if request.method == 'POST':
        disciplina.nome = request.form['nome']
        db.session.commit()
        flash('Disciplina atualizada com sucesso!', 'success')
        return redirect(url_for('main.disciplinas_list'))

    return render_template('admin_disciplina_form.html', action='edit', title="Editar Disciplina", disciplina=disciplina)


@bp.route('/admin/disciplinas/delete/<string:disciplina_id>', methods=['POST'])
@login_required
@roles_required('Full')
def disciplina_delete(disciplina_id):
    """ Rota para deletar uma disciplina. (Rota Delete) """
    disciplina = Disciplina.query.get_or_404(disciplina_id)

    # Lógica de Negócio: Antes de deletar, verificar se a disciplina não faz
    # parte de um quadro de aulas existente para manter a integridade.

    db.session.delete(disciplina)
    db.session.commit()
    flash('Disciplina deletada com sucesso!', 'success')
    return redirect(url_for('main.disciplinas_list'))

# --- ROTAS DE GERENCIAMENTO DE TURMAS ---

@bp.route('/admin/turmas')
@login_required
@roles_required('Full', 'Supervisor')
def turmas_list():
    """ Lista todas as turmas cadastradas. (Rota Read) """
    turmas = Turma.query.order_by(Turma.nome).all()
    # Reutilizamos o template genérico para exibir os dados
    return render_template('admin_view_data.html', data=turmas, title="Turmas", data_type="turmas")

@bp.route('/admin/turmas/add', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def turma_add():
    """ Rota para adicionar uma nova turma. (Rota Create) """
    if request.method == 'POST':
        turma_id = request.form['id']
        nome = request.form['nome']

        # Validação: Garante que o ID da turma ainda não foi cadastrado
        if Turma.query.get(turma_id):
            flash(f'O ID de turma "{turma_id}" já existe.', 'danger')
        else:
            nova_turma = Turma(id=turma_id, nome=nome)
            db.session.add(nova_turma)
            db.session.commit()
            flash('Turma adicionada com sucesso!', 'success')
            return redirect(url_for('main.turmas_list'))
    
    # Para requisições GET, apenas mostra o formulário de adição.
    return render_template('admin_turma_form.html', action='add', title="Adicionar Turma")


@bp.route('/admin/turmas/edit/<string:turma_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def turma_edit(turma_id):
    """ Rota para editar uma turma existente. (Rota Update) """
    # Busca a turma pelo ID ou retorna um erro 404 (Not Found)
    turma = Turma.query.get_or_404(turma_id)

    if request.method == 'POST':
        # Atualiza o nome da turma com o valor vindo do formulário
        turma.nome = request.form['nome']
        db.session.commit()
        flash('Turma atualizada com sucesso!', 'success')
        return redirect(url_for('main.turmas_list'))

    # Para requisições GET, mostra o formulário preenchido com os dados da turma
    return render_template('admin_turma_form.html', action='edit', title="Editar Turma", turma=turma)


@bp.route('/admin/turmas/delete/<string:turma_id>', methods=['POST'])
@login_required
@roles_required('Full')
def turma_delete(turma_id):
    """ Rota para deletar uma turma. (Rota Delete) """
    turma = Turma.query.get_or_404(turma_id)

    # Lógica de Negócio Importante:
    # Antes de deletar uma turma, seria ideal verificar se ela não possui
    # aulas ou professores vinculados em um horário já gerado.
    # Isso previne inconsistências nos dados.

    db.session.delete(turma)
    db.session.commit()
    flash('Turma deletada com sucesso!', 'success')
    return redirect(url_for('main.turmas_list'))


# --- ROTAS DE LÓGICA DE NEGÓCIO (ALOCAÇÃO, ETC.) ---
@bp.route('/admin/alocacao', methods=['GET'])
@login_required
@roles_required('Full', 'Supervisor')
def admin_alocacao():
    """
    Renderiza a página principal de alocação de horários.
    Esta função agora busca os dados cadastrais diretamente do banco de dados.
    """
    # Lógica de Banco de Dados: Busca todos os dados básicos necessários para a interface.
    # O método .order_by() garante que os dados sempre aparecerão em ordem alfabética nos menus.
    professores = Professor.query.order_by(Professor.nome).all()
    turmas = Turma.query.order_by(Turma.nome).all()
    disciplinas = Disciplina.query.order_by(Disciplina.nome).all()
    salas = Sala.query.order_by(Sala.nome).all()
    
    # As constantes de configuração agora são carregadas de forma segura a partir do app.
    grade_horarios = current_app.config['GRADE_HORARIOS_FIXOS_POR_CATEGORIA']
    
    # Ponto de Atenção: O "quadro de aulas" (a demanda de aulas por turma)
    # ainda não tem uma tabela no banco. Abordaremos isso no próximo passo.
    # Por enquanto, podemos passar uma estrutura vazia ou um exemplo.
    quadro_aulas_existente = {} # Futuramente, isso também virá do banco.

    return render_template('admin_alocacao.html',
                           professores=professores,
                           turmas=turmas,
                           disciplinas=disciplinas,
                           salas=salas,
                           grade_horarios=grade_horarios,
                           quadro_aulas=quadro_aulas_existente)
    
@bp.route('/gerar-novo-horario', methods=['POST'])
@login_required
@roles_required('Full', 'Supervisor')
def gerar_novo_horario():
    """
    Endpoint da API que recebe a demanda de aulas, busca os dados no banco,
    executa o motor de agendamento e retorna as soluções encontradas.
    """
    # 1. Recebe a demanda de aulas (quadro de aulas) enviada pelo frontend.
    quadro_aulas_demanda = request.get_json()
    if not quadro_aulas_demanda:
        return jsonify({"error": "Nenhum quadro de aulas fornecido."}), 400

    # 2. Busca os dados cadastrais do banco de dados.
    professores_db = Professor.query.all()
    disciplinas_db = Disciplina.query.all()
    salas_db = Sala.query.all()
    turmas_db = Turma.query.all()

    # 3. Transforma os dados do formato SQLAlchemy para o formato de dicionário
    #    que o motor `scheduler_engine` espera. Esta é uma etapa crucial de "tradução".
    dados_para_motor = {
        'professores': {p.id: {'nome': p.nome, 'disponibilidade': p.disponibilidade or {}} for p in professores_db},
        'disciplinas': {d.id: {'nome': d.nome} for d in disciplinas_db},
        'salas': {s.id: {'nome': s.nome} for s in salas_db},
        'turmas': {t.id: {'nome': t.nome} for t in turmas_db},
        'quadro_aulas': quadro_aulas_demanda # Usa a demanda que veio do frontend
    }

    # 4. Chama o motor com os dados devidamente formatados.
    try:
        solucoes = resolver_horarios(dados_para_motor)
        if not solucoes:
            return jsonify({"error": "Não foi possível encontrar uma solução com as restrições fornecidas."}), 422 # Unprocessable Entity
        
        # O motor já retorna uma lista de soluções em formato JSON serializável.
        return jsonify(solucoes)

    except Exception as e:
        # É uma boa prática capturar exceções do motor e retornar um erro claro.
        current_app.logger.error(f"Erro no motor de agendamento: {e}")
        return jsonify({"error": "Ocorreu um erro interno ao processar o horário."}), 500

@bp.route('/admin/reposicao')
@login_required
def admin_reposicao():
    """
    Rota para a página de gerenciamento de reposições.
    Por enquanto, é um placeholder para a funcionalidade futura.
    """
    # Analisando o template 'admin_reposicao.html', vemos que ele espera
    # uma variável chamada 'sabados_letivos'. Vamos passar uma lista vazia
    # por enquanto para evitar erros no template.
    sabados_letivos = [] 
    
    flash('A funcionalidade de Reposições ainda está em desenvolvimento.', 'info')
    return render_template('admin_reposicao.html', sabados_letivos=sabados_letivos)


## --- ROTAS PARA IMPORTAÇÂO DE PROFESSORES, TURMAS, DISCIPLINAS, SALAS ---
@bp.route('/admin/import/professores', methods=['GET', 'POST'])
@login_required
@roles_required('Full')
def importar_professores_csv():
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('Nenhum arquivo selecionado', 'danger')
            return redirect(request.url)
        
        file = request.files['csv_file']
        
        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'danger')
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            try:
                # Usamos o `stream` para ler o arquivo em memória
                stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
                csv_reader = csv.reader(stream)
                
                # Pular o cabeçalho
                next(csv_reader, None)
                
                novos_professores = []
                for row in csv_reader:
                    # Supondo que o CSV tem as colunas: id, nome
                    prof_id, prof_nome = row
                    
                    # Verifica se o professor já não existe para evitar duplicatas
                    existente = Professor.query.get(prof_id)
                    if not existente:
                        novo_prof = Professor(id=prof_id, nome=prof_nome)
                        novos_professores.append(novo_prof)

                if novos_professores:
                    db.session.add_all(novos_professores)
                    db.session.commit()
                    flash(f'{len(novos_professores)} novos professores importados com sucesso!', 'success')
                else:
                    flash('Nenhum novo professor para importar.', 'info')

            except Exception as e:
                db.session.rollback()
                flash(f'Ocorreu um erro durante a importação: {e}', 'danger')
            
            return redirect(url_for('main.professores_list'))

    return render_template('sua_pagina_de_importacao.html', title="Importar Professores")

# =============================================================================
# ROTAS DE API PARA O DASHBOARD (GERAÇÃO AUTOMÁTICA)
# =============================================================================

@bp.route('/admin/api/validar-dados', methods=['POST'])
@login_required
@roles_required('Full', 'Supervisor')
def validar_dados_api():
    """
    Endpoint da API para validar a consistência dos dados antes da geração.
    TODO: Implementar a lógica de validação real lendo do banco de dados.
    """
    # Por enquanto, retornamos uma resposta de sucesso para não quebrar o frontend.
    return jsonify({"status": "ok", "message": "Validação concluída (placeholder)."}), 200

@bp.route('/admin/api/gerar-horario', methods=['POST'])
@login_required
@roles_required('Full', 'Supervisor')
def gerar_horario_automatico():
    """
    Endpoint da API para iniciar a tarefa de geração de horário em background.
    TODO: Implementar a lógica real com Celery ou outra fila de tarefas.
    """
    # Por enquanto, retornamos um ID de tarefa falso para o frontend continuar.
    return jsonify({"task_id": "tarefa_ficticia_12345"}), 202 # HTTP 202: Accepted

@bp.route('/admin/api/status/<string:task_id>')
@login_required
@roles_required('Full', 'Supervisor')
def verificar_status_geracao(task_id):
    """
    Endpoint da API para verificar o status de uma tarefa de geração.
    TODO: Implementar a consulta real do status da tarefa.
    """
    # Para o teste, retornamos 'completed' diretamente para finalizar o ciclo no frontend.
    return jsonify({"status": "completed", "result": "Horário gerado com sucesso (placeholder)!"})

@bp.route('/admin/sugestoes')
@login_required
@roles_required('Full', 'Supervisor')
def listar_sugestoes():
    """
    Rota para listar as sugestões de horários gerados pelo motor.
    TODO: Implementar a busca das sugestões salvas no banco de dados.
    """
    # O template 'admin_sugestoes_lista.html' espera uma variável 'sugestoes'.
    # Passamos uma lista vazia por enquanto.
    sugestoes = []
    
    flash('A funcionalidade de Sugestões de Horário ainda está em desenvolvimento.', 'info')
    return render_template('admin_sugestoes_lista.html', sugestoes=sugestoes)

