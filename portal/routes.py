# portal/routes.py

# ========================================================================
# 1. IMPORTAÇÕES
# ========================================================================
import json
import csv
import io
from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    jsonify,
    current_app,
    session,
)
from werkzeug.security import generate_password_hash
from sqlalchemy import or_, func

from .auth import login_required, roles_required

# --- CORREÇÃO DEFINITIVA DAS IMPORTAÇÕES ---
from .models import (
    db,
    Professor,
    Disciplina,
    Turma,
    Sala,
    User,
    QuadroDeAulas,
    SabadoLetivo,
    HorarioAlocado,
    ReposicaoAlocada,
    GradeHorario,
)

# from .scheduler_engine import resolver_horarios # Comentado pois não está sendo usado no momento

bp = Blueprint("main", __name__)


# ========================================================================
# 2. ROTAS PRINCIPAIS E DASHBOARD
# ========================================================================

# Em portal/routes.py


@bp.route("/")
def index():
    """
    Rota pública para visualização da grade.
    Prepara os dados de TODAS as turmas com aulas, agrupadas por período e ano/categoria.
    """
    try:
        from sqlalchemy.orm import joinedload
        import locale

        try:
            locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
        except locale.Error:
            locale.setlocale(locale.LC_TIME, "Portuguese_Brazil")

        aulas_alocadas = HorarioAlocado.query.all()
        horarios_por_turma = {}
        turmas_com_aulas = {aula.quadro_aula.turma_id for aula in aulas_alocadas}

        for aula in aulas_alocadas:
            turma_id = aula.quadro_aula.turma_id
            if turma_id not in horarios_por_turma:
                horarios_por_turma[turma_id] = {}
            if aula.dia_semana not in horarios_por_turma[turma_id]:
                horarios_por_turma[turma_id][aula.dia_semana] = {}
            if aula.horario not in horarios_por_turma[turma_id][aula.dia_semana]:
                horarios_por_turma[turma_id][aula.dia_semana][aula.horario] = []

            horarios_por_turma[turma_id][aula.dia_semana][aula.horario].append(
                {
                    "sala": aula.sala.nome,
                    "disciplina": aula.quadro_aula.disciplina.sigla,
                }
            )

        turmas_para_exibir = (
            Turma.query.filter(Turma.id.in_(turmas_com_aulas))
            .order_by(Turma.nome)
            .all()
        )

        periodo_map = current_app.config["PERIODO_MAP"]
        grupos_por_periodo = {"Manhã": [], "Tarde": [], "Noite": []}

        for turma in turmas_para_exibir:
            turma_dict = {
                "id": turma.id,
                "nome": turma.nome,
                "apelido": turma.apelido,
                "periodo": turma.periodo,
                "categoria": turma.categoria,
            }
            periodo_nome = periodo_map.get(str(turma.periodo))

            if periodo_nome == "Integral":
                if "Manhã" in grupos_por_periodo:
                    grupos_por_periodo["Manhã"].append(turma_dict)
                if "Tarde" in grupos_por_periodo:
                    grupos_por_periodo["Tarde"].append(turma_dict)
            elif periodo_nome in grupos_por_periodo:
                grupos_por_periodo[periodo_nome].append(turma_dict)

        # --- LÓGICA DE PAGINAÇÃO CORRIGIDA ---
        paginas_por_periodo = {}
        for nome_periodo, lista_turmas in grupos_por_periodo.items():
            if not lista_turmas:
                continue

            # Agrupa as turmas do período por ano/categoria
            grupos_por_ano = {
                "Ensino Médio - 1º Ano": [],
                "Ensino Médio - 2º Ano": [],
                "Ensino Médio - 3º Ano": [],
                "Curso Técnico": [],
            }
            for turma in lista_turmas:
                if turma["categoria"] == "Curso Técnico":
                    grupos_por_ano["Curso Técnico"].append(turma)
                elif turma["nome"].startswith("1"):
                    grupos_por_ano["Ensino Médio - 1º Ano"].append(turma)
                elif turma["nome"].startswith("2"):
                    grupos_por_ano["Ensino Médio - 2º Ano"].append(turma)
                elif turma["nome"].startswith("3"):
                    grupos_por_ano["Ensino Médio - 3º Ano"].append(turma)

            paginas_do_periodo_atual = []
            for nome_grupo, turmas_do_grupo in grupos_por_ano.items():
                if not turmas_do_grupo:
                    continue
                for i in range(0, len(turmas_do_grupo), 6):
                    paginas_do_periodo_atual.append(
                        {"titulo": nome_grupo, "turmas": turmas_do_grupo[i : i + 6]}
                    )

            if paginas_do_periodo_atual:
                paginas_por_periodo[nome_periodo] = paginas_do_periodo_atual

        grade_horarios = current_app.config["GRADE_HORARIOS_FIXOS_POR_CATEGORIA"]

    except Exception as e:
        flash(f"Ocorreu um erro ao carregar os horários: {e}", "danger")
        paginas_por_periodo, horarios_por_turma, grade_horarios = {}, {}, {}

    return render_template(
        "index.html",
        paginas_por_periodo=paginas_por_periodo,
        horarios_alocados=horarios_por_turma,
        grade_horarios=grade_horarios,
    )


@bp.route("/admin/dashboard")
@login_required
def dashboard():
    return render_template("admin_dashboard.html")


# ========================================================================
# 3. ROTAS DE ALOCAÇÃO (SEMANAL E REPOSIÇÃO)
# ========================================================================


# --- ROTAS DE LÓGICA DE NEGÓCIO (ALOCAÇÃO, ETC.) ---
@bp.route("/admin/alocacao", methods=["GET"])
@login_required
@roles_required(["Full", "Supervisor"])
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
    grade_horarios = current_app.config["GRADE_HORARIOS_FIXOS_POR_CATEGORIA"]

    # Ponto de Atenção: O "quadro de aulas" (a demanda de aulas por turma)
    # ainda não tem uma tabela no banco. Abordaremos isso no próximo passo.
    # Por enquanto, podemos passar uma estrutura vazia ou um exemplo.
    quadro_aulas_existente = {}  # Futuramente, isso também virá do banco.

    return render_template(
        "admin_alocacao.html",
        professores=professores,
        turmas=turmas,
        disciplinas=disciplinas,
        salas=salas,
        grade_horarios=grade_horarios,
        quadro_aulas=quadro_aulas_existente,
    )


