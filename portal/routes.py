# portal/routes.py
from sqlalchemy import or_
from sqlalchemy import func


import json 
import csv
import io
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
)
from werkzeug.security import generate_password_hash
from .auth import login_required, roles_required # Importa os decorators do nosso novo arquivo de auth
from .models import db, Professor, Disciplina, Turma, Sala, User, QuadroDeAulas, HorarioAlocado, SabadoLetivo, ReposicaoAlocada

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
        # Para uma importação limpa, deletamos os dados que serão recalculados
        db.session.query(HorarioAlocado).delete()
        db.session.query(QuadroDeAulas).delete()
        db.session.query(Professor).delete()
        db.session.query(Disciplina).delete()
        db.session.query(Turma).delete()

        stream = io.StringIO(file.stream.read().decode("UTF-8-sig"), newline=None)
        reader = csv.DictReader(stream, delimiter=';')

        for i, row in enumerate(reader, start=2):
            try:
                # --- Extração e Limpeza dos Dados ---
                prof_nome = row.get("Professor Ministrando", "").strip()
                prof_apelido = row.get("Professor Apelido", "").strip() or prof_nome.split(' ')[0]
                if prof_apelido not in professores_cache:
                    professor = Professor.query.filter(or_(Professor.apelido == prof_apelido, Professor.nome == prof_nome)).first()
                    if not professor:
                        professor = Professor(apelido=prof_apelido, nome=prof_nome)
                        db.session.add(professor)
                        db.session.flush()
                    professores_cache[prof_apelido] = professor

                disciplina_nome = row.get("Componente", "").strip()
                disciplina_sigla = row.get("Sigla", "").strip() or disciplina_nome[:3].upper()
                if disciplina_sigla not in disciplinas_cache:
                    disciplina = Disciplina.query.filter(or_(Disciplina.sigla == disciplina_sigla, Disciplina.nome == disciplina_nome)).first()
                    if not disciplina:
                        disciplina = Disciplina(sigla=disciplina_sigla, nome=disciplina_nome)
                        db.session.add(disciplina)
                        db.session.flush()
                    disciplinas_cache[disciplina_sigla] = disciplina

                # --- Lógica de Turma CORRIGIDA ---
                turma_apelido = row.get("Turma Apelido", "").strip()
                if turma_apelido not in turmas_cache:
                    turma = Turma.query.filter_by(apelido=turma_apelido).first()
                    if not turma:
                        # CORREÇÃO: Agora lemos e salvamos Categoria e Período
                        turma = Turma(
                            apelido=turma_apelido,
                            nome=row.get("Turma", "").strip(),
                            periodo=row.get("Período", "").strip(),
                            categoria=row.get("Categoria", "").strip()
                        )
                        db.session.add(turma)
                        db.session.flush()
                    turmas_cache[turma_apelido] = turma
                
                # --- Cria a entrada na Matriz Curricular ---
                qtde_aulas = int(float(row.get("Qtde Aulas", "0").strip().replace(',', '.')))
                nova_entrada = QuadroDeAulas(
                    turma_id=turmas_cache[turma_apelido].id,
                    disciplina_id=disciplinas_cache[disciplina_sigla].id,
                    professor_id=professores_cache[prof_apelido].id,
                    aulas_semanais=qtde_aulas,
                    origem=row.get("Origem", "").strip()
                )
                db.session.add(nova_entrada)
                summary["processed"] += 1

                if not all([turma_apelido, disciplina_sigla, prof_apelido]):
                    raise ValueError("Colunas essenciais (Turma Apelido, Sigla, Professor Apelido) estão vazias.")
            
            except Exception as row_error:
                summary["skipped"] += 1
                skipped_rows_details.append({"line_number": i, "data": row, "reason": str(row_error)})

        db.session.commit()
        flash(f'Importação concluída! Processados: {summary["processed"]}, Ignorados: {summary["skipped"]}.', 'success')

    except Exception as e:
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
            
    return render_template('admin_user_form.html', action='add', title="Adicionar Usuário", user=None)


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
        if password:
            user.password_hash = generate_password_hash(password)
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('main.users_list'))

    # CORREÇÃO: Garantimos que a variável se chama 'user' ao passar para o template
    return render_template('admin_user_form.html', action='edit', title="Editar Usuário", user=user)


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
    if request.method == 'POST':
        apelido = request.form.get('apelido')
        nome = request.form.get('nome')
        if Professor.query.filter(or_(Professor.apelido==apelido, Professor.nome==nome)).first():
            flash(f'Um professor com este apelido ou nome já existe.', 'danger')
        else:
            novo_professor = Professor(apelido=apelido, nome=nome, disponibilidade={})
            db.session.add(novo_professor)
            db.session.commit()
            flash('Professor adicionado com sucesso!', 'success')
            return redirect(url_for('main.professores_list'))
    return render_template('admin_professor_form.html', action='add', title="Adicionar Professor", professor=None)