@bp.route("/admin/importar", methods=["POST"])
@login_required
@roles_required(["Full"])
def importar_quadro_aulas_csv():
    file = request.files.get("csv_file")
    if not file or not file.filename.endswith(".csv"):
        flash("Formato de arquivo inválido. Por favor, envie um arquivo .csv", "danger")
        return redirect(url_for("main.dashboard"))

    professores_cache = {}
    disciplinas_cache = {}
    turmas_cache = {}
    summary = {"processed": 0, "skipped": 0}
    skipped_rows_details = []

    try:
        # --- CORREÇÃO APLICADA AQUI ---
        # A ordem da exclusão foi corrigida.
        # Primeiro, apagamos os registros que dependem do QuadroDeAulas.
        db.session.query(ReposicaoAlocada).delete()
        db.session.query(HorarioAlocado).delete()

        # Agora, com as dependências removidas, podemos apagar o QuadroDeAulas
        # e as outras tabelas principais sem violar as restrições.
        db.session.query(QuadroDeAulas).delete()
        db.session.query(Professor).delete()
        db.session.query(Disciplina).delete()
        db.session.query(Turma).delete()

        stream = io.StringIO(file.stream.read().decode("UTF-8-sig"), newline=None)
        reader = csv.DictReader(stream, delimiter=";")

        for i, row in enumerate(reader, start=2):
            try:
                # --- Extração e Limpeza dos Dados ---
                prof_nome = row.get("Professor Ministrando", "").strip()
                prof_apelido = (
                    row.get("Professor Apelido", "").strip() or prof_nome.split(" ")[0]
                )
                if prof_apelido not in professores_cache:
                    professor = Professor.query.filter(
                        or_(
                            Professor.apelido == prof_apelido,
                            Professor.nome == prof_nome,
                        )
                    ).first()
                    if not professor:
                        professor = Professor(apelido=prof_apelido, nome=prof_nome)
                        db.session.add(professor)
                        db.session.flush()
                    professores_cache[prof_apelido] = professor

                disciplina_nome = row.get("Componente", "").strip()
                disciplina_sigla = (
                    row.get("Sigla", "").strip() or disciplina_nome[:3].upper()
                )
                if disciplina_sigla not in disciplinas_cache:
                    disciplina = Disciplina.query.filter(
                        or_(
                            Disciplina.sigla == disciplina_sigla,
                            Disciplina.nome == disciplina_nome,
                        )
                    ).first()
                    if not disciplina:
                        disciplina = Disciplina(
                            sigla=disciplina_sigla, nome=disciplina_nome
                        )
                        db.session.add(disciplina)
                        db.session.flush()
                    disciplinas_cache[disciplina_sigla] = disciplina

                # --- Lógica de Turma ---
                turma_apelido = row.get("Turma Apelido", "").strip()
                if turma_apelido not in turmas_cache:
                    turma = Turma.query.filter_by(apelido=turma_apelido).first()
                    if not turma:
                        turma = Turma(
                            apelido=turma_apelido,
                            nome=row.get("Turma", "").strip(),
                            periodo=row.get("Período", "").strip(),
                            categoria=row.get("Categoria", "").strip(),
                        )
                        db.session.add(turma)
                        db.session.flush()
                    turmas_cache[turma_apelido] = turma

                # --- Cria a entrada na Matriz Curricular ---
                qtde_aulas = int(
                    float(row.get("Qtde Aulas", "0").strip().replace(",", "."))
                )
                nova_entrada = QuadroDeAulas(
                    turma_id=turmas_cache[turma_apelido].id,
                    disciplina_id=disciplinas_cache[disciplina_sigla].id,
                    professor_id=professores_cache[prof_apelido].id,
                    aulas_semanais=qtde_aulas,
                    origem=row.get("Origem", "").strip(),
                )
                db.session.add(nova_entrada)
                summary["processed"] += 1

                if not all([turma_apelido, disciplina_sigla, prof_apelido]):
                    raise ValueError(
                        "Colunas essenciais (Turma Apelido, Sigla, Professor Apelido) estão vazias."
                    )

            except Exception as row_error:
                summary["skipped"] += 1
                skipped_rows_details.append(
                    {"line_number": i, "data": row, "reason": str(row_error)}
                )

        db.session.commit()
        flash(
            f'Importação concluída! Processados: {summary["processed"]}, Ignorados: {summary["skipped"]}.',
            "success",
        )

    except Exception as e:
        db.session.rollback()
        flash(
            f"Ocorreu um erro crítico durante a importação. Nenhuma alteração foi salva. Erro: {e}",
            "danger",
        )
        return redirect(url_for("main.dashboard"))

    return render_template(
        "admin_import_report.html", summary=summary, skipped_rows=skipped_rows_details
    )


# --- ROTAS DE GERENCIAMENTO DE USUÁRIOS ---


@bp.route("/admin/users")
@login_required
@roles_required(["Full"])
def users_list():
    """Lista todos os usuários do sistema."""
    # Lógica de DB: Pega todos os usuários, ordenados pelo nome.
    users = User.query.order_by(User.username).all()
    return render_template("admin_users_list.html", users=users)


@bp.route("/admin/users/add", methods=["GET", "POST"])
@login_required
@roles_required(["Full"])
def user_add():
    """Adiciona um novo usuário."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        # Lógica de DB: Verifica se o usuário já existe.
        if User.query.filter_by(username=username).first():
            flash("Nome de usuário já existe.", "danger")
        else:
            # Lógica de DB: Cria um novo usuário e o salva no banco.
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password_hash=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()
            flash("Usuário adicionado com sucesso!", "success")
            return redirect(url_for("main.users_list"))

    return render_template(
        "admin_user_form.html", action="add", title="Adicionar Usuário", user=None
    )


@bp.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
@roles_required(["Full"])
def user_edit(user_id):
    """
    Rota para editar um usuário existente.
    <int:user_id> na URL captura o ID do usuário e o passa como argumento para a função.
    """
    # Usar get_or_404 é uma melhor prática do Flask. Ele busca o usuário pelo ID
    # e, se não encontrar, automaticamente retorna uma página de erro 404 (Not Found).
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        # Pega os dados do formulário enviado
        username = request.form["username"]
        role = request.form["role"]
        password = request.form["password"]
        if password:
            user.password_hash = generate_password_hash(password)
        db.session.commit()
        flash("Usuário atualizado com sucesso!", "success")
        return redirect(url_for("main.users_list"))

    # CORREÇÃO: Garantimos que a variável se chama 'user' ao passar para o template
    return render_template(
        "admin_user_form.html", action="edit", title="Editar Usuário", user=user
    )


@bp.route("/admin/users/delete/<int:user_id>", methods=["POST"])
@login_required
@roles_required(["Full"])
def user_delete(user_id):
    """
    Rota para deletar um usuário.
    É crucial que esta rota aceite apenas o método POST para evitar exclusões acidentais
    através de links (que são requisições GET).
    """
    user = User.query.get_or_404(user_id)

    # Uma verificação de segurança importante: não permitir que um usuário delete a si mesmo.
    if user.id == session.get("user_id"):
        flash("Você não pode deletar sua própria conta de usuário.", "danger")
        return redirect(url_for("main.users_list"))

    # Lógica de exclusão: remove o usuário da sessão do banco de dados
    db.session.delete(user)
    # Efetiva a exclusão no banco de dados.
    db.session.commit()

    flash("Usuário deletado com sucesso!", "success")
    return redirect(url_for("main.users_list"))


# --- ROTAS DE GERENCIAMENTO DE PROFESSORES ---


@bp.route("/admin/professores")
@login_required
@roles_required(["Full", "Supervisor"])
def professores_list():
    """
    Rota para listar todos os professores cadastrados.
    O nome desta função, 'professores_list', gera o endpoint 'main.professores_list'.
    """
    professores = Professor.query.order_by(Professor.nome).all()
    return render_template(
        "admin_view_data.html",
        data=professores,
        title="Professores",
        data_type="professores",
    )


@bp.route("/admin/professores/add", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def professor_add():
    if request.method == "POST":

        nome = request.form.get("nome")
        apelido = request.form.get("apelido")

        if Professor.query.filter(
            or_(Professor.nome == nome, Professor.apelido == apelido)
        ).first():
            flash("Um professor com este nome ou apelido já existe.", "danger")
        else:
            novo_professor = Professor(nome=nome, apelido=apelido)
            db.session.add(novo_professor)
            db.session.commit()
            flash("Professor adicionado com sucesso!", "success")
            return redirect(url_for("main.professores_list"))

    return render_template("admin_professor_form.html", item=None)


@bp.route("/admin/professores/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def professor_edit(item_id):
    professor = Professor.query.get_or_404(item_id)
    if request.method == "POST":
        professor.nome = request.form["nome"]
        # --- LINHA ADICIONADA ---
        professor.apelido = request.form["apelido"]

        try:
            db.session.commit()
            flash("Professor atualizado com sucesso!", "success")
            return redirect(url_for("main.professores_list"))
        except Exception as e:
            db.session.rollback()
            flash(
                f"Erro ao atualizar. Verifique se o nome ou apelido já está em uso por outro professor. Erro: {e}",
                "danger",
            )

    return render_template("admin_professor_form.html", item=professor)


@bp.route("/admin/professores/disponibilidade/<int:item_id>", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def professor_disponibilidade(item_id):
    """
    Rota para editar a disponibilidade de um professor.
    GET: Exibe a grade interativa.
    POST: Recebe um JSON e salva a nova disponibilidade.
    """
    professor = Professor.query.get_or_404(item_id)

    if request.method == "POST":
        # A nova interface envia um JSON
        nova_disponibilidade = request.get_json()

        # Atualiza a coluna de disponibilidade do professor
        professor.disponibilidade = nova_disponibilidade
        db.session.commit()

        # Retorna uma resposta de sucesso para o JavaScript
        return jsonify(
            {"status": "success", "message": "Disponibilidade atualizada com sucesso!"}
        )

    # Lógica para o método GET (carregar a página)

    # Busca a configuração de horários
    grade_config = current_app.config["GRADE_HORARIOS_FIXOS_POR_CATEGORIA"]

    # Cria uma lista mestre de todos os horários possíveis para exibir na grade
    todos_horarios = set()
    for categoria in grade_config.values():
        for periodo in categoria.values():
            for horario, apelido in periodo.items():
                if apelido.upper() not in ["INTERVALO", "ALMOÇO"]:
                    todos_horarios.add(horario)

    # Ordena os horários para exibição consistente
    horarios_ordenados = sorted(list(todos_horarios))
    dias_semana = [
        "segunda-feira",
        "terca-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
    ]

    return render_template(
        "admin_professor_disponibilidade.html",
        professor=professor,
        horarios=horarios_ordenados,
        dias=dias_semana,
    )


@bp.route("/admin/professores/delete/<int:item_id>", methods=["POST"])
@login_required
@roles_required(["Full"])
def professor_delete(item_id):
    """Rota para deletar um professor."""
    professor = Professor.query.get_or_404(item_id)
    db.session.delete(professor)
    db.session.commit()
    flash("Professor deletado com sucesso!", "success")
    return redirect(url_for("main.professores_list"))


# --- ROTAS DE GERENCIAMENTO DE SALAS ---


@bp.route("/admin/salas")
@login_required
@roles_required(["Full", "Supervisor"])
def salas_list():
    """Lista todas as salas cadastradas. (Rota Read)"""
    salas = Sala.query.order_by(Sala.nome).all()
    return render_template(
        "admin_view_data.html", data=salas, title="Salas", data_type="salas"
    )


@bp.route("/admin/salas/add", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def sala_add():
    if request.method == "POST":
        nome = request.form.get("nome")
        # Verifica se já existe uma sala com este nome
        if Sala.query.filter_by(nome=nome).first():
            flash(f'Uma sala com o nome "{nome}" já existe.', "danger")
        else:
            nova_sala = Sala(nome=nome)  # Cria o objeto apenas com o nome
            db.session.add(nova_sala)
            db.session.commit()
            flash("Sala adicionada com sucesso!", "success")
            return redirect(url_for("main.salas_list"))
    return render_template(
        "admin_sala_form.html", action="add", title="Adicionar Sala", sala=None
    )


@bp.route("/admin/salas/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def sala_edit(item_id):
    """Rota para editar uma sala existente. (Rota Update)"""
    sala = Sala.query.get_or_404(item_id)

    if request.method == "POST":
        sala.nome = request.form["nome"]
        db.session.commit()
        flash("Sala atualizada com sucesso!", "success")
        return redirect(url_for("main.salas_list"))

    return render_template(
        "admin_sala_form.html", action="edit", title="Editar Sala", sala=sala
    )


@bp.route("/admin/salas/delete/<int:item_id>", methods=["POST"])
@login_required
@roles_required(["Full"])
def sala_delete(item_id):
    """Rota para deletar uma sala. (Rota Delete)"""
    sala = Sala.query.get_or_404(item_id)

    # Lógica de Negócio: Antes de deletar, o ideal é verificar se a sala
    # está sendo usada em algum horário para não quebrar a alocação.

    db.session.delete(sala)
    db.session.commit()
    flash("Sala deletada com sucesso!", "success")
    return redirect(url_for("main.salas_list"))


# --- ROTAS DE GERENCIAMENTO DE DISCIPLINAS ---


@bp.route("/admin/disciplinas")
@login_required
@roles_required(["Full", "Supervisor"])
def disciplinas_list():
    """Lista todas as disciplinas cadastradas. (Rota Read)"""
    disciplinas = Disciplina.query.order_by(Disciplina.nome).all()
    return render_template(
        "admin_view_data.html",
        data=disciplinas,
        title="Disciplinas",
        data_type="disciplinas",
    )


@bp.route("/admin/disciplinas/add", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def disciplina_add():
    if request.method == "POST":
        nome = request.form["nome"]
        sigla = request.form["sigla"]

        # Verifica se já existe uma disciplina com o mesmo nome ou sigla
        if Disciplina.query.filter(
            or_(Disciplina.nome == nome, Disciplina.sigla == sigla)
        ).first():
            flash("Uma disciplina com este nome ou sigla já existe.", "danger")
        else:
            # --- LÓGICA ATUALIZADA ---
            nova_disciplina = Disciplina(nome=nome, sigla=sigla)
            db.session.add(nova_disciplina)
            db.session.commit()
            flash("Disciplina adicionada com sucesso!", "success")
            return redirect(url_for("main.disciplinas_list"))

    # Passamos 'item' como None para o template saber que é um formulário de adição
    return render_template(
        "admin_disciplina_form.html", item=None, title="Adicionar Disciplina"
    )


@bp.route("/admin/disciplinas/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def disciplina_edit(item_id):
    disciplina = Disciplina.query.get_or_404(item_id)
    if request.method == "POST":
        disciplina.nome = request.form["nome"]
        # --- LINHA ADICIONADA ---
        disciplina.sigla = request.form["sigla"]

        try:
            db.session.commit()
            flash("Disciplina atualizada com sucesso!", "success")
            return redirect(url_for("main.disciplinas_list"))
        except Exception:
            db.session.rollback()
            flash(
                "Erro ao atualizar. Verifique se o nome ou a sigla já está em uso.",
                "danger",
            )

    # Passamos o objeto 'disciplina' como 'item' para o template
    return render_template(
        "admin_disciplina_form.html", item=disciplina, title="Editar Disciplina"
    )


@bp.route("/admin/disciplinas/delete/<int:item_id>", methods=["POST"])
@login_required
@roles_required(["Full"])
def disciplina_delete(item_id):
    """Rota para deletar uma disciplina. (Rota Delete)"""
    disciplina = Disciplina.query.get_or_404(item_id)

    # Lógica de Negócio: Antes de deletar, verificar se a disciplina não faz
    # parte de um quadro de aulas existente para manter a integridade.

    db.session.delete(disciplina)
    db.session.commit()
    flash("Disciplina deletada com sucesso!", "success")
    return redirect(url_for("main.disciplinas_list"))


# --- ROTAS DE GERENCIAMENTO DE TURMAS ---


@bp.route("/admin/turmas")
@login_required
@roles_required(["Full", "Supervisor"])
def turmas_list():
    """Lista todas as turmas cadastradas. (Rota Read)"""
    turmas = Turma.query.order_by(Turma.nome).all()
    # Reutilizamos o template genérico para exibir os dados
    return render_template(
        "admin_view_data.html", data=turmas, title="Turmas", data_type="turmas"
    )


@bp.route("/admin/turmas/add", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def turma_add():
    if request.method == "POST":
        try:
            # Pega o nome do período enviado pelo formulário (ex: "Manhã")
            periodo_nome = request.form["periodo"]

            # Cria um mapa reverso para encontrar o ID a partir do nome
            periodo_map_reverso = {
                v: k for k, v in current_app.config["PERIODO_MAP"].items()
            }
            periodo_id = periodo_map_reverso.get(periodo_nome)

            if not periodo_id:
                raise ValueError("Período inválido selecionado.")

            nova_turma = Turma(
                nome=request.form["nome"],
                apelido=request.form["apelido"],
                categoria=request.form["categoria"],
                periodo=periodo_id,  # Salva o ID numérico (ex: "1")
            )
            db.session.add(nova_turma)
            db.session.commit()
            flash("Turma adicionada com sucesso!", "success")
            return redirect(url_for("main.turmas_list"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao adicionar turma: {e}", "danger")

    return render_template("admin_turma_form.html", item=None)


# Em portal/routes.py
@bp.route("/admin/turmas/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def turma_edit(item_id):
    turma = Turma.query.get_or_404(item_id)
    if request.method == "POST":
        try:
            turma.nome = request.form["nome"]
            turma.apelido = request.form["apelido"]
            turma.categoria = request.form["categoria"]

            # Pega o nome do período enviado pelo formulário (ex: "Tarde")
            periodo_nome = request.form["periodo"]

            # Cria um mapa reverso para encontrar o ID a partir do nome
            periodo_map_reverso = {
                v: k for k, v in current_app.config["PERIODO_MAP"].items()
            }
            periodo_id = periodo_map_reverso.get(periodo_nome)

            if not periodo_id:
                raise ValueError("Período inválido selecionado.")

            turma.periodo = periodo_id  # Salva o ID numérico (ex: "2")

            db.session.commit()
            flash("Turma atualizada com sucesso!", "success")
            return redirect(url_for("main.turmas_list"))
        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao atualizar turma: {e}", "danger")

    return render_template("admin_turma_form.html", item=turma)


@bp.route("/admin/turmas/delete/<int:item_id>", methods=["POST"])
@login_required
@roles_required(["Full"])
def turma_delete(item_id):
    """Rota para deletar uma turma. (Rota Delete)"""
    turma = Turma.query.get_or_404(item_id)

    # Lógica de Negócio Importante:
    # Antes de deletar uma turma, seria ideal verificar se ela não possui
    # aulas ou professores vinculados em um horário já gerado.
    # Isso previne inconsistências nos dados.

    db.session.delete(turma)
    db.session.commit()
    flash("Turma deletada com sucesso!", "success")
    return redirect(url_for("main.turmas_list"))


@bp.route("/gerar-novo-horario", methods=["POST"])
@login_required
@roles_required(["Full", "Supervisor"])
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
        "professores": {
            p.id: {"nome": p.nome, "disponibilidade": p.disponibilidade or {}}
            for p in professores_db
        },
        "disciplinas": {d.id: {"nome": d.nome} for d in disciplinas_db},
        "salas": {s.id: {"nome": s.nome} for s in salas_db},
        "turmas": {t.id: {"nome": t.nome} for t in turmas_db},
        "quadro_aulas": quadro_aulas_demanda,  # Usa a demanda que veio do frontend
    }

    # 4. Chama o motor com os dados devidamente formatados.
    try:
        solucoes = resolver_horarios(dados_para_motor)
        if not solucoes:
            return (
                jsonify(
                    {
                        "error": "Não foi possível encontrar uma solução com as restrições fornecidas."
                    }
                ),
                422,
            )  # Unprocessable Entity

        # O motor já retorna uma lista de soluções em formato JSON serializável.
        return jsonify(solucoes)

    except Exception as e:
        # É uma boa prática capturar exceções do motor e retornar um erro claro.
        current_app.logger.error(f"Erro no motor de agendamento: {e}")
        return (
            jsonify({"error": "Ocorreu um erro interno ao processar o horário."}),
            500,
        )


## --- ROTAS PARA IMPORTAÇÂO DE PROFESSORES, TURMAS, DISCIPLINAS, SALAS ---
@bp.route("/admin/import/professores", methods=["GET", "POST"])
@login_required
@roles_required(["Full"])
def importar_professores_csv():
    if request.method == "POST":
        if "csv_file" not in request.files:
            flash("Nenhum arquivo selecionado", "danger")
            return redirect(request.url)

        file = request.files["csv_file"]

        if file.filename == "":
            flash("Nenhum arquivo selecionado", "danger")
            return redirect(request.url)

        if file and file.filename.endswith(".csv"):
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
                    flash(
                        f"{len(novos_professores)} novos professores importados com sucesso!",
                        "success",
                    )
                else:
                    flash("Nenhum novo professor para importar.", "info")

            except Exception as e:
                db.session.rollback()
                flash(f"Ocorreu um erro durante a importação: {e}", "danger")

            return redirect(url_for("main.professores_list"))

    return render_template(
        "sua_pagina_de_importacao.html", title="Importar Professores"
    )


# =============================================================================
# ROTAS DE API PARA O DASHBOARD (GERAÇÃO AUTOMÁTICA)
# =============================================================================


@bp.route("/admin/api/validar-dados", methods=["POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def validar_dados_api():
    """
    Valida a consistência dos dados antes de rodar o motor de geração de horário.
    Principalmente, verifica se algum professor tem mais aulas do que horários disponíveis.
    """
    try:
        # Agrupa o quadro de aulas por professor e soma a quantidade de aulas semanais
        aulas_por_professor = (
            db.session.query(
                QuadroDeAulas.professor_id,
                func.sum(QuadroDeAulas.aulas_semanais).label("total_aulas"),
            )
            .group_by(QuadroDeAulas.professor_id)
            .all()
        )

        conflitos = []
        for prof_id, total_aulas in aulas_por_professor:
            professor = Professor.query.get(prof_id)
            if professor and professor.disponibilidade:
                # Calcula o total de horários disponíveis
                horarios_disponiveis = 0
                for categoria in professor.disponibilidade.values():
                    for turno in categoria.values():
                        for status in turno.values():
                            if status == "disponivel":
                                horarios_disponiveis += 1

                # Compara o total de aulas com os horários disponíveis
                if total_aulas > horarios_disponiveis:
                    conflitos.append(
                        {
                            "id": professor.id,
                            "nome": professor.nome,
                            "aulas_atribuidas": total_aulas,
                            "horarios_disponiveis": horarios_disponiveis,
                        }
                    )

        if conflitos:
            # Se houver conflitos, retorna o relatório de erros para o frontend
            return jsonify({"status": "error", "conflitos": conflitos})
        else:
            # Se tudo estiver ok, retorna sucesso
            return jsonify(
                {"status": "ok", "message": "Validação concluída sem conflitos."}
            )

    except Exception as e:
        # Em caso de um erro inesperado, informa o usuário
        current_app.logger.error(f"Erro na validação de dados: {e}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Ocorreu um erro interno ao validar os dados.",
                }
            ),
            500,
        )


@bp.route("/admin/api/gerar-horario", methods=["POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def gerar_horario_automatico():
    """
    Endpoint da API para iniciar a tarefa de geração de horário em background.
    TODO: Implementar a lógica real com Celery ou outra fila de tarefas.
    """
    # Por enquanto, retornamos um ID de tarefa falso para o frontend continuar.
    return jsonify({"task_id": "tarefa_ficticia_12345"}), 202  # HTTP 202: Accepted


@bp.route("/admin/api/status/<string:task_id>")
@login_required
@roles_required(["Full", "Supervisor"])
def verificar_status_geracao(task_id):
    """
    Endpoint da API para verificar o status de uma tarefa de geração.
    TODO: Implementar a consulta real do status da tarefa.
    """
    # Para o teste, retornamos 'completed' diretamente para finalizar o ciclo no frontend.
    return jsonify(
        {"status": "completed", "result": "Horário gerado com sucesso (placeholder)!"}
    )


@bp.route("/admin/sugestoes")
@login_required
@roles_required(["Full", "Supervisor"])
def listar_sugestoes():
    """
    Rota para listar as sugestões de horários gerados pelo motor.
    TODO: Implementar a busca das sugestões salvas no banco de dados.
    """
    # O template 'admin_sugestoes_lista.html' espera uma variável 'sugestoes'.
    # Passamos uma lista vazia por enquanto.
    sugestoes = []

    flash(
        "A funcionalidade de Sugestões de Horário ainda está em desenvolvimento.",
        "info",
    )
    return render_template("admin_sugestoes_lista.html", sugestoes=sugestoes)


# Adicione este bloco de código ao final de portal/routes.py


# =============================================================================
# ROTAS DE API PARA A PÁGINA DE ALOCAÇÃO MANUAL
# =============================================================================
# Em portal/routes.py


@bp.route("/admin/api/dados_alocacao/<int:turma_id>")
@login_required
def dados_alocacao_api(turma_id):
    """Retorna todos os dados necessários para renderizar a interface de alocação de uma turma."""
    try:
        turma = Turma.query.get_or_404(turma_id)
        matriz_turma = []
        quadro_aulas = QuadroDeAulas.query.filter_by(turma_id=turma_id).all()

        for qa in quadro_aulas:
            matriz_turma.append(
                {
                    "matriz_id": qa.id,
                    "disciplina": qa.disciplina.nome,
                    "sigla": qa.disciplina.sigla,
                    "professor": qa.professor.nome,
                    "aulas_necessarias": qa.aulas_semanais,
                    # --- CORREÇÃO APLICADA AQUI ---
                    # O nome correto do relacionamento é 'horarios_alocados'.
                    # Usamos len() para contar os itens na lista do relacionamento.
                    "alocadas": len(qa.horarios_alocados),
                    "origem": qa.origem,
                }
            )

        horarios_alocados = {}
        alocacoes_da_turma = (
            HorarioAlocado.query.join(QuadroDeAulas)
            .filter(QuadroDeAulas.turma_id == turma_id)
            .all()
        )

        for aloc in alocacoes_da_turma:
            dia = aloc.dia_semana
            horario = aloc.horario
            if dia not in horarios_alocados:
                horarios_alocados[dia] = {}
            if horario not in horarios_alocados[dia]:
                horarios_alocados[dia][horario] = []

            horarios_alocados[dia][horario].append(
                {
                    "disciplina": aloc.quadro_aula.disciplina.sigla,
                    "professor": aloc.quadro_aula.professor.apelido,
                    "sala": aloc.sala.nome,
                    "matriz_id": aloc.quadro_aula_id,
                }
            )

        grade_config = current_app.config["GRADE_HORARIOS_FIXOS_POR_CATEGORIA"]
        periodo_map = current_app.config["PERIODO_MAP"]
        periodo_nome = periodo_map.get(str(turma.periodo))
        grade_da_turma = grade_config.get(turma.categoria, {}).get(periodo_nome, {})

        if not grade_da_turma:
            return (
                jsonify(
                    {
                        "error": f"Grade de horários não encontrada para a Categoria '{turma.categoria}' e Período '{periodo_nome}'. Verifique o cadastro da turma."
                    }
                ),
                404,
            )

        return jsonify(
            {
                "matriz_turma": matriz_turma,
                "horarios_alocados": horarios_alocados,
                "horarios_grade": grade_da_turma,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/admin/api/salas-disponiveis", methods=["POST"])
@login_required
def available_rooms():
    """Retorna uma lista de salas disponíveis para um dia e horário específicos."""
    data = request.get_json()
    dia = data["dia"]
    horario = data["horario"]

    salas_ocupadas_ids = [
        r[0]
        for r in db.session.query(HorarioAlocado.sala_id)
        .filter_by(dia_semana=dia, horario=horario)
        .all()
    ]
    salas_disponiveis = (
        Sala.query.filter(Sala.id.notin_(salas_ocupadas_ids)).order_by(Sala.nome).all()
    )

    return jsonify(
        {"available_rooms": [s.nome for s in salas_disponiveis]}
    )  # Retorna o nome da sala


@bp.route("/admin/api/alocar", methods=["POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def admin_api_alocar():
    data = request.get_json()
    dia = data.get("dia")
    horario = data.get("horario")
    matriz_id = data.get("matriz_id")
    sala_nome = data.get("sala")

    try:
        quadro_aula = QuadroDeAulas.query.get_or_404(matriz_id)
        sala = Sala.query.filter_by(nome=sala_nome).first_or_404()
        professor_id = quadro_aula.professor_id

        # --- VALIDAÇÃO DE CONFLITO DE PROFESSOR (NOVA LÓGICA) ---
        # Verifica se já existe alguma alocação para este professor, neste mesmo dia e horário.
        conflito_professor = (
            HorarioAlocado.query.join(QuadroDeAulas)
            .filter(
                HorarioAlocado.dia_semana == dia,
                HorarioAlocado.horario == horario,
                QuadroDeAulas.professor_id == professor_id,
            )
            .first()
        )

        # Se encontrar um conflito, retorna uma mensagem de erro clara.
        if conflito_professor:
            # Busca a turma do conflito para dar uma mensagem mais informativa
            conflito_turma_apelido = Turma.query.get(
                conflito_professor.quadro_aula.turma_id
            ).apelido
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Conflito de Professor! O(A) professor(a) {quadro_aula.professor.apelido} já está alocado na turma {conflito_turma_apelido} neste horário.",
                    }
                ),
                409,
            )  # Código HTTP 409 significa "Conflito"

        # --- VALIDAÇÃO DE CONFLITO DE SALA (LÓGICA EXISTENTE) ---
        # Esta parte do código já funcionava perfeitamente e foi mantida.
        conflito_sala = HorarioAlocado.query.filter_by(
            dia_semana=dia, horario=horario, sala_id=sala.id
        ).first()

        if conflito_sala:
            conflito_turma_apelido = Turma.query.get(
                conflito_sala.quadro_aula.turma_id
            ).apelido
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Conflito de Sala! A sala {sala.nome} já está sendo usada pela turma {conflito_turma_apelido} neste horário.",
                    }
                ),
                409,
            )

        # Se não houver conflitos, cria a nova alocação
        nova_alocacao = HorarioAlocado(
            quadro_aula_id=matriz_id, dia_semana=dia, horario=horario, sala_id=sala.id
        )
        db.session.add(nova_alocacao)
        db.session.commit()
        return jsonify({"status": "success", "message": "Aula alocada com sucesso!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/admin/api/remover", methods=["POST"])
@login_required
def admin_api_remover():
    """Remove uma alocação do banco de dados."""
    data = request.get_json()

    alocacao_para_remover = HorarioAlocado.query.filter_by(
        quadro_aula_id=data["matriz_id"],
        dia_semana=data["dia"],
        horario=data["horario"],
    ).first_or_404()

    db.session.delete(alocacao_para_remover)
    db.session.commit()

    return jsonify({"status": "success", "message": "Alocação removida com sucesso!"})


# =============================================================================
# ROTAS DE GERENCIAMENTO DA MATRIZ CURRICULAR (QUADRO DE AULAS)
# =============================================================================


@bp.route("/admin/matriz")
@login_required
@roles_required(["Full", "Supervisor"])
def matriz_curricular_list():
    """
    Lista a Matriz Curricular (Quadro de Aulas), agrupada por turma.
    """
    # --- CORREÇÃO APLICADA AQUI ---
    # Em vez de buscar a matriz diretamente, buscamos todas as TURMAS.
    # Usamos .options(joinedload(Turma.quadro_aulas)) para otimizar a consulta,
    # garantindo que as aulas de cada turma sejam carregadas de forma eficiente.
    # O template já sabe como usar 'turma.quadro_aulas' para exibir os dados.
    from sqlalchemy.orm import joinedload

    turmas = (
        Turma.query.options(joinedload(Turma.quadro_aulas)).order_by(Turma.nome).all()
    )

    # A variável agora se chama 'turmas', que é o que o template espera.
    return render_template("admin_matriz_curricular.html", turmas=turmas)


@bp.route("/admin/matriz/add", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def matriz_curricular_add():
    """Rota para adicionar uma nova entrada na matriz curricular."""
    if request.method == "POST":
        # Coleta os dados do formulário
        turma_id = request.form.get("turma_id")
        disciplina_id = request.form.get("disciplina_id")
        professor_id = request.form.get("professor_id")
        aulas_semanais = request.form.get("aulas_semanais")

        # Cria a nova entrada e salva no banco
        nova_entrada = QuadroDeAulas(
            turma_id=turma_id,
            disciplina_id=disciplina_id,
            professor_id=professor_id,
            aulas_semanais=aulas_semanais,
        )
        db.session.add(nova_entrada)
        db.session.commit()

        flash("Atribuição de aula adicionada à matriz com sucesso!", "success")
        return redirect(url_for("main.matriz_curricular_list"))

    # Para o GET, busca os dados para popular os menus do formulário
    turmas = Turma.query.order_by(Turma.nome).all()
    disciplinas = Disciplina.query.order_by(Disciplina.nome).all()
    professores = Professor.query.order_by(Professor.nome).all()

    return render_template(
        "admin_matriz_form.html",
        action="add",
        title="Adicionar Atribuição de Aula",
        turmas=turmas,
        disciplinas=disciplinas,
        professores=professores,
    )


@bp.route("/admin/matriz/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def matriz_curricular_edit(item_id):
    """
    Rota para editar uma entrada existente na Matriz Curricular (QuadroDeAulas).
    - GET: Exibe o formulário preenchido com os dados do item.
    - POST: Atualiza o item no banco de dados com as informações enviadas.
    """
    # 1. Busca o item específico no banco de dados pelo ID fornecido na URL.
    #    O .first_or_404() é uma conveniência do Flask-SQLAlchemy que automaticamente
    #    retorna um erro 404 (Não Encontrado) se nenhum item com esse ID existir.
    item_matriz = QuadroDeAulas.query.get_or_404(item_id)

    # 2. Se o método da requisição for POST, o usuário enviou o formulário.
    if request.method == "POST":
        try:
            # 3. Atualiza os campos do objeto 'item_matriz' com os dados do formulário.
            #    request.form.get() é usado para acessar os dados enviados.
            #    Convertemos os IDs para inteiros e a quantidade de aulas também.
            item_matriz.turma_id = int(request.form.get("turma_id"))
            item_matriz.disciplina_id = int(request.form.get("disciplina_id"))
            item_matriz.professor_id = int(request.form.get("professor_id"))
            item_matriz.aulas_semanais = int(request.form.get("aulas_semanais"))

            # 4. Confirma a transação no banco de dados.
            db.session.commit()
            flash("Item da matriz curricular atualizado com sucesso!", "success")

            # 5. Redireciona o usuário de volta para a lista principal.
            return redirect(url_for("main.matriz_curricular_list"))
        except Exception as e:
            # Em caso de erro, desfaz quaisquer alterações e informa o usuário.
            db.session.rollback()
            flash(f"Erro ao atualizar o item da matriz: {e}", "danger")

    # 6. Se o método for GET (o usuário acabou de clicar em "Editar"),
    #    precisamos buscar as listas de todas as turmas, disciplinas e professores
    #    para popular os menus <select> do formulário.
    turmas = Turma.query.order_by(Turma.nome).all()
    disciplinas = Disciplina.query.order_by(Disciplina.nome).all()
    professores = Professor.query.order_by(Professor.nome).all()

    # 7. Renderiza o mesmo template do formulário de adição, mas passa o 'item_matriz'
    #    que será usado para pré-preencher os campos.
    return render_template(
        "admin_matriz_form.html",
        title=f"Editar Item da Matriz",
        item=item_matriz,  # A variável 'item' será usada no template para preencher os valores
        turmas=turmas,
        disciplinas=disciplinas,
        professores=professores,
    )


@bp.route("/admin/matriz/delete/<int:item_id>", methods=["POST"])
@login_required
@roles_required(["Full"])
def matriz_curricular_delete(item_id):
    """Deleta uma entrada da matriz curricular."""
    entrada = QuadroDeAulas.query.get_or_404(item_id)
    db.session.delete(entrada)
    db.session.commit()
    flash("Atribuição de aula removida com sucesso.", "success")
    return redirect(url_for("main.matriz_curricular_list"))


@bp.route("/admin/reposicao")
@login_required
@roles_required(["Full", "Supervisor", "User"])
def admin_reposicao():
    turmas = Turma.query.order_by(Turma.nome).all()
    sabados = SabadoLetivo.query.order_by(SabadoLetivo.id).all()
    return render_template("admin_reposicao.html", turmas=turmas, sabados=sabados)


@bp.route("/admin/reposicao/add-sabado", methods=["POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def reposicao_add_sabado():
    """Cria um novo registro de Sábado Letivo."""
    sabado_id = request.form.get("sabado_id")
    if SabadoLetivo.query.get(sabado_id):
        flash("Este sábado letivo já foi cadastrado.", "danger")
        return redirect(url_for("main.admin_reposicao"))

    # Processa os horários customizados
    apelidos = request.form.getlist("apelido[]")
    inicios = request.form.getlist("inicio[]")
    fins = request.form.getlist("fim[]")
    grade_customizada = {
        f"{i}-{f}": a for a, i, f in zip(apelidos, inicios, fins) if a and i and f
    }

    if not grade_customizada:
        flash("É necessário definir pelo menos um horário para o sábado.", "warning")
        return redirect(url_for("main.admin_reposicao"))

    novo_sabado = SabadoLetivo(
        id=sabado_id,
        descricao=request.form.get("descricao"),
        grade_horarios=grade_customizada,
    )
    db.session.add(novo_sabado)
    db.session.commit()
    flash("Sábado letivo criado com sucesso!", "success")
    return redirect(url_for("main.admin_reposicao"))


# Rota da API para alocar aula de reposição
@bp.route("/admin/api/alocar_reposicao", methods=["POST"])
@login_required
def alocar_reposicao():
    data = request.get_json()
    try:
        nova_aula = Horario(
            quadro_aula_id=data["matriz_id"],
            turma_id=data["turma_id"],
            dia=data["dia"],
            horario=data["horario"],
            sala_id=Sala.query.filter_by(nome=data["sala"]).first().id,
            sabado_letivo_id=data["sabado_id"],
        )
        db.session.add(nova_aula)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# Rota da API para remover aula de reposição
@bp.route("/admin/api/remover_reposicao", methods=["POST"])
@login_required
def remover_reposicao():
    data = request.get_json()
    try:
        aula = Horario.query.filter_by(
            quadro_aula_id=data["matriz_id"],
            dia=data["dia"],
            horario=data["horario"],
            sabado_letivo_id=data["sabado_id"],
        ).first()

        if aula:
            db.session.delete(aula)
            db.session.commit()
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "message": "Aula não encontrada."}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# --- ROTAS DE API PARA A PÁGINA DE REPOSIÇÃO ---
# Rota da API de dados de reposição (outro exemplo de correção)
@bp.route("/admin/api/dados_reposicao/<string:sabado_id>/<int:turma_id>")
@login_required
def dados_reposicao(sabado_id, turma_id):
    try:
        turma = Turma.query.get_or_404(turma_id)
        sabado = SabadoLetivo.query.get_or_404(sabado_id)

        matriz_turma = QuadroDeAulas.query.filter_by(turma_id=turma.id).all()
        horarios_grade = sabado.grade_horarios
        aulas_alocadas = (
            ReposicaoAlocada.query.filter_by(sabado_id=sabado.id)
            .join(QuadroDeAulas)
            .filter(QuadroDeAulas.turma_id == turma.id)
            .all()
        )

        horarios_alocados = {}
        for aula in aulas_alocadas:
            dia = "sabado"
            if dia not in horarios_alocados:
                horarios_alocados[dia] = {}
            if aula.horario not in horarios_alocados[dia]:
                horarios_alocados[dia][aula.horario] = []

            horarios_alocados[dia][aula.horario].append(
                {
                    "disciplina": aula.quadro_aula.disciplina.sigla,
                    "professor": aula.quadro_aula.professor.apelido,
                    "sala": aula.sala.nome,
                    "matriz_id": aula.quadro_aula_id,
                }
            )

        matriz_com_alocadas = []
        for item in matriz_turma:
            total_alocadas = ReposicaoAlocada.query.filter_by(
                quadro_aula_id=item.id
            ).count()
            matriz_com_alocadas.append(
                {
                    "matriz_id": item.id,
                    "disciplina": item.disciplina.nome,
                    "sigla": item.disciplina.sigla,
                    "professor": item.professor.apelido,
                    "aulas_necessarias": item.aulas_semanais,
                    "alocadas": total_alocadas,
                    "origem": item.origem,
                }
            )

        return jsonify(
            {
                "matriz_turma": matriz_com_alocadas,
                "horarios_grade": horarios_grade,
                "horarios_alocados": horarios_alocados,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# Crie placeholders para as outras APIs para evitar BuildError
@bp.route("/admin/api/reposicao/alocar", methods=["POST"])
@login_required
def reposicao_api_alocar():
    """Cria uma nova alocação de reposição no banco de dados."""
    data = request.get_json()
    try:
        sala_obj = Sala.query.filter_by(nome=data["sala_nome"]).first_or_404()

        nova_alocacao = ReposicaoAlocada(
            sabado_id=data["sabado_id"],
            quadro_aula_id=data["matriz_id"],
            horario=data["horario"],
            sala_id=sala_obj.id,
        )
        db.session.add(nova_alocacao)
        db.session.commit()
        return jsonify(
            {"status": "success", "message": "Aula de reposição alocada com sucesso!"}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/admin/api/reposicao/remover", methods=["POST"])
@login_required
def reposicao_api_remover():
    """Remove uma alocação de reposição do banco de dados."""
    data = request.get_json()
    try:
        alocacao_para_remover = ReposicaoAlocada.query.filter_by(
            sabado_id=data["sabado_id"],
            quadro_aula_id=data["matriz_id"],
            horario=data["horario"],
        ).first_or_404()

        db.session.delete(alocacao_para_remover)
        db.session.commit()
        return jsonify(
            {"status": "success", "message": "Alocação removida com sucesso!"}
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/admin/api/reposicao/salas-disponiveis", methods=["POST"])
@login_required
def reposicao_available_rooms():
    """Retorna uma lista de salas disponíveis para um sábado e horário específicos."""
    data = request.get_json()
    sabado_id = data.get("sabado_id")
    horario = data.get("horario")

    # Encontra os IDs de todas as salas ocupadas naquele sábado e horário
    salas_ocupadas_ids = [
        r.sala_id
        for r in ReposicaoAlocada.query.filter_by(
            sabado_id=sabado_id, horario=horario
        ).all()
    ]

    # Busca todas as salas cujo ID não está na lista de ocupadas
    salas_disponiveis = (
        Sala.query.filter(Sala.id.notin_(salas_ocupadas_ids)).order_by(Sala.nome).all()
    )

    return jsonify({"available_rooms": [s.nome for s in salas_disponiveis]})


@bp.route("/admin/sabados-letivos")
@login_required
@roles_required(["Full", "Supervisor"])
def sabados_letivos_list():
    """
    Rota para listar, adicionar e gerenciar os Sábados Letivos.
    """
    sabados = SabadoLetivo.query.order_by(SabadoLetivo.id).all()
    return render_template("admin_sabados_letivos.html", sabados=sabados)


# Adicionar esta nova rota ao final do arquivo portal/routes.py
# Adicionar em portal/routes.py


@bp.route("/admin/sabados-letivos/add", methods=["POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def reposicao_add():
    """
    Processa o formulário para adicionar um novo Sábado Letivo e sua grade horária.
    """
    try:
        data = request.form
        data_sabado = data.get("id")
        descricao = data.get("descricao")
        apelidos = data.getlist("apelido[]")
        inicios = data.getlist("inicio[]")
        fins = data.getlist("fim[]")

        if not all([data_sabado, descricao, apelidos, inicios, fins]):
            flash("Todos os campos são obrigatórios.", "danger")
            return redirect(url_for("main.sabados_letivos_list"))

        # Monta a grade de horários a partir dos dados do formulário
        grade_horarios = {f"{i} - {f}": a for a, i, f in zip(apelidos, inicios, fins)}

        novo_sabado = SabadoLetivo(
            id=data_sabado, descricao=descricao, grade_horarios=grade_horarios
        )
        db.session.add(novo_sabado)
        db.session.commit()
        flash("Sábado Letivo cadastrado com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao cadastrar sábado letivo: {e}", "danger")

    return redirect(url_for("main.sabados_letivos_list"))


# Adicionar em portal/routes.py


@bp.route("/admin/sabados-letivos/delete/<path:sabado_id>", methods=["POST"])
@login_required
@roles_required(["Full"])
def reposicao_delete_sabado(sabado_id):
    """
    Processa a exclusão de um Sábado Letivo.
    """
    try:
        # Busca o sábado letivo no banco de dados pelo seu ID (a data)
        sabado_para_deletar = SabadoLetivo.query.get(sabado_id)

        if sabado_para_deletar:
            # Apaga o registro do banco
            db.session.delete(sabado_para_deletar)
            db.session.commit()
            flash("Sábado Letivo removido com sucesso!", "success")
        else:
            flash("Sábado Letivo não encontrado.", "warning")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao remover sábado letivo: {e}", "danger")

    # Redireciona de volta para a lista de sábados
    return redirect(url_for("main.sabados_letivos_list"))


@bp.route("/admin/sabados-letivos/importar-pdf", methods=["POST"])
@login_required
@roles_required(["Full"])
def importar_calendario_pdf():
    """
    Processa o upload de um PDF de calendário escolar, extrai os sábados letivos
    e os adiciona ao banco de dados.
    """
    file = request.files.get("pdf_file")
    if not file or not file.filename.endswith(".pdf"):
        flash("Arquivo inválido. Por favor, envie um arquivo .pdf", "danger")
        return redirect(url_for("main.sabados_letivos_list"))

    try:
        reader = PyPDF2.PdfReader(file.stream)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += page.extract_text()

        # Regex para encontrar as datas de sábados letivos no formato do calendário
        # Ex: "22-Sábado Letivo referente ao dia 05/03 (quarta-feira)"
        import re

        padrao = re.compile(r"(\d{2})-Sábado Letivo referente ao dia (\d{2}\/\d{2})")

        sabados_encontrados = padrao.findall(texto_completo)

        if not sabados_encontrados:
            flash(
                "Nenhum sábado letivo encontrado no formato esperado dentro do PDF.",
                "warning",
            )
            return redirect(url_for("main.sabados_letivos_list"))

        # Mapeamento de meses para números (para construir a data correta)
        # Esta parte é um pouco mais complexa pois o PDF não informa o mês em cada linha
        # Vamos ter que "adivinhar" o mês com base na ordem que aparecem.
        # (Isso pode ser melhorado no futuro se o formato do PDF mudar)

        # Simplesmente adicionamos os sábados com uma descrição padrão
        count_adicionados = 0
        for dia, ref_dia_mes in sabados_encontrados:
            # Como não temos o ano/mês fácil, vamos criar uma descrição clara
            descricao = f"Reposição do dia {ref_dia_mes}"

            # Precisamos construir a data do sábado. Vamos assumir 2025 por enquanto.
            # Esta parte é uma simplificação.
            # O ideal seria uma lógica mais robusta para identificar o mês.

            # Por enquanto, vamos pedir ao usuário para preencher a data completa.
            # Apenas usaremos a descrição extraída.

            # Simplificação: Vamos apenas extrair as descrições para o usuário ver
            # e ele preenche o resto. A automação completa da data é mais complexa.

        flash(
            f"Extração preliminar: {len(sabados_encontrados)} sábados letivos encontrados no PDF. Funcionalidade de cadastro automático em desenvolvimento.",
            "info",
        )

    except Exception as e:
        flash(f"Ocorreu um erro ao processar o PDF: {e}", "danger")

    return redirect(url_for("main.sabados_letivos_list"))


@bp.route("/admin/professores/importar-disponibilidade-json", methods=["POST"])
@login_required
@roles_required(["Full", "Supervisor"])
def importar_disponibilidade_json():
    file = request.files.get("json_file")
    if not file or not file.filename.endswith(".json"):
        flash("Arquivo inválido. Por favor, envie um arquivo .json", "danger")
        return redirect(url_for("main.dashboard"))

    try:
        # Lê o conteúdo do arquivo JSON
        data = json.load(file.stream)

        professores_atualizados = []
        professores_nao_encontrados = []

        # Zera a disponibilidade de todos os professores antes de começar
        for p in Professor.query.all():
            p.disponibilidade = {}

        # --- CORREÇÃO APLICADA AQUI ---
        # A iteração agora é feita usando .items(), que nos dá acesso tanto à chave (nome do professor)
        # quanto ao valor (o objeto de disponibilidade) em cada passo do loop.
        for nome_professor_json, disponibilidade_data in data.items():

            nome_professor_json = nome_professor_json.strip()
            if not nome_professor_json:
                continue

            # Procura o professor no banco de dados pelo nome
            professor = Professor.query.filter(
                func.lower(Professor.nome) == func.lower(nome_professor_json)
            ).first()

            if professor:
                # Se encontrou, agora precisamos "traduzir" o JSON para o formato do nosso banco
                nova_disponibilidade = {}
                mapa_dias = {
                    "2ª": "segunda-feira",
                    "3ª": "terca-feira",
                    "4ª": "quarta-feira",
                    "5ª": "quinta-feira",
                    "6ª": "sexta-feira",
                }
                grade_config = current_app.config["GRADE_HORARIOS_FIXOS_POR_CATEGORIA"][
                    "Ensino Médio"
                ]
                mapa_horarios = {
                    "Manhã": sorted(
                        [
                            h
                            for h, a in grade_config["Manhã"].items()
                            if "INTERVALO" not in a
                        ]
                    ),
                    "Tarde": sorted(
                        [
                            h
                            for h, a in grade_config["Tarde"].items()
                            if "INTERVALO" not in a
                        ]
                    ),
                    "Noite": sorted(
                        [
                            h
                            for h, a in grade_config["Noturno"].items()
                            if "INTERVALO" not in a
                        ]
                    ),
                }

                for periodo_json, dias_json in disponibilidade_data.items():
                    horarios_periodo = mapa_horarios.get(periodo_json)
                    if not horarios_periodo:
                        continue

                    for dia_json, aulas_json in dias_json.items():
                        dia_sistema = mapa_dias.get(dia_json)
                        if not dia_sistema:
                            continue

                        # O JSON marca com "X" a aula inteira, então marcamos todos os horários daquele período
                        if "X" in aulas_json:
                            for horario in horarios_periodo:
                                if dia_sistema not in nova_disponibilidade:
                                    nova_disponibilidade[dia_sistema] = {}
                                nova_disponibilidade[dia_sistema][
                                    horario
                                ] = "indisponivel"

                professor.disponibilidade = nova_disponibilidade
                professores_atualizados.append(professor.nome)
            else:
                # Se não encontrou, adiciona à lista de não encontrados
                professores_nao_encontrados.append(nome_professor_json)

        db.session.commit()

        flash(
            f"Importação via JSON concluída! {len(professores_atualizados)} professores tiveram a disponibilidade atualizada.",
            "success",
        )

        if professores_nao_encontrados:
            return render_template(
                "admin_import_report.html",
                title="Relatório de Importação de Disponibilidade (JSON)",
                nomes_nao_encontrados=sorted(list(set(professores_nao_encontrados))),
                nomes_no_banco=sorted([p.nome for p in Professor.query.all()]),
            )

    except json.JSONDecodeError:
        db.session.rollback()
        flash("Erro crítico: O arquivo enviado não é um JSON válido.", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Ocorreu um erro crítico durante a importação: {e}", "danger")

    return redirect(url_for("main.dashboard"))


# ========================================================================
# 6. ROTA PARA GERENCIAMENTO DE HORÁRIO POR TURMA
# ========================================================================
@bp.route("/admin/horarios", methods=["GET"])
@login_required
@roles_required(["admin", "Full", "Supervisor"])
def gerenciar_horarios():
    """
    Página principal para o gerenciamento de horários.
    Exibe uma lista de todas as turmas para que o usuário selecione qual gerenciar.
    """
    # 1. Busca todas as turmas cadastradas, ordenadas por nome.
    turmas = Turma.query.order_by(Turma.nome).all()

    # 2. Renderiza um NOVO template, que será a nossa página principal de gerenciamento.
    #    Passamos a lista de turmas para que ela possa ser exibida no menu lateral.
    return render_template(
        "admin_gerenciar_horarios.html", title="Gerenciar Horários", turmas=turmas
    )


@bp.route("/api/horario/turma/<int:turma_id>")
@login_required
@roles_required(["admin", "Full", "Supervisor"])
def api_get_horario_turma(turma_id):
    """
    Endpoint de API que retorna o HTML da grade de horários de uma turma,
    buscando a estrutura de horários da nova tabela GradeHorario.
    """
    turma = Turma.query.get_or_404(turma_id)

    # 1. Acessamos o mapa de períodos diretamente do config.
    periodo_map = current_app.config["PERIODO_MAP"]
    # 2. Traduzimos o número do período (turma.periodo) para o nome (ex: "Manhã").
    periodo_nome = periodo_map.get(turma.periodo, "Desconhecido")

    # 3. Usamos o nome do período na nossa busca no banco de dados.
    horarios_da_grade = (
        GradeHorario.query.filter_by(categoria=turma.categoria, periodo=periodo_nome)
        .order_by(GradeHorario.inicio)
        .all()
    )

    # 3. A lógica para buscar aulas já alocadas e a demanda da matriz continua a mesma.
    horarios_alocados = HorarioAlocado.query.filter_by(turma_id=turma.id).all()
    grade_alocada = {f"{h.dia_semana}-{h.horario}": h for h in horarios_alocados}

    demanda_aulas = QuadroDeAulas.query.filter_by(turma_id=turma.id).all()

    # 4. Renderiza o template parcial, passando a nova lista de horários vinda do banco.
    return render_template(
        "_admin_horario_turma_partial.html",
        turma=turma,
        grade_alocada=grade_alocada,
        demanda_aulas=demanda_aulas,
        horarios_da_grade=horarios_da_grade,  # Usando a nova variável
    )


@bp.route("/admin/executar-migracao-horarios")
@login_required
@roles_required(["admin", "Full", "Supervisor"])
def migrar_horarios_para_db_reestruturado():
    """
    Rota temporária e robusta para migrar os horários do config.py.
    Ela agora ignora duplicatas encontradas nos dados de origem.
    """
    # 1. Continua verificando se a tabela já tem dados para não rodar duas vezes.
    if GradeHorario.query.first():
        flash(
            "A migração de horários para o banco de dados já foi realizada anteriormente.",
            "warning",
        )
        return redirect(url_for("main.dashboard"))

    try:
        grade_fixa = current_app.config["GRADE_HORARIOS_FIXOS_POR_CATEGORIA"]
        novos_horarios = []
        # 2. INTELIGÊNCIA NOVA: Usamos um "set" para guardar as combinações que já processamos.
        combinacoes_adicionadas = set()

        for categoria, periodos in grade_fixa.items():
            for periodo, horarios in periodos.items():
                for horario_str, apelido in horarios.items():
                    # 3. Criamos uma chave única para verificar se já vimos essa combinação.
                    chave_unica = (categoria, periodo, apelido)

                    # 4. Se a combinação for nova, nós a processamos. Se for duplicata, ignoramos.
                    if chave_unica not in combinacoes_adicionadas:
                        inicio, fim = horario_str.split(" - ")
                        novo_horario = GradeHorario(
                            categoria=categoria,
                            periodo=periodo,
                            apelido=apelido,
                            inicio=inicio,
                            fim=fim,
                        )
                        novos_horarios.append(novo_horario)
                        # 5. Adicionamos a combinação ao nosso controle para não processá-la de novo.
                        combinacoes_adicionadas.add(chave_unica)

        if novos_horarios:
            db.session.bulk_save_objects(novos_horarios)
            db.session.commit()
            flash(
                f"{len(novos_horarios)} registros de horários únicos foram migrados com sucesso!",
                "success",
            )
        else:
            flash("Nenhum horário encontrado para migrar.", "info")

    except Exception as e:
        db.session.rollback()
        flash(f"Ocorreu um erro durante a migração: {e}", "danger")

    return redirect(url_for("main.dashboard"))


@bp.route("/admin/migrar-horarios")
@login_required
@roles_required(["admin", "Full", "Supervisor"])
def migrar_horarios_para_db():
    """
    Rota temporária para migrar os horários do config.py para a nova tabela.
    Acessar uma vez e depois remover.
    """
    try:
        turmas = Turma.query.all()
        grade_fixa = current_app.config["GRADE_HORARIOS_FIXOS_POR_CATEGORIA"]

        for turma in turmas:
            # Verifica se a turma já tem horários para não duplicar
            if GradeHorario.query.filter_by(turma_id=turma.id).first():
                continue  # Pula para a próxima turma

            # Lógica para encontrar a grade correta para a turma
            categoria = (
                turma.categoria if turma.categoria in grade_fixa else "Ensino Médio"
            )
            periodo = turma.get_periodo_nome()

            if periodo in grade_fixa[categoria]:
                horarios_da_turma = grade_fixa[categoria][periodo]

                for horario_str, apelido in horarios_da_turma.items():
                    inicio, fim = horario_str.split(" - ")
                    novo_horario = GradeHorario(
                        turma_id=turma.id,
                        periodo=periodo,
                        apelido=apelido,
                        inicio=inicio,
                        fim=fim,
                    )
                    db.session.add(novo_horario)

        db.session.commit()
        flash("Migração de horários concluída com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Erro na migração: {e}", "danger")

    return redirect(url_for("main.dashboard"))

# ========================================================================
# 8. ROTAS PARA ESTRUTURA ESCOLAR (Categorias, Períodos, Grades)
# ========================================================================

@bp.route('/admin/estrutura')
@login_required
@roles_required(['admin', 'Full', 'Supervisor'])
def admin_estrutura():
    """
    Renderiza a página principal para gerenciar a estrutura da escola.
    """
    return render_template('admin_estrutura.html', title="Estrutura Escolar")


@bp.route('/api/estrutura/categorias')
@login_required
@roles_required(['admin', 'Full', 'Supervisor'])
def api_get_categorias():
    """
    API que retorna o HTML da lista de categorias para gerenciamento.
    """
    # 1. Busca todas as categorias no banco de dados, ordenadas por nome.
    categorias = Categoria.query.order_by(Categoria.nome).all()
    
    # 2. Renderiza um novo template parcial, passando a lista de categorias.
    return render_template('_admin_categorias_partial.html', categorias=categorias)