@bp.route('/admin/professores/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def professor_edit(item_id):
    """ Rota para editar os dados básicos de um professor. """
    professor = Professor.query.get_or_404(item_id)
    if request.method == 'POST':
        professor.nome = request.form['nome']
        professor.apelido = request.form['apelido']
        db.session.commit()
        flash('Nome do professor atualizado com sucesso!', 'success')
        return redirect(url_for('main.professores_list'))
    return render_template('admin_professor_form.html', action='edit', title="Editar Professor", professor=professor)


@bp.route('/admin/professores/disponibilidade/<string:item_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def professor_disponibilidade(item_id):
    """ Rota para editar a disponibilidade de um professor. """
    professor = Professor.query.get_or_404(item_id)
    grade_config = current_app.config['GRADE_HORARIOS_FIXOS_POR_CATEGORIA']
    if request.method == 'POST':
        nova_disponibilidade = {}
        dias_da_semana = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira", "sexta-feira"]
        for categoria in grade_config:
            for periodo, horarios in grade_config[categoria].items():
                for horario in horarios:
                    for dia in dias_da_semana:
                        # Lógica para processar o form de disponibilidade
                        pass # Implementar a lógica de salvar a disponibilidade
        
        # professor.disponibilidade = nova_disponibilidade
        # db.session.commit()
        flash(f'Disponibilidade do professor {professor.nome} atualizada.', 'success')
        return redirect(url_for('main.professores_list'))
    return render_template('admin_professor_disponibilidade.html', professor=professor, grade_horarios=grade_config)


@bp.route('/admin/professores/delete/<int:item_id>', methods=['POST'])
@login_required
@roles_required('Full')
def professor_delete(item_id):
    """ Rota para deletar um professor. """
    professor = Professor.query.get_or_404(item_id)
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
    if request.method == 'POST':
        nome = request.form.get('nome')
        # Verifica se já existe uma sala com este nome
        if Sala.query.filter_by(nome=nome).first():
            flash(f'Uma sala com o nome "{nome}" já existe.', 'danger')
        else:
            nova_sala = Sala(nome=nome) # Cria o objeto apenas com o nome
            db.session.add(nova_sala)
            db.session.commit()
            flash('Sala adicionada com sucesso!', 'success')
            return redirect(url_for('main.salas_list'))
    return render_template('admin_sala_form.html', action='add', title="Adicionar Sala", sala=None)

@bp.route('/admin/salas/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def sala_edit(item_id):
    """ Rota para editar uma sala existente. (Rota Update) """
    sala = Sala.query.get_or_404(item_id)

    if request.method == 'POST':
        sala.nome = request.form['nome']
        db.session.commit()
        flash('Sala atualizada com sucesso!', 'success')
        return redirect(url_for('main.salas_list'))

    return render_template('admin_sala_form.html', action='edit', title="Editar Sala", sala=sala)


@bp.route('/admin/salas/delete/<int:item_id>', methods=['POST'])
@login_required
@roles_required('Full')
def sala_delete(item_id):
    """ Rota para deletar uma sala. (Rota Delete) """
    sala = Sala.query.get_or_404(item_id)

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
    if request.method == 'POST':
        sigla = request.form.get('sigla')
        nome = request.form.get('nome')
        if Disciplina.query.filter(or_(Disciplina.sigla==sigla, Disciplina.nome==nome)).first():
            flash(f'Uma disciplina com esta sigla ou nome já existe.', 'danger')
        else:
            nova_disciplina = Disciplina(sigla=sigla, nome=nome)
            db.session.add(nova_disciplina)
            db.session.commit()
            flash('Disciplina adicionada com sucesso!', 'success')
            return redirect(url_for('main.disciplinas_list'))
    return render_template('admin_disciplina_form.html', action='add', title="Adicionar Disciplina", disciplina=None)


@bp.route('/admin/disciplinas/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def disciplina_edit(item_id):
    """ Rota para editar uma disciplina existente. (Rota Update) """
    disciplina = Disciplina.query.get_or_404(item_id)

    if request.method == 'POST':
        disciplina.nome = request.form['nome']
        db.session.commit()
        flash('Disciplina atualizada com sucesso!', 'success')
        return redirect(url_for('main.disciplinas_list'))

    return render_template('admin_disciplina_form.html', action='edit', title="Editar Disciplina", disciplina=disciplina)


@bp.route('/admin/disciplinas/delete/<int:item_id>', methods=['POST'])
@login_required
@roles_required('Full')
def disciplina_delete(item_id):
    """ Rota para deletar uma disciplina. (Rota Delete) """
    disciplina = Disciplina.query.get_or_404(item_id)

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
    if request.method == 'POST':
        apelido = request.form.get('apelido')
        if Turma.query.filter_by(apelido=apelido).first():
            flash(f'Uma turma com o apelido "{apelido}" já existe.', 'danger')
        else:
            nova_turma = Turma(
                nome=request.form.get('nome'),
                apelido=apelido,
                categoria=request.form.get('categoria'),
                periodo=request.form.get('periodo')
            )
            db.session.add(nova_turma)
            db.session.commit()
            flash('Turma adicionada com sucesso!', 'success')
            return redirect(url_for('main.turmas_list'))
            
    categorias_curso = current_app.config['CATEGORIAS_CURSO']
    return render_template('admin_turma_form.html', action='add', title="Adicionar Turma", turma=None, categorias_curso=categorias_curso)

# Em portal/routes.py
@bp.route('/admin/turmas/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def turma_edit(item_id):
    turma = Turma.query.get_or_404(item_id)

    if request.method == 'POST':
        # Atualiza o objeto turma com todos os dados do formulário
        turma.nome = request.form['nome']
        turma.apelido = request.form['apelido']
        turma.periodo = request.form.get('periodo') # Usamos .get() para segurança
        turma.categoria = request.form.get('categoria') # Usamos .get() para segurança
        db.session.commit()
        flash('Turma atualizada com sucesso!', 'success')
        return redirect(url_for('main.turmas_list'))

    # Para o método GET, buscamos as categorias do config para popular o dropdown
    categorias_curso = current_app.config['CATEGORIAS_CURSO']
    return render_template('admin_turma_form.html',
                           action='edit',
                           title="Editar Turma",
                           turma=turma,
                           categorias_curso=categorias_curso)


@bp.route('/admin/turmas/delete/<int:item_id>', methods=['POST'])
@login_required
@roles_required('Full')
def turma_delete(item_id):
    """ Rota para deletar uma turma. (Rota Delete) """
    turma = Turma.query.get_or_404(item_id)

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
    Valida a consistência dos dados antes de rodar o motor de geração de horário.
    Principalmente, verifica se algum professor tem mais aulas do que horários disponíveis.
    """
    try:
        # Agrupa o quadro de aulas por professor e soma a quantidade de aulas semanais
        aulas_por_professor = db.session.query(
            QuadroDeAulas.professor_id,
            func.sum(QuadroDeAulas.aulas_semanais).label('total_aulas')
        ).group_by(QuadroDeAulas.professor_id).all()

        conflitos = []
        for prof_id, total_aulas in aulas_por_professor:
            professor = Professor.query.get(prof_id)
            if professor and professor.disponibilidade:
                # Calcula o total de horários disponíveis
                horarios_disponiveis = 0
                for categoria in professor.disponibilidade.values():
                    for turno in categoria.values():
                        for status in turno.values():
                            if status == 'disponivel':
                                horarios_disponiveis += 1
                
                # Compara o total de aulas com os horários disponíveis
                if total_aulas > horarios_disponiveis:
                    conflitos.append({
                        "id": professor.id,
                        "nome": professor.nome,
                        "aulas_atribuidas": total_aulas,
                        "horarios_disponiveis": horarios_disponiveis
                    })

        if conflitos:
            # Se houver conflitos, retorna o relatório de erros para o frontend
            return jsonify({"status": "error", "conflitos": conflitos})
        else:
            # Se tudo estiver ok, retorna sucesso
            return jsonify({"status": "ok", "message": "Validação concluída sem conflitos."})

    except Exception as e:
        # Em caso de um erro inesperado, informa o usuário
        current_app.logger.error(f"Erro na validação de dados: {e}")
        return jsonify({"status": "error", "message": "Ocorreu um erro interno ao validar os dados."}), 500

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

# Adicione este bloco de código ao final de portal/routes.py

# =============================================================================
# ROTAS DE API PARA A PÁGINA DE ALOCAÇÃO MANUAL
# =============================================================================
@bp.route('/admin/api/dados_alocacao/<int:turma_id>') # Mudança para <int:turma_id>
@login_required
def dados_alocacao_api(turma_id):
    """ Retorna todos os dados necessários para renderizar a interface de alocação de uma turma. """
    turma = Turma.query.get_or_404(turma_id)
    
    # Busca a matriz curricular (demanda de aulas) para esta turma
    matriz_turma = []
    quadro_aulas = QuadroDeAulas.query.filter_by(turma_id=turma_id).all()
    for qa in quadro_aulas:
        matriz_turma.append({
            "matriz_id": qa.id,
            "disciplina": qa.disciplina.nome,
            "sigla": qa.disciplina.sigla,
            "professor": qa.professor.nome,
            "aulas_necessarias": qa.aulas_semanais,
            "alocadas": qa.alocacoes.count(), # Conta quantas já foram alocadas
            "origem": qa.origem
        })
    
    # Busca os horários que já foram alocados para esta turma
    horarios_alocados = {}
    # Acessa as alocações através da relação da turma, o que é mais eficiente
    alocacoes_da_turma = HorarioAlocado.query.join(QuadroDeAulas).filter(QuadroDeAulas.turma_id == turma_id).all()

    for aloc in alocacoes_da_turma:
        dia = aloc.dia_semana
        horario = aloc.horario
        if dia not in horarios_alocados:
            horarios_alocados[dia] = {}
        if horario not in horarios_alocados[dia]:
            horarios_alocados[dia][horario] = []
        
        horarios_alocados[dia][horario].append({
            "disciplina": aloc.quadro_aula.disciplina.sigla,
            "professor": aloc.quadro_aula.professor.apelido,
            "sala": aloc.sala.nome,
            "matriz_id": aloc.quadro_aula_id
        })

    # 1. Pega os dicionários de configuração
    grade_config = current_app.config['GRADE_HORARIOS_FIXOS_POR_CATEGORIA']
    periodo_map = current_app.config['PERIODO_MAP']

    # 2. "Traduz" o código do período (ex: '1') para o nome correspondente (ex: 'Manhã')
    # Usamos str(turma.periodo) para garantir que estamos lidando com uma string na busca do dicionário
    periodo_nome = periodo_map.get(str(turma.periodo))

    # 3. Faz a busca na configuração usando o nome do período já traduzido
    grade_da_turma = grade_config.get(turma.categoria, {}).get(periodo_nome, {})

    if not grade_da_turma:
        return jsonify({
            "error": f"Grade de horários não encontrada para a Categoria '{turma.categoria}' e Período '{turma.periodo}'. Verifique o cadastro da turma."
        }), 404
    
    return jsonify({
        "matriz_turma": matriz_turma,
        "horarios_alocados": horarios_alocados,
        "horarios_grade": grade_da_turma
    })


@bp.route('/admin/api/salas-disponiveis', methods=['POST'])
@login_required
def available_rooms():
    """ Retorna uma lista de salas disponíveis para um dia e horário específicos. """
    data = request.get_json()
    dia = data['dia']
    horario = data['horario']
    
    salas_ocupadas_ids = [r[0] for r in db.session.query(HorarioAlocado.sala_id).filter_by(dia_semana=dia, horario=horario).all()]
    salas_disponiveis = Sala.query.filter(Sala.id.notin_(salas_ocupadas_ids)).order_by(Sala.nome).all()
    
    return jsonify({"available_rooms": [s.nome for s in salas_disponiveis]}) # Retorna o nome da sala


@bp.route('/admin/api/alocar', methods=['POST'])
@login_required
def admin_api_alocar():
    """ Cria uma nova alocação no banco de dados. """
    data = request.get_json()
    
    # Busca a sala pelo nome para obter o ID
    sala_obj = Sala.query.filter_by(nome=data['sala']).first_or_404()

    nova_alocacao = HorarioAlocado(
        quadro_aula_id=data['matriz_id'],
        dia_semana=data['dia'],
        horario=data['horario'],
        sala_id=sala_obj.id # Usa o ID da sala
    )
    db.session.add(nova_alocacao)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Aula alocada com sucesso!"})


@bp.route('/admin/api/remover', methods=['POST'])
@login_required
def admin_api_remover():
    """ Remove uma alocação do banco de dados. """
    data = request.get_json()
    
    alocacao_para_remover = HorarioAlocado.query.filter_by(
        quadro_aula_id=data['matriz_id'],
        dia_semana=data['dia'],
        horario=data['horario']
    ).first_or_404()
    
    db.session.delete(alocacao_para_remover)
    db.session.commit()

    return jsonify({"status": "success", "message": "Alocação removida com sucesso!"})

# =============================================================================
# ROTAS DE GERENCIAMENTO DA MATRIZ CURRICULAR (QUADRO DE AULAS)
# =============================================================================

@bp.route('/admin/matriz')
@login_required
@roles_required('Full', 'Supervisor')
def matriz_curricular_list():
    """ Exibe a matriz curricular completa, agrupada por turma. """
    # Buscamos todas as turmas e o SQLAlchemy nos dará acesso 
    # às suas entradas de quadro de aulas através do 'backref' que definimos no modelo.
    turmas = Turma.query.order_by(Turma.nome).all()
    return render_template('admin_matriz_curricular.html', turmas=turmas)


@bp.route('/admin/matriz/add', methods=['GET', 'POST'])
@login_required
@roles_required('Full', 'Supervisor')
def matriz_curricular_add():
    """ Rota para adicionar uma nova entrada na matriz curricular. """
    if request.method == 'POST':
        # Coleta os dados do formulário
        turma_id = request.form.get('turma_id')
        disciplina_id = request.form.get('disciplina_id')
        professor_id = request.form.get('professor_id')
        aulas_semanais = request.form.get('aulas_semanais')
        
        # Cria a nova entrada e salva no banco
        nova_entrada = QuadroDeAulas(
            turma_id=turma_id,
            disciplina_id=disciplina_id,
            professor_id=professor_id,
            aulas_semanais=aulas_semanais
        )
        db.session.add(nova_entrada)
        db.session.commit()
        
        flash('Atribuição de aula adicionada à matriz com sucesso!', 'success')
        return redirect(url_for('main.matriz_curricular_list'))

    # Para o GET, busca os dados para popular os menus do formulário
    turmas = Turma.query.order_by(Turma.nome).all()
    disciplinas = Disciplina.query.order_by(Disciplina.nome).all()
    professores = Professor.query.order_by(Professor.nome).all()
    
    return render_template('admin_matriz_form.html', 
                           action='add', 
                           title="Adicionar Atribuição de Aula",
                           turmas=turmas,
                           disciplinas=disciplinas,
                           professores=professores)


@bp.route('/admin/matriz/delete/<int:item_id>', methods=['POST'])
@login_required
@roles_required('Full')
def matriz_curricular_delete(item_id):
    """ Deleta uma entrada da matriz curricular. """
    entrada = QuadroDeAulas.query.get_or_404(item_id)
    db.session.delete(entrada)
    db.session.commit()
    flash('Atribuição de aula removida com sucesso.', 'success')
    return redirect(url_for('main.matriz_curricular_list'))

# Adicione ou substitua este bloco em portal/routes.py

@bp.route('/admin/reposicao')
@login_required
def admin_reposicao():
    """ Renderiza a página principal de gerenciamento de reposições. """
    sabados_letivos = SabadoLetivo.query.order_by(SabadoLetivo.id).all()
    # Para o formulário de alocação, precisamos da lista de turmas
    turmas = Turma.query.order_by(Turma.nome).all()
    return render_template('admin_reposicao.html', sabados_letivos=sabados_letivos, turmas=turmas)

@bp.route('/admin/reposicao/add-sabado', methods=['POST'])
@login_required
@roles_required('Full', 'Supervisor')
def reposicao_add_sabado():
    """ Cria um novo registro de Sábado Letivo. """
    sabado_id = request.form.get('sabado_id')
    if SabadoLetivo.query.get(sabado_id):
        flash('Este sábado letivo já foi cadastrado.', 'danger')
        return redirect(url_for('main.admin_reposicao'))

    # Processa os horários customizados
    apelidos = request.form.getlist('apelido[]')
    inicios = request.form.getlist('inicio[]')
    fins = request.form.getlist('fim[]')
    grade_customizada = {f"{i}-{f}": a for a, i, f in zip(apelidos, inicios, fins) if a and i and f}

    if not grade_customizada:
        flash('É necessário definir pelo menos um horário para o sábado.', 'warning')
        return redirect(url_for('main.admin_reposicao'))

    novo_sabado = SabadoLetivo(
        id=sabado_id,
        descricao=request.form.get('descricao'),
        grade_horarios=grade_customizada
    )
    db.session.add(novo_sabado)
    db.session.commit()
    flash('Sábado letivo criado com sucesso!', 'success')
    return redirect(url_for('main.admin_reposicao'))

@bp.route('/admin/reposicao/delete/<string:sabado_id>', methods=['POST'])
@login_required
@roles_required('Full')
def reposicao_delete_sabado(sabado_id):
    """ Deleta um sábado letivo e todas as suas alocações. """
    sabado = SabadoLetivo.query.get_or_404(sabado_id)
    db.session.delete(sabado)
    db.session.commit()
    flash(f'Sábado letivo de {sabado_id} foi removido com sucesso.', 'success')
    return redirect(url_for('main.admin_reposicao'))

# --- ROTAS DE API PARA A PÁGINA DE REPOSIÇÃO ---

@bp.route('/admin/api/dados_reposicao/<string:sabado_id>/<int:turma_id>')
@login_required
def dados_reposicao_api(sabado_id, turma_id):
    """ Retorna os dados para a interface de alocação de reposição. """
    sabado = SabadoLetivo.query.get_or_404(sabado_id)
    turma = Turma.query.get_or_404(turma_id)

    matriz = QuadroDeAulas.query.filter_by(turma_id=turma.id).all()
    matriz_ids = [qa.id for qa in matriz]

    alocacoes_atuais = ReposicaoAlocada.query.filter(
        ReposicaoAlocada.sabado_id == sabado.id,
        ReposicaoAlocada.quadro_aula_id.in_(matriz_ids)
    ).all()

    # Conta quantas aulas de cada item da matriz já foram alocadas
    alocacoes_contadas = {qa_id: 0 for qa_id in matriz_ids}
    for aloc in alocacoes_atuais:
        if aloc.quadro_aula_id in alocacoes_contadas:
            alocacoes_contadas[aloc.quadro_aula_id] += 1

    matriz_formatada = [{
        "matriz_id": qa.id, "disciplina": qa.disciplina.nome, "professor": qa.professor.nome,
        "aulas_necessarias": qa.aulas_semanais, "alocadas": alocacoes_contadas.get(qa.id, 0)
    } for qa in matriz]

    alocacoes_formatadas = {}
    for aloc in alocacoes_atuais:
        horario = aloc.horario
        if horario not in alocacoes_formatadas:
            alocacoes_formatadas[horario] = []
        alocacoes_formatadas[horario].append({
            "disciplina": aloc.quadro_aula.disciplina.sigla,
            "professor": aloc.quadro_aula.professor.apelido,
            "sala": aloc.sala.nome, "matriz_id": aloc.quadro_aula_id
        })

    return jsonify({
        "grade_horarios": sabado.grade_horarios,
        "matriz": matriz_formatada,
        "alocacoes": alocacoes_formatadas
    })


# Crie placeholders para as outras APIs para evitar BuildError
@bp.route('/admin/api/reposicao/alocar', methods=['POST'])
@login_required
def reposicao_api_alocar():
    """ Cria uma nova alocação de reposição no banco de dados. """
    data = request.get_json()
    try:
        sala_obj = Sala.query.filter_by(nome=data['sala_nome']).first_or_404()
        
        nova_alocacao = ReposicaoAlocada(
            sabado_id=data['sabado_id'],
            quadro_aula_id=data['matriz_id'],
            horario=data['horario'],
            sala_id=sala_obj.id
        )
        db.session.add(nova_alocacao)
        db.session.commit()
        return jsonify({"status": "success", "message": "Aula de reposição alocada com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/admin/api/reposicao/remover', methods=['POST'])
@login_required
def reposicao_api_remover():
    """ Remove uma alocação de reposição do banco de dados. """
    data = request.get_json()
    try:
        alocacao_para_remover = ReposicaoAlocada.query.filter_by(
            sabado_id=data['sabado_id'],
            quadro_aula_id=data['matriz_id'],
            horario=data['horario']
        ).first_or_404()
        
        db.session.delete(alocacao_para_remover)
        db.session.commit()
        return jsonify({"status": "success", "message": "Alocação removida com sucesso!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    
@bp.route('/admin/api/reposicao/salas-disponiveis', methods=['POST'])
@login_required
def reposicao_available_rooms():
    """ Retorna uma lista de salas disponíveis para um sábado e horário específicos. """
    data = request.get_json()
    sabado_id = data.get('sabado_id')
    horario = data.get('horario')

    # Encontra os IDs de todas as salas ocupadas naquele sábado e horário
    salas_ocupadas_ids = [r.sala_id for r in ReposicaoAlocada.query.filter_by(sabado_id=sabado_id, horario=horario).all()]
    
    # Busca todas as salas cujo ID não está na lista de ocupadas
    salas_disponiveis = Sala.query.filter(Sala.id.notin_(salas_ocupadas_ids)).order_by(Sala.nome).all()
    
    return jsonify({"available_rooms": [s.nome for s in salas_disponiveis]})
