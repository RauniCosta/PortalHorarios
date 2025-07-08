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
from flask import Flask, Response, render_template, jsonify, request, redirect, url_for, flash, session
import io
import json
import os
import csv
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import locale
import threading
import uuid
from . import scheduler_engine 

# Função principal que cria a aplicação Flask (Application Factory)
def create_app(test_config=None):
    # =============================================================================
    # CONFIGURAÇÃO DA APLICAÇÃO
    # =============================================================================
    # Ajuste na criação do app para reconhecer a estrutura de pacote
    
    # Tenta configurar o local para Português do Brasil para obter nomes de dias da semana corretos
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
        except locale.Error:
            print("Aviso: Locale 'pt_BR' não encontrado. Nomes dos dias podem aparecer em inglês.")
    
    # Inicialização da aplicação Flask
    app = Flask(__name__, instance_relative_config=True)

    # Configurações padrão
    app.config.from_mapping(
        SECRET_KEY=os.getenv('FLASK_SECRET_KEY', '\sH(217SZD+>E57\Sf|Xskj<Z5u7/9rMW*mD.+bF^=z-OlSdt5'),
    )
    #app.secret_key = '\sH(217SZD+>E57\Sf|Xskj<Z5u7/9rMW*mD.+bF^=z-OlSdt5'
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, '..', 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Configuração do diretório para uploads de arquivos
    UPLOAD_FOLDER = 'uploads'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    
    # O DATA_FILE agora aponta para um nível acima, na raiz do projeto
    DATA_FILE = os.path.join(app.root_path, '..', 'dados.json')

    # =============================================================================
    # CONSTANTES E DADOS GLOBAIS (dentro da factory)
    # =============================================================================
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

    # =============================================================================
    # 3. FUNÇÕES DE MANIPULAÇÃO DE DADOS (JSON)
    # =============================================================================
    def carregar_dados():
        """
        Carrega os dados do arquivo JSON. Se o arquivo não existir ou estiver
        corrompido, cria uma estrutura de dados padrão com um usuário admin inicial.
        Garante que todas as chaves esperadas existam nos dados carregados.
        """
        default_data = {
            "turmas": [], "professores": [], "disciplinas": [], "matriz_curricular": [],
            "horarios_alocados": {}, "salas": [], "admin_users": [],
            "reposicao_sabado": []  # <-- ADICIONE ESTA LINHA
        }
        if not os.path.exists(DATA_FILE):
            hashed_password = generate_password_hash("admin")
            default_data['admin_users'] = [{"id": 1, "username": "admin", "password_hash": hashed_password, "role": "Full"}]
            return default_data

        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return default_data

        for key, value in default_data.items():
            data.setdefault(key, value)

        # O resto da função continua igual...
        if not data.get('admin_users'):
            hashed_password = generate_password_hash("admin")
            data['admin_users'] = [{"id": 1, "username": "admin", "password_hash": hashed_password, "role": "Full"}]
            salvar_dados(data)

        for user in data.get('admin_users', []):
            user.setdefault('role', 'User')

        return data

    def salvar_dados(dados):
        """
        Salva o dicionário de dados fornecido no arquivo JSON, garantindo uma
        formatação legível (indent=4) e o encoding correto.
        """
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)

    def validar_consistencia_dados():
        """
        Verifica a consistência dos dados, principalmente a carga horária vs. disponibilidade dos professores.
        
        Returns:
            dict: Um dicionário com o status da validação e uma lista de conflitos, se houver.
                Ex: {'status': 'conflito', 'conflitos': [...]} ou {'status': 'ok'}
        """
        dados = carregar_dados()
        professores = dados.get('professores', [])
        matriz = dados.get('matriz_curricular', [])
        
        lista_conflitos = []
        
        for professor in professores:
            prof_id = professor.get('id')
            
            total_aulas_atribuidas = sum(
                item.get('aulas_necessarias', 0) 
                for item in matriz if item.get('id_professor') == prof_id
            )
            
            disponibilidade = professor.get('disponibilidade', {})
            total_horarios_disponiveis = 0
            if disponibilidade:
                for dia, horarios in disponibilidade.items():
                    total_horarios_disponiveis += list(horarios.values()).count('disponivel')
            else:
                # Se não há registro, assume-se que não há horários disponíveis para alocação.
                total_horarios_disponiveis = 0

            if total_aulas_atribuidas > total_horarios_disponiveis:
                lista_conflitos.append({
                    "id": prof_id,
                    "nome": professor.get('nome', 'N/A'),
                    "aulas_atribuidas": total_aulas_atribuidas,
                    "horarios_disponiveis": total_horarios_disponiveis
                })

        if lista_conflitos:
            return {"status": "conflito", "conflitos": lista_conflitos}
        
        return {"status": "ok"}

    # =============================================================================
    # 4. DECORATORS DE AUTENTICAÇÃO E AUTORIZAÇÃO
    # =============================================================================
    def login_required(f):
        """
        Decorator que verifica se um usuário está logado. Se não, redireciona para o login.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Por favor, faça login para acessar esta página.', 'warning')
                return redirect(url_for('admin_login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function

    def roles_required(required_roles):
        """
        Decorator que verifica se o usuário logado tem uma das permissões ('roles') necessárias.
        """
        _required_roles = [required_roles] if isinstance(required_roles, str) else required_roles
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                user_role = session.get('user_role')
                if user_role not in _required_roles:
                    flash('Acesso negado. Você não tem permissão para este recurso.', 'error')
                    return redirect(url_for('admin_dashboard'))
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    # =============================================================================
    # 5. ROTAS PÚBLICAS E DE AUTENTICAÇÃO
    # =============================================================================
    @app.route('/')
    def index():
        return render_template('index.html', grade_horarios_fixos_por_categoria=GRADE_HORARIOS_FIXOS_POR_CATEGORIA)

    @app.route('/api/horarios')
    def get_horarios():
        return jsonify(carregar_dados())

    @app.route('/api/server_info')
    def get_server_info():
        """
        Fornece a hora atual do servidor, o dia da semana e o período correspondente.
        AGORA, ele também verifica se o dia atual é um sábado de reposição.
        """
        now = datetime.now()
        dia_semana_num = now.weekday() # Segunda é 0, Sábado é 5, Domingo é 6

        # Formatações padrão de data e hora
        data_formatada = now.strftime("%d/%m/%Y")
        hora_formatada = now.strftime("%H:%M:%S")
        dia_semana_display = now.strftime("%A").replace("-feira", "").capitalize()

        # Checagem especial para Sábados de Reposição
        if dia_semana_num == 5: # Se for Sábado
            dados = carregar_dados()
            hoje_id = now.strftime("%Y-%m-%d")
            sabado_letivo_config = next((s for s in dados.get('reposicao_sabado', []) if s.get('id') == hoje_id), None)
            
            if sabado_letivo_config:
                # É um sábado de reposição! Envia dados especiais.
                return jsonify({
                    'data': data_formatada,
                    'hora': hora_formatada,
                    'dia_key': 'sabado_letivo', # Chave especial
                    'dia_display': f"{sabado_letivo_config.get('descricao', 'Sábado Letivo')}, {data_formatada}",
                    'periodo_atual': 'Reposição', # Período especial
                    'is_reposicao': True,
                    'reposicao_info': sabado_letivo_config # Envia toda a configuração do sábado
                })

        # Lógica antiga para dias de semana normais
        current_hour = now.hour
        if 7 <= current_hour < 12:
            periodo = "Manhã"
        elif 12 <= current_hour < 18:
            periodo = "Tarde"
        elif 18 <= current_hour < 23:
            periodo = "Noturno"
        else:
            periodo = "Fora do Horário"
        
        dias_map = {0: 'segunda-feira', 1: 'terca-feira', 2: 'quarta-feira', 3: 'quinta-feira', 4: 'sexta-feira', 5: 'sabado', 6: 'domingo'}
        dia_semana_key = dias_map.get(dia_semana_num, 'domingo')

        return jsonify({
            'data': data_formatada,
            'hora': hora_formatada,
            'dia_key': dia_semana_key,
            'dia_display': f"{dia_semana_display}, {data_formatada}",
            'periodo_atual': periodo,
            'is_reposicao': False # Indica que não é um dia de reposição
        })


    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            dados = carregar_dados()
            user = next((u for u in dados.get('admin_users', []) if u['username'] == username), None)
            
            if user and check_password_hash(user.get('password_hash', ''), password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['user_role'] = user.get('role', 'User')
                flash('Login realizado com sucesso!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('admin_dashboard'))
            else:
                flash('Nome de usuário ou senha inválidos.', 'error')
        return render_template('admin_login.html')

    @app.route('/admin/logout')
    @login_required
    def admin_logout():
        session.clear()
        flash('Você foi desconectado.', 'info')
        return redirect(url_for('admin_login'))

    # =============================================================================
    # 6. ROTAS DO PAINEL DE ADMINISTRAÇÃO (DASHBOARD E IMPORTAÇÃO)
    # =============================================================================
    tasks = {}

    @app.route('/admin')
    @login_required
    def admin_dashboard():
        return render_template('admin_dashboard.html')

    # Adicione esta nova rota em qualquer lugar antes da seção de execução
    @app.route('/admin/download/template_csv')
    @login_required
    def download_template_csv():
        """
        Gera e serve um arquivo CSV de modelo para download, com a codificação correta.
        """
        # Cabeçalhos corretos para a importação
        headers = [
            "Turma", "Turma Apelido", "Período", "Categoria", 
            "Componente", "Sigla", "Qtde Aulas", "Origem", 
            "Professor Ministrando", "Professor Apelido"
        ]
        
        # Usa o módulo 'io' para criar o arquivo em memória
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        
        # Escreve o cabeçalho
        writer.writerow(headers)
        
        # Prepara o arquivo para ser enviado
        output.seek(0)
        
        # ***** AJUSTE PRINCIPAL AQUI *****
        # Codifica a saída para 'utf-8-sig', que inclui o BOM para o Excel.
        return Response(
            output.getvalue().encode('utf-8-sig'), # A mágica acontece aqui!
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=modelo_quadro_aulas.csv"}
        )

    @app.route('/admin/importar', methods=['POST'])
    @login_required
    @roles_required('Full')
    def importar_quadro_aulas_csv():
        file = request.files.get('csv_file')
        if not file or not file.filename.endswith('.csv'):
            flash('Formato de arquivo inválido. Por favor, envie um arquivo .csv', 'error')
            return redirect(url_for('admin_dashboard'))

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(filepath)

        novos_dados = {"turmas": [], "professores": [], "disciplinas": [], "matriz_curricular": []}
        lookup = {"turmas": {}, "professores": {}, "disciplinas": {}}
        next_id = {"turmas": 1, "professores": 1, "disciplinas": 1, "matriz": 1}
        summary, skipped_rows_details = {"processed": 0, "skipped": 0}, []
        
        try:
            with open(filepath, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for i, row in enumerate(reader, start=2):
                    apelido_turma = row.get("Turma Apelido","").strip()
                    componente = row.get("Componente","").strip()
                    prof_nome_completo = row.get("Professor Ministrando","").strip()
                    apelido_prof = row.get("Professor Apelido", "").strip()
                    periodo = row.get("Período","").strip()
                    cat = row.get("Categoria","").strip()
                    qtde_aulas_str = row.get("Qtde Aulas", "0").strip().replace(',', '.')
                    sigla_csv = row.get("Sigla", "").strip()
                    
                    if not all([apelido_turma, componente, prof_nome_completo, periodo, cat, qtde_aulas_str]):
                        skipped_rows_details.append({"line_number": i, "data": row, "reason": "Uma ou mais colunas essenciais estão vazias."})
                        summary["skipped"] += 1
                        continue

                    matriz_entry = {"aulas_necessarias": 0, "tipo_bloco": "Normal"}
                    is_valid_qtde = False
                    try:
                        qtde = float(qtde_aulas_str)
                        if cat == "Curso Técnico" and periodo == "3":
                            if qtde == 2.5: 
                                matriz_entry.update({"aulas_necessarias": 1, "tipo_bloco": "1º Bloco"})
                                is_valid_qtde = True
                            elif qtde == 5: 
                                matriz_entry.update({"aulas_necessarias": 1, "tipo_bloco": "2º Bloco"})
                                is_valid_qtde = True
                        elif qtde > 0:
                            matriz_entry.update({"aulas_necessarias": int(qtde)})
                            is_valid_qtde = True
                    except (ValueError, TypeError): pass

                    if not is_valid_qtde:
                        skipped_rows_details.append({"line_number": i, "data": row, "reason": f"Valor inválido para 'Qtde Aulas': {qtde_aulas_str}"})
                        summary["skipped"] += 1
                        continue
                    
                    summary["processed"] += 1
                    
                    if prof_nome_completo not in lookup["professores"]:
                        lookup["professores"][prof_nome_completo] = next_id["professores"]
                        if not apelido_prof:
                            apelido_prof = prof_nome_completo.split(' ')[0].capitalize()
                        novos_dados["professores"].append({"id": next_id["professores"], "nome": prof_nome_completo, "apelido": apelido_prof})
                        next_id["professores"] += 1
                    
                    if componente not in lookup["disciplinas"]:
                        lookup["disciplinas"][componente] = next_id["disciplinas"]
                        
                        # Usa a sigla do CSV, ou gera uma automaticamente se estiver vazia
                        sigla_final = sigla_csv if sigla_csv else componente[:3].upper()
                        
                        novos_dados["disciplinas"].append({
                            "id": next_id["disciplinas"], 
                            "componente": componente, 
                            "sigla": sigla_final
                        })
                        next_id["disciplinas"] += 1
                    
                    if apelido_turma not in lookup["turmas"]:
                        lookup["turmas"][apelido_turma] = next_id["turmas"]
                        novos_dados["turmas"].append({"id": next_id["turmas"], "nome_completo": row.get("Turma","").strip(), "apelido": apelido_turma, "periodo": periodo, "categoria": cat})
                        next_id["turmas"] += 1

                    matriz_entry.update({
                        "matriz_id": next_id["matriz"],
                        "id_turma": lookup["turmas"][apelido_turma],
                        "id_disciplina": lookup["disciplinas"][componente],
                        "id_professor": lookup["professores"][prof_nome_completo],
                        "origem": row.get("Origem","").strip()
                    })
                    novos_dados["matriz_curricular"].append(matriz_entry)
                    next_id["matriz"] += 1

                if summary["processed"] > 0:
                    dados_atuais = carregar_dados()
                    novos_dados["admin_users"] = dados_atuais.get("admin_users", [])
                    novos_dados["salas"] = dados_atuais.get("salas", [])
                    novos_dados["horarios_alocados"] = {}
                    novos_dados["reposicao_sabado"] = [] 
                    salvar_dados(novos_dados)
                    flash(f'Importação concluída: {summary["processed"]} registros processados, {summary["skipped"]} ignorados.', 'success')
                else:
                    flash('Nenhum registro válido encontrado no arquivo para importar.', 'warning')
                
                return render_template('admin_import_report.html', summary=summary, skipped_rows=skipped_rows_details)

        except Exception as e:
            flash(f'Ocorreu um erro crítico durante a importação: {str(e)}', 'error')
            return redirect(url_for('admin_dashboard'))
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def run_schedule_generation(task_id, app_context):
        """
        Função que executa em uma thread separada para não bloquear o servidor.
        """
        with app_context:
            try:
                print(f"Iniciando tarefa de geração de horário: {task_id}")
                dados = carregar_dados()
                
                # Chama o motor de geração
                resultados_brutos  = scheduler_engine.gerar_sugestao_horario(
                    dados,
                    GRADE_HORARIOS_FIXOS_POR_CATEGORIA,
                    PERIODO_MAP
                )
                
                if "error" in resultados_brutos :
                    tasks[task_id]['status'] = 'failed'
                    tasks[task_id]['result'] = resultados_brutos ['error']
                    print(f"Tarefa {task_id} falhou: {resultados_brutos ['error']}")
                else:
                    # Salva a sugestão no lugar correto em dados.json
                    sugestao_obj = {
                        "id": task_id,
                        "criado_em": datetime.now().isoformat(),
                        "gerado_por": session.get('username', 'sistema'),
                        "sugestao": resultados_brutos 
                    }
                    dados.setdefault('horarios_sugeridos', {})[task_id] = sugestao_obj
                    salvar_dados(dados)
                    
                    tasks[task_id]['status'] = 'completed'
                    print(f"Tarefa {task_id} concluída com sucesso.")

            except Exception as e:
                tasks[task_id]['status'] = 'failed'
                tasks[task_id]['result'] = f"Erro inesperado: {str(e)}"
                print(f"Tarefa {task_id} falhou com uma exceção: {str(e)}")

    @app.route('/admin/horarios/gerar', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def gerar_horario_automatico():
        task_id = str(uuid.uuid4())
        tasks[task_id] = {'status': 'running', 'result': None}
        
        # Inicia a geração em uma thread para não bloquear a requisição
        thread = threading.Thread(target=run_schedule_generation, args=(task_id, app.app_context()))
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'Geração de sugestão de horário iniciada.', 'task_id': task_id})

    # Adicione também a rota de status que já planejamos
    @app.route('/admin/horarios/status/<task_id>')
    @login_required
    def get_task_status(task_id):
        task = tasks.get(task_id, {})
        return jsonify({
            'status': task.get('status', 'not_found'),
            'result': task.get('result')
        })
    @app.route('/admin/sugestoes')
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def listar_sugestoes():
        dados = carregar_dados()
        sugestoes = dados.get('horarios_sugeridos', {})
        # Passa os valores do dicionário, que são os objetos de sugestão
        return render_template('admin_sugestoes_lista.html', sugestoes=list(sugestoes.values()))

    @app.route('/admin/sugestao/aprovar/<string:task_id>', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def aprovar_sugestao(task_id):
        dados = carregar_dados()
        sugestao_obj = dados.get('horarios_sugeridos', {}).get(task_id)

        if not sugestao_obj:
            flash('Sugestão não encontrada para aprovação.', 'error')
            return redirect(url_for('listar_sugestoes'))
            
        # O passo crítico: A alocação oficial é substituída pela sugestão
        dados['horarios_alocados'] = sugestao_obj['sugestao']
        
        # Remove a sugestão da lista de pendentes
        del dados['horarios_sugeridos'][task_id]
        
        salvar_dados(dados)
        flash('Grade de horários atualizada e publicada com sucesso!', 'success')
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/sugestao/visualizar/<string:task_id>')
    @login_required
    def visualizar_sugestao(task_id):
        dados = carregar_dados()
        sugestao_obj = dados.get('horarios_sugeridos', {}).get(task_id)

        if not sugestao_obj:
            return "Sugestão não encontrada", 404

        # Prepara um objeto de dados "falso" contendo apenas a sugestão como alocação principal
        dados_para_template = {
            "turmas": dados.get('turmas'),
            "horarios_alocados": sugestao_obj.get('sugestao', {}),
            "disciplinas": dados.get('disciplinas', [])
        }
        
        # Renderiza a página pública, mas com os dados da sugestão
        return render_template('index.html', 
                            grade_horarios_fixos_por_categoria=GRADE_HORARIOS_FIXOS_POR_CATEGORIA, 
                            dados_override=dados_para_template)

    @app.route('/admin/horarios/validar', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def validar_dados_api():
        """
        Endpoint da API que executa a validação de consistência dos dados.
        """
        resultado_validacao = validar_consistencia_dados()
        return jsonify(resultado_validacao)

    # =============================================================================
    # 7. ROTAS CRUD (CRIAR, LER, ATUALIZAR, DELETAR)
    # =============================================================================
    # --- Rotas para Visualização Genérica e Matriz ---
    @app.route('/admin/view/<string:data_key>')
    @login_required
    @roles_required(['Full', 'Supervisor', 'User'])
    def admin_view_data(data_key):
        dados = carregar_dados()
        title_map = {"turmas": "Turmas", "disciplinas": "Disciplinas", "professores": "Professores"}
        if data_key not in title_map and data_key != 'matriz':
            flash(f"A seção '{data_key}' não foi encontrada.", 'error')
            return redirect(url_for('admin_dashboard'))

        if data_key == 'matriz':
            return redirect(url_for('admin_view_matriz'))

        headers_map = {
            "turmas": [("ID","id"),("Nome Completo","nome_completo"),("Apelido","apelido"),("Período","periodo"),("Categoria","categoria")],
            "disciplinas": [("ID","id"),("Componente","componente"),("Sigla","sigla")],
            "professores": [("ID","id"),("Nome Completo","nome"), ("Apelido", "apelido")]
        }
        page_title = title_map.get(data_key)
        headers = [h[0] for h in headers_map.get(data_key, [])]
        
        if data_key == 'professores':
            for item in dados[data_key]:
                item.setdefault('apelido', '')

        rows = [{"id": item.get('id', 0), "data": [item.get(h[1], 'N/A') for h in headers_map.get(data_key, [])]} for item in dados[data_key]]
        return render_template('admin_view_data.html', title=page_title, headers=headers, rows=rows, data_key=data_key)

    @app.route('/admin/matriz')
    @login_required
    @roles_required(['Full', 'Supervisor', 'User'])
    def admin_view_matriz():
        dados = carregar_dados()
        turma_map = {t['id']: t for t in dados.get('turmas', [])}
        disciplina_map = {d['id']: d for d in dados.get('disciplinas', [])}
        professor_map = {p['id']: p for p in dados.get('professores', [])}
        
        matriz_detalhada = []
        for item in dados.get('matriz_curricular', []):
            matriz_detalhada.append({
                "turma": turma_map.get(item['id_turma'], {}).get('apelido', 'ID Inválido'),
                "disciplina": disciplina_map.get(item['id_disciplina'], {}).get('componente', 'ID Inválido'),
                "professor": professor_map.get(item['id_professor'], {}).get('nome', 'ID Inválido'),
                "qtde": item.get('aulas_necessarias', '?'),
                "origem": item.get('origem', '?')
            })
        
        headers = ["Turma", "Disciplina", "Professor", "Qtde Aulas", "Origem"]
        rows = [{'id': None, 'data': list(row.values())} for row in matriz_detalhada]
        return render_template('admin_view_data.html', title="Matriz Curricular Completa", headers=headers, rows=rows, data_key="matriz")

    # --- Rotas CRUD para Salas ---
    @app.route('/admin/salas')
    @login_required
    @roles_required(['Full', 'Supervisor', 'User'])
    def admin_salas():
        dados = carregar_dados()
        return render_template('admin_salas.html', salas=dados.get('salas', []))

    @app.route('/admin/salas/add', methods=['GET', 'POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def salas_add():
        if request.method == 'POST':
            dados = carregar_dados()
            new_id = max([s.get('id',0) for s in dados.get('salas', [])] + [0]) + 1
            dados.setdefault('salas', []).append({"id":new_id, "nome":request.form['nome']})
            salvar_dados(dados)
            flash('Sala adicionada com sucesso!', 'success')
            return redirect(url_for('admin_salas'))
        return render_template('admin_form.html', title="Adicionar Nova Sala", fields=[{'name':'nome','label':'Nome da Sala'}], item=None, form_action=url_for('salas_add'), cancel_url=url_for('admin_salas'))

    @app.route('/admin/salas/edit/<int:item_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def salas_edit(item_id):
        dados = carregar_dados()
        item = next((s for s in dados.get('salas', []) if s.get('id') == item_id), None)
        if not item:
            flash('Sala não encontrada.', 'error')
            return redirect(url_for('admin_salas'))

        if request.method == 'POST':
            nome_antigo = item.get('nome')
            nome_novo = request.form['nome'].strip()

            # Validação para evitar nomes duplicados
            outra_sala_com_nome = next((s for s in dados.get('salas', []) if s.get('nome') == nome_novo and s.get('id') != item_id), None)
            if outra_sala_com_nome:
                flash(f"Erro: O nome de sala '{nome_novo}' já está em uso.", 'error')
                return render_template('admin_form.html', title="Editar Sala", fields=[{'name':'nome','label':'Nome da Sala'}], item=request.form, form_action=url_for('salas_edit', item_id=item_id), cancel_url=url_for('admin_salas'))

            # Se o nome mudou, atualiza em todas as alocações existentes
            if nome_antigo != nome_novo:
                for turma, dias in dados.get('horarios_alocados', {}).items():
                    for dia, horarios in dias.items():
                        for horario, aulas in horarios.items():
                            for aula in aulas:
                                if aula.get('sala') == nome_antigo:
                                    aula['sala'] = nome_novo
            
            # Atualiza o nome da sala na lista principal e salva
            item['nome'] = nome_novo
            salvar_dados(dados)
            flash('Sala atualizada com sucesso e todas as alocações foram migradas.', 'success')
            return redirect(url_for('admin_salas'))

        return render_template('admin_form.html', title="Editar Sala", fields=[{'name':'nome','label':'Nome da Sala'}], item=item, form_action=url_for('salas_edit', item_id=item_id), cancel_url=url_for('admin_salas'))

    @app.route('/admin/salas/delete/<int:item_id>', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def salas_delete(item_id):
        dados = carregar_dados()
        sala_a_remover = next((s for s in dados.get('salas', []) if s.get('id') == item_id), None)
        if sala_a_remover:
            sala_nome = sala_a_remover['nome']
            dados['salas'] = [s for s in dados.get('salas', []) if s.get('id') != item_id]
            for turma_horarios in dados.get('horarios_alocados', {}).values():
                for dia_horarios in turma_horarios.values():
                    for horario, aulas in list(dia_horarios.items()):
                        dia_horarios[horario] = [a for a in aulas if a.get('sala') != sala_nome]
                        if not dia_horarios[horario]: del dia_horarios[horario]
            flash('Sala excluída e suas alocações foram removidas!', 'success')
            salvar_dados(dados)
        else:
            flash('Sala não encontrada.', 'error')
        return redirect(url_for('admin_salas'))

    # --- Rotas CRUD para Turmas ---
    @app.route('/admin/turmas/add', methods=['GET', 'POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def turmas_add():
        if request.method == 'POST':
            dados = carregar_dados()
            new_id = max([t.get('id', 0) for t in dados.get('turmas', [])] + [0]) + 1
            nova_turma = {
                "id": new_id,
                "nome_completo": request.form['nome_completo'],
                "apelido": request.form['apelido'],
                "periodo": request.form['periodo'],
                "categoria": request.form['categoria'],
                "local": request.form['local'] 
            }
            dados.setdefault('turmas', []).append(nova_turma)
            salvar_dados(dados)
            flash('Turma adicionada com sucesso!', 'success')
            return redirect(url_for('admin_view_data', data_key='turmas'))
        return render_template('admin_turma_form.html', title="Adicionar Turma", item=None, categorias=CATEGORIAS_CURSO, form_action=url_for('turmas_add'), cancel_url=url_for('admin_view_data', data_key='turmas'))

    @app.route('/admin/turmas/edit/<int:item_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def turmas_edit(item_id):
        dados = carregar_dados()
        item = next((t for t in dados.get('turmas', []) if t.get('id') == item_id), None)
        if not item:
            flash("Turma não encontrada.", "error")
            return redirect(url_for('admin_view_data', data_key='turmas'))

        if request.method == 'POST':
            apelido_antigo = item.get('apelido')
            apelido_novo = request.form.get('apelido', '').strip()

            # Validação para evitar apelidos duplicados em outras turmas
            outra_turma_com_apelido = next((t for t in dados.get('turmas', []) if t.get('apelido') == apelido_novo and t.get('id') != item_id), None)
            if outra_turma_com_apelido:
                flash(f"Erro: O apelido '{apelido_novo}' já está em uso pela turma '{outra_turma_com_apelido.get('nome_completo')}'.", 'error')
                item_para_form = request.form.to_dict()
                item_para_form['id'] = item_id
                return render_template('admin_turma_form.html', title="Editar Turma", item=item_para_form, categorias=CATEGORIAS_CURSO, form_action=url_for('turmas_edit', item_id=item_id), cancel_url=url_for('admin_view_data', data_key='turmas'))

            # Se o apelido mudou, atualiza a chave no dicionário de horários alocados
            if apelido_antigo and apelido_novo and apelido_antigo != apelido_novo and apelido_antigo in dados.get('horarios_alocados', {}):
                dados['horarios_alocados'][apelido_novo] = dados['horarios_alocados'].pop(apelido_antigo)
                
            # Atualiza os dados da turma na lista de turmas
            item.update({
                "nome_completo": request.form['nome_completo'],
                "apelido": apelido_novo,
                "periodo": request.form['periodo'],
                "categoria": request.form['categoria'],
                "local": request.form['local'] 
            })
            
            salvar_dados(dados)
            flash('Turma atualizada com sucesso! A rastreabilidade dos horários foi mantida.', 'success')
            return redirect(url_for('admin_view_data', data_key='turmas'))

        return render_template('admin_turma_form.html', title="Editar Turma", item=item, categorias=CATEGORIAS_CURSO, form_action=url_for('turmas_edit', item_id=item_id), cancel_url=url_for('admin_view_data', data_key='turmas'))

    @app.route('/admin/turmas/delete/<int:item_id>', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def turmas_delete(item_id):
        dados = carregar_dados()
        dados['turmas'] = [t for t in dados.get('turmas', []) if t.get('id') != item_id]
        dados['matriz_curricular'] = [m for m in dados.get('matriz_curricular', []) if m.get('id_turma') != item_id]
        salvar_dados(dados)
        flash('Turma e suas referências na matriz foram excluídas!', 'success')
        return redirect(url_for('admin_view_data', data_key='turmas'))

    # --- Rotas CRUD para Disciplinas ---
    @app.route('/admin/disciplinas/add', methods=['GET', 'POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def disciplinas_add():
        if request.method == 'POST':
            dados = carregar_dados()
            new_id = max([d.get('id', 0) for d in dados.get('disciplinas', [])] + [0]) + 1
            dados.setdefault('disciplinas', []).append({"id": new_id, "componente": request.form['componente'], "sigla": request.form['sigla']})
            salvar_dados(dados)
            flash('Disciplina adicionada com sucesso!', 'success')
            return redirect(url_for('admin_view_data', data_key='disciplinas'))
        fields = [{'name': 'componente', 'label': 'Componente'}, {'name': 'sigla', 'label': 'Sigla'}]
        return render_template('admin_form.html', title="Adicionar Disciplina", fields=fields, item=None, form_action=url_for('disciplinas_add'), cancel_url=url_for('admin_view_data', data_key='disciplinas'))

    @app.route('/admin/disciplinas/edit/<int:item_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def disciplinas_edit(item_id):
        dados = carregar_dados()
        item = next((d for d in dados.get('disciplinas', []) if d.get('id') == item_id), None)
        if not item:
            flash("Disciplina não encontrada.", "error")
            return redirect(url_for('admin_view_data', data_key='disciplinas'))
        if request.method == 'POST':
            item.update({"componente": request.form['componente'], "sigla": request.form['sigla']})
            salvar_dados(dados)
            flash('Disciplina atualizada com sucesso!', 'success')
            return redirect(url_for('admin_view_data', data_key='disciplinas'))
        fields = [{'name': 'componente', 'label': 'Componente'}, {'name': 'sigla', 'label': 'Sigla'}]
        return render_template('admin_form.html', title="Editar Disciplina", fields=fields, item=item, form_action=url_for('disciplinas_edit', item_id=item_id), cancel_url=url_for('admin_view_data', data_key='disciplinas'))

    @app.route('/admin/disciplinas/delete/<int:item_id>', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def disciplinas_delete(item_id):
        dados = carregar_dados()
        dados['disciplinas'] = [d for d in dados.get('disciplinas', []) if d.get('id') != item_id]
        dados['matriz_curricular'] = [m for m in dados.get('matriz_curricular', []) if m.get('id_disciplina') != item_id]
        salvar_dados(dados)
        flash('Disciplina e suas referências na matriz foram excluídas!', 'success')
        return redirect(url_for('admin_view_data', data_key='disciplinas'))

    # --- Rotas CRUD para Professores ---
    @app.route('/admin/professores/add', methods=['GET', 'POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def professores_add():
        if request.method == 'POST':
            dados = carregar_dados()
            new_id = max([p.get('id', 0) for p in dados.get('professores', [])] + [0]) + 1
            dados.setdefault('professores', []).append({
                "id": new_id, 
                "nome": request.form['nome'],
                "apelido": request.form['apelido']
            })
            salvar_dados(dados)
            flash('Professor adicionado com sucesso!', 'success')
            return redirect(url_for('admin_view_data', data_key='professores'))
        
        fields = [
            {'name': 'nome', 'label': 'Nome Completo'}, 
            {'name': 'apelido', 'label': 'Apelido'}
        ]
        return render_template('admin_form.html', title="Adicionar Professor", fields=fields, item=None, form_action=url_for('professores_add'), cancel_url=url_for('admin_view_data', data_key='professores'))

    @app.route('/admin/professores/edit/<int:item_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def professores_edit(item_id):
        dados = carregar_dados()
        item = next((p for p in dados.get('professores', []) if p.get('id') == item_id), None)
        if not item:
            flash("Professor não encontrado.", "error")
            return redirect(url_for('admin_view_data', data_key='professores'))
        
        if request.method == 'POST':
            item['nome'] = request.form['nome']
            item['apelido'] = request.form['apelido']
            salvar_dados(dados)
            flash('Professor atualizado com sucesso!', 'success')
            return redirect(url_for('admin_view_data', data_key='professores'))
        
        item.setdefault('apelido', '')
        fields = [
            {'name': 'nome', 'label': 'Nome Completo'}, 
            {'name': 'apelido', 'label': 'Apelido'}
        ]
        return render_template('admin_form.html', title="Editar Professor", fields=fields, item=item, form_action=url_for('professores_edit', item_id=item_id), cancel_url=url_for('admin_view_data', data_key='professores'))

    @app.route('/admin/professores/delete/<int:item_id>', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def professores_delete(item_id):
        dados = carregar_dados()
        dados['professores'] = [p for p in dados.get('professores', []) if p.get('id') != item_id]
        dados['matriz_curricular'] = [m for m in dados.get('matriz_curricular', []) if m.get('id_professor') != item_id]
        salvar_dados(dados)
        flash('Professor e suas referências na matriz foram excluídos!', 'success')
        return redirect(url_for('admin_view_data', data_key='professores'))

    @app.route('/admin/professores/disponibilidade/<int:prof_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required(['Full', 'Supervisor']) # Ou o role que definirmos para coordenador
    def professor_disponibilidade(prof_id):
        dados = carregar_dados()
        professor = next((p for p in dados.get('professores', []) if p.get('id') == prof_id), None)

        if not professor:
            flash('Professor não encontrado.', 'error')
            return redirect(url_for('admin_view_data', data_key='professores'))

        if request.method == 'POST':
            nova_disponibilidade = {}
            for key, status in request.form.items():
                if '|' in key:
                    dia, horario = key.split('|', 1)
                    if dia not in nova_disponibilidade:
                        nova_disponibilidade[dia] = {}
                    # Salva o status apenas se não for o padrão ('disponivel') para economizar espaço
                    if status != 'disponivel':
                        nova_disponibilidade[dia][horario] = status

            professor['disponibilidade'] = nova_disponibilidade
            salvar_dados(dados)
            flash(f'Disponibilidade do professor {professor["nome"]} atualizada com sucesso!', 'success')
            return redirect(url_for('admin_view_data', data_key='professores'))

        # Lógica para o método GET
        # Garante que a chave de disponibilidade exista no objeto do professor
        professor.setdefault('disponibilidade', {})
        
        # Cria uma lista mestre de todos os horários possíveis para exibir na grade
        todos_horarios = set()
        for categoria in GRADE_HORARIOS_FIXOS_POR_CATEGORIA.values():
            for periodo in categoria.values():
                for horario, apelido in periodo.items():
                    if apelido.upper() not in ["INTERVALO", "ALMOÇO"]:
                        todos_horarios.add(horario)
        
        # Ordena os horários para exibição consistente
        horarios_ordenados = sorted(list(todos_horarios))
        dias_semana = ['segunda-feira', 'terca-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira']

        return render_template('admin_professor_disponibilidade.html', 
                            professor=professor,
                            horarios=horarios_ordenados,
                            dias=dias_semana)

    # --- Rotas CRUD para Usuários ---
    @app.route('/admin/users')
    @login_required
    @roles_required('Full')
    def admin_users_list():
        dados = carregar_dados()
        return render_template('admin_users_list.html', users=dados.get('admin_users', []))
    
    @app.route('/admin/users/add', methods=['GET', 'POST'])
    @login_required
    @roles_required('Full')
    def admin_users_add():
        if request.method == 'POST':
            dados = carregar_dados()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')
            role = request.form.get('role')

            # --- Validações ---
            if not username or ' ' in username:
                flash('Nome de usuário é obrigatório e não pode conter espaços.', 'error')
            elif any(u['username'].lower() == username.lower() for u in dados.get('admin_users', [])):
                flash('Este nome de usuário já existe. Por favor, escolha outro.', 'error')
            elif len(password) < 8:
                flash('A senha deve ter no mínimo 8 caracteres.', 'error')
            elif password != password_confirm:
                flash('As senhas não coincidem.', 'error')
            else:
                # Se todas as validações passarem
                new_id = max([u.get('id', 0) for u in dados.get('admin_users', [])] + [0]) + 1
                dados.setdefault('admin_users', []).append({
                    "id": new_id, 
                    "username": username, 
                    "password_hash": generate_password_hash(password), 
                    "role": role
                })
                salvar_dados(dados)
                flash('Usuário adicionado com sucesso!', 'success')
                return redirect(url_for('admin_users_list'))
            
            # Se houver erro de validação, renderiza o formulário com os dados preenchidos
            return render_template('admin_user_form.html', title="Adicionar Usuário", user_data=request.form, roles=['Full', 'Supervisor', 'User'], form_action=url_for('admin_users_add'))
        
        return render_template('admin_user_form.html', title="Adicionar Usuário", user_data={}, roles=['Full', 'Supervisor', 'User'], form_action=url_for('admin_users_add'))

    @app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
    @login_required
    @roles_required('Full')
    def admin_users_edit(user_id):
        dados = carregar_dados()
        user = next((u for u in dados.get('admin_users', []) if u.get('id') == user_id), None)
        if not user:
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('admin_users_list'))

        if request.method == 'POST':
            new_username = request.form.get('username', '').strip()
            new_password = request.form.get('password', '')
            password_confirm = request.form.get('password_confirm', '')
            
            # --- Validações ---
            if not new_username or ' ' in new_username:
                flash('Nome de usuário é obrigatório e não pode conter espaços.', 'error')
            elif any(u['username'].lower() == new_username.lower() and u['id'] != user_id for u in dados.get('admin_users', [])):
                flash('Este nome de usuário já está em uso por outra conta.', 'error')
            elif new_password and len(new_password) < 8:
                flash('A nova senha deve ter no mínimo 8 caracteres.', 'error')
            elif new_password and new_password != password_confirm:
                flash('As novas senhas não coincidem.', 'error')
            else:
                # Se todas as validações passarem
                user['username'] = new_username
                user['role'] = request.form.get('role')
                if new_password:
                    user['password_hash'] = generate_password_hash(new_password)
                
                salvar_dados(dados)
                flash('Usuário atualizado com sucesso!', 'success')
                return redirect(url_for('admin_users_list'))

            # Se houver erro de validação, renderiza o formulário com os dados preenchidos
            return render_template('admin_user_form.html', title="Editar Usuário", user_data=user, roles=['Full', 'Supervisor', 'User'], form_action=url_for('admin_users_edit', user_id=user_id))

        return render_template('admin_user_form.html', title="Editar Usuário", user_data=user, roles=['Full', 'Supervisor', 'User'], form_action=url_for('admin_users_edit', user_id=user_id))

    @app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
    @login_required
    @roles_required('Full')
    def admin_users_delete(user_id):
        if user_id == session.get('user_id'):
            flash('Você não pode excluir sua própria conta.', 'error')
        else:
            dados = carregar_dados()
            user_to_delete = next((u for u in dados.get('admin_users', []) if u.get('id') == user_id), None)
            if user_to_delete:
                if user_to_delete.get('role') == 'Full' and sum(1 for u in dados.get('admin_users', []) if u.get('role') == 'Full') <= 1:
                    flash('Não é possível excluir o único administrador "Full".', 'error')
                else:
                    dados['admin_users'] = [u for u in dados.get('admin_users', []) if u.get('id') != user_id]
                    salvar_dados(dados)
                    flash('Usuário excluído com sucesso!', 'success')
            else:
                flash('Usuário não encontrado.', 'error')
        return redirect(url_for('admin_users_list'))

    # =============================================================================
    # 8. ROTAS E API PARA ALOCAÇÃO DE HORÁRIOS
    # =============================================================================
    @app.route('/admin/alocacao')
    @login_required
    @roles_required(['Full', 'Supervisor', 'User'])
    def admin_alocacao():
        dados = carregar_dados()
        turmas_ordenadas = sorted(dados.get('turmas', []), key=lambda t: t.get('nome_completo', ''))
        return render_template('admin_alocacao.html', turmas=turmas_ordenadas)

    @app.route('/admin/api/dados_alocacao/<string:turma_apelido>')
    @login_required
    @roles_required(['Full', 'Supervisor', 'User'])
    def get_dados_alocacao(turma_apelido):
        dados = carregar_dados()
        turma = next((t for t in dados.get('turmas', []) if t.get('apelido') == turma_apelido), None)
        if not turma: return jsonify({"error": "Turma não encontrada"}), 404

        periodo_str = str(turma.get('periodo', '1'))
        categoria = turma.get('categoria', 'Ensino Médio')
        
        periodo_nome = PERIODO_MAP.get(periodo_str, "Manhã")
        horarios_grade = GRADE_HORARIOS_FIXOS_POR_CATEGORIA.get(categoria, {}).get(periodo_nome, {})
        
        matriz_turma_raw = [item for item in dados.get('matriz_curricular', []) if item.get('id_turma') == turma.get('id')]
        disciplina_map = {d['id']: d for d in dados.get('disciplinas', [])}
        professor_map = {p['id']: p for p in dados.get('professores', [])} 
        horarios_alocados_turma = dados.get('horarios_alocados', {}).get(turma_apelido, {})

        alocadas_count = {}
        for dia_aulas in horarios_alocados_turma.values():
            for lista_aulas in dia_aulas.values():
                for aula in lista_aulas:
                    matriz_id = aula.get('matriz_id')
                    if matriz_id:
                        alocadas_count[matriz_id] = alocadas_count.get(matriz_id, 0) + 1
        
        matriz_turma_final = []
        for item in matriz_turma_raw:
            matriz_id = item.get('matriz_id')
            if not matriz_id: continue
            
            item_copy = item.copy()
            item_copy['disciplina'] = disciplina_map.get(item['id_disciplina'], {}).get('componente', 'N/A')
            professor_obj = professor_map.get(item['id_professor'], {})
            item_copy['professor'] = professor_obj.get('apelido') or professor_obj.get('nome', 'N/A').split(' ')[0]
            item_copy['alocadas'] = alocadas_count.get(matriz_id, 0)
            matriz_turma_final.append(item_copy)

        return jsonify({
            "matriz_turma": matriz_turma_final,
            "horarios_alocados": horarios_alocados_turma,
            "horarios_grade": horarios_grade
        })

    @app.route('/admin/api/available_rooms', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor', 'User'])
    def available_rooms():
        check_data = request.json
        dia, horario = check_data['dia'], check_data['horario']
        dados = carregar_dados()
        todas_as_salas = [sala['nome'] for sala in dados.get('salas', [])]
        salas_ocupadas = {aula['sala'] for t, dias in dados.get('horarios_alocados', {}).items() for d, h in dias.items() if d == dia for hr, aulas in h.items() if hr == horario for aula in aulas if 'sala' in aula}
        salas_disponiveis = sorted([sala for sala in todas_as_salas if sala not in salas_ocupadas])
        return jsonify({"available_rooms": salas_disponiveis})

    @app.route('/admin/api/alocar', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def admin_api_alocar():
        req = request.json
        dados = carregar_dados()
        turma_apelido, dia, horario, sala, matriz_id = req['turma_apelido'], req['dia'], req['horario'], req['sala'], req['matriz_id']
        
        matriz_item = next((m for m in dados.get('matriz_curricular', []) if m.get('matriz_id') == matriz_id), None)
        if not matriz_item:
            return jsonify({"status": "error", "message": "Item da matriz não encontrado."}), 404

        professor_id_para_alocar = matriz_item.get('id_professor')
        professor_info = next((p for p in dados.get('professores', []) if p.get('id') == professor_id_para_alocar), {})
        professor_apelido = professor_info.get('apelido') or professor_info.get('nome', 'Desconhecido').split(' ')[0]

        for t_apelido_existente, horarios_turma_existente in dados.get('horarios_alocados', {}).items():
            if dia in horarios_turma_existente and horario in horarios_turma_existente[dia]:
                for aula_existente in horarios_turma_existente[dia][horario]:
                    if aula_existente.get('sala') == sala:
                        return jsonify({"status": "error", "message": f"Conflito: Sala {sala} já ocupada pela turma '{t_apelido_existente}' neste horário."}), 409
                    
                    matriz_existente = next((m for m in dados.get('matriz_curricular', []) if m.get('matriz_id') == aula_existente.get('matriz_id')), None)
                    if matriz_existente and matriz_existente.get('id_professor') == professor_id_para_alocar:
                        return jsonify({"status": "error", "message": f"Conflito: Professor(a) {professor_apelido} já está alocado(a) para a turma '{t_apelido_existente}' neste horário."}), 409

        disciplina = next((d['componente'] for d in dados['disciplinas'] if d['id'] == matriz_item['id_disciplina']), "?")
        
        nova_aula = {"matriz_id": matriz_id, "disciplina": disciplina, "professor": professor_apelido, "sala": sala}
        
        dia_horarios = dados.get('horarios_alocados', {}).setdefault(turma_apelido, {}).setdefault(dia, {})
        dia_horarios.setdefault(horario, []).append(nova_aula)
        
        salvar_dados(dados)
        return jsonify({"status": "success", "message": "Aula alocada com sucesso!"})

    @app.route('/admin/api/remover', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def admin_api_remover():
        req = request.json
        dados = carregar_dados()
        turma_apelido, dia, horario, matriz_id = req['turma_apelido'], req['dia'], req['horario'], req['matriz_id']
        
        horarios_dia = dados.get('horarios_alocados', {}).get(turma_apelido, {}).get(dia, {})
        if horario in horarios_dia:
            lista_aulas = horarios_dia[horario]
            aula_para_remover = next((aula for aula in lista_aulas if aula.get('matriz_id') == matriz_id), None)
            
            if aula_para_remover:
                lista_aulas.remove(aula_para_remover)
                if not lista_aulas: del horarios_dia[horario]
                if not horarios_dia: del dados['horarios_alocados'][turma_apelido][dia]
                if not dados['horarios_alocados'][turma_apelido]: del dados['horarios_alocados'][turma_apelido]
                
                salvar_dados(dados)
                return jsonify({"status": "success", "message": "Aula removida."})
                
        return jsonify({"status": "error", "message": "Aula não encontrada para remover."})

    @app.route('/admin/clear_allocations', methods=['POST'])
    @login_required
    @roles_required('Full')
    def clear_allocations():
        """
        Rota para limpar todos os horários alocados no sistema.
        Preserva todos os outros dados (turmas, professores, etc.).
        """
        try:
            dados = carregar_dados()
            dados['horarios_alocados'] = {}  # Esvazia o dicionário de alocações
            salvar_dados(dados)
            flash('Todas as alocações de horários foram limpas com sucesso!', 'success')
        except Exception as e:
            flash(f'Ocorreu um erro ao tentar limpar as alocações: {str(e)}', 'error')
        
        return redirect(url_for('admin_dashboard'))

    # =============================================================================
    # 9. ROTAS E API PARA REPOSIÇÃO AOS SÁBADOS
    # =============================================================================
    @app.route('/admin/reposicao')
    @login_required
    @roles_required(['Full', 'Supervisor', 'User'])
    def admin_reposicao():
        """
        Renderiza a página de alocação para reposições de sábado.
        """
        dados = carregar_dados()
        sabados_letivos = sorted(dados.get('reposicao_sabado', []), key=lambda s: s.get('id'))
        # Por enquanto, focamos na alocação. Em um próximo passo, podemos criar
        # as telas para adicionar e editar os sábados letivos.
        # Se não houver sábados, podemos passar uma lista vazia para o template.
        return render_template('admin_reposicao.html', sabados_letivos=sabados_letivos)

    @app.route('/admin/api/dados_reposicao/<string:sabado_id>')
    @login_required
    @roles_required(['Full', 'Supervisor', 'User'])
    def get_dados_reposicao(sabado_id):
        """
        Fornece todos os dados necessários para alocar aulas em um sábado específico.
        """
        dados = carregar_dados()
        sabado_selecionado = next((s for s in dados.get('reposicao_sabado', []) if s.get('id') == sabado_id), None)

        if not sabado_selecionado:
            return jsonify({"error": "Sábado letivo não encontrado"}), 404

        # Precisamos de todas as turmas e da matriz curricular completa para a seleção
        turmas = dados.get('turmas', [])
        matriz_completa = dados.get('matriz_curricular', [])
        disciplina_map = {d['id']: d for d in dados.get('disciplinas', [])}
        professor_map = {p['id']: p for p in dados.get('professores', [])}

        # Contar aulas já alocadas neste sábado específico
        alocadas_count = {}
        for turma_horarios in sabado_selecionado.get('horarios_alocados', {}).values():
            for lista_aulas in turma_horarios.values():
                for aula in lista_aulas:
                    matriz_id = aula.get('matriz_id')
                    if matriz_id:
                        alocadas_count[matriz_id] = alocadas_count.get(matriz_id, 0) + 1

        # Montar a matriz curricular detalhada com contagem de alocadas
        matriz_final = []
        for item in matriz_completa:
            matriz_id = item.get('matriz_id')
            if not matriz_id: continue

            item_copy = item.copy()
            item_copy['disciplina'] = disciplina_map.get(item['id_disciplina'], {}).get('componente', 'N/A')
            item_copy['professor'] = professor_map.get(item['id_professor'], {}).get('nome', 'N/A')
            item_copy['alocadas'] = alocadas_count.get(matriz_id, 0)
            matriz_final.append(item_copy)

        return jsonify({
            "sabado_info": sabado_selecionado,
            "turmas": turmas,
            "matriz_curricular": matriz_final
        })
    
    @app.route('/admin/reposicao/add', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def reposicao_add_sabado():
        """
        Adiciona uma nova definição de sábado letivo.
        """
        dados = carregar_dados()
        sabado_id = request.form.get('sabado_id')
        descricao = request.form.get('descricao')

        if not sabado_id or not descricao:
            flash('Data e descrição são obrigatórias.', 'error')
            return redirect(url_for('admin_reposicao'))

        # Verifica se o sábado já existe
        if any(s['id'] == sabado_id for s in dados.get('reposicao_sabado', [])):
            flash(f'O sábado letivo na data {sabado_id} já existe.', 'error')
            return redirect(url_for('admin_reposicao'))

        # Pega os horários do formulário
        horarios_grade = {}
        apelidos = request.form.getlist('apelido[]')
        inicios = request.form.getlist('inicio[]')
        fins = request.form.getlist('fim[]')

        for i in range(len(apelidos)):
            if apelidos[i] and inicios[i] and fins[i]:
                chave_horario = f"{inicios[i]} - {fins[i]}"
                horarios_grade[chave_horario] = apelidos[i]

        if not horarios_grade:
            flash('É necessário definir pelo menos um horário para o sábado.', 'error')
            return redirect(url_for('admin_reposicao'))

        novo_sabado = {
            "id": sabado_id,
            "descricao": descricao,
            "grade_horarios": horarios_grade,
            "horarios_alocados": {}
        }
        
        dados.setdefault('reposicao_sabado', []).append(novo_sabado)
        salvar_dados(dados)
        flash('Sábado letivo adicionado com sucesso!', 'success')
        return redirect(url_for('admin_reposicao'))

    @app.route('/admin/reposicao/delete/<string:sabado_id>', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def reposicao_delete_sabado(sabado_id):
        """
        Remove uma definição de sábado letivo.
        """
        dados = carregar_dados()
        dados['reposicao_sabado'] = [s for s in dados.get('reposicao_sabado', []) if s.get('id') != sabado_id]
        salvar_dados(dados)
        flash('Sábado letivo removido com sucesso!', 'success')
        return redirect(url_for('admin_reposicao'))

    @app.route('/admin/api/reposicao/available_rooms', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor', 'User'])
    def reposicao_available_rooms():
        req = request.json
        sabado_id, horario = req['sabado_id'], req['horario']
        dados = carregar_dados()
        
        sabado_selecionado = next((s for s in dados.get('reposicao_sabado', []) if s.get('id') == sabado_id), None)
        if not sabado_selecionado:
            return jsonify({"available_rooms": []})

        todas_as_salas = [sala['nome'] for sala in dados.get('salas', [])]
        salas_ocupadas = {
            aula['sala']
            for turma, horarios in sabado_selecionado.get('horarios_alocados', {}).items()
            for h, aulas in horarios.items() if h == horario
            for aula in aulas if 'sala' in aula
        }
        salas_disponiveis = sorted([sala for sala in todas_as_salas if sala not in salas_ocupadas])
        return jsonify({"available_rooms": salas_disponiveis})

    @app.route('/admin/api/reposicao/alocar', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def reposicao_api_alocar():
        req = request.json
        dados = carregar_dados()
        sabado_id, turma_apelido, horario, sala, matriz_id = req['sabado_id'], req['turma_apelido'], req['horario'], req['sala'], req['matriz_id']
        
        sabado_obj = next((s for s in dados.get('reposicao_sabado', []) if s.get('id') == sabado_id), None)
        if not sabado_obj:
            return jsonify({"status": "error", "message": "Sábado letivo não encontrado."}), 404
        
        matriz_item = next((m for m in dados.get('matriz_curricular', []) if m.get('matriz_id') == matriz_id), None)
        if not matriz_item:
            return jsonify({"status": "error", "message": "Item da matriz não encontrado."}), 404

        professor_id = matriz_item.get('id_professor')
        professor_info = next((p for p in dados.get('professores', []) if p.get('id') == professor_id), {})
        professor_apelido = professor_info.get('apelido') or professor_info.get('nome', 'Desconhecido').split(' ')[0]

        horarios_sabado = sabado_obj.get('horarios_alocados', {})
        for t_apelido, t_horarios in horarios_sabado.items():
            if horario in t_horarios:
                for aula_existente in t_horarios[horario]:
                    if aula_existente.get('sala') == sala:
                        return jsonify({"status":"error", "message": f"Conflito: Sala {sala} já ocupada pela turma {t_apelido}."}), 409
                    
                    matriz_existente = next((m for m in dados.get('matriz_curricular', []) if m.get('matriz_id') == aula_existente.get('matriz_id')), None)
                    if matriz_existente and matriz_existente.get('id_professor') == professor_id:
                        return jsonify({"status":"error", "message": f"Conflito: Professor {professor_apelido} já alocado na turma {t_apelido}."}), 409

        disciplina = next((d['componente'] for d in dados['disciplinas'] if d['id'] == matriz_item['id_disciplina']), "?")
        
        nova_aula = {"matriz_id": matriz_id, "disciplina": disciplina, "professor": professor_apelido, "sala": sala}
        
        turma_horarios = horarios_sabado.setdefault(turma_apelido, {})
        turma_horarios.setdefault(horario, []).append(nova_aula)
        
        salvar_dados(dados)
        return jsonify({"status": "success", "message": "Aula alocada com sucesso!"})


    @app.route('/admin/api/reposicao/remover', methods=['POST'])
    @login_required
    @roles_required(['Full', 'Supervisor'])
    def reposicao_api_remover():
        req = request.json
        dados = carregar_dados()
        sabado_id, turma_apelido, horario, matriz_id = req['sabado_id'], req['turma_apelido'], req['horario'], int(req['matriz_id'])

        sabado_obj = next((s for s in dados.get('reposicao_sabado', []) if s.get('id') == sabado_id), None)
        if not sabado_obj:
            return jsonify({"status": "error", "message": "Sábado letivo não encontrado."}), 404
        
        horarios_turma = sabado_obj.get('horarios_alocados', {}).get(turma_apelido, {})
        if horario in horarios_turma:
            aulas_no_slot = horarios_turma[horario]
            aula_para_remover = next((a for a in aulas_no_slot if a.get('matriz_id') == matriz_id), None)
            
            if aula_para_remover:
                aulas_no_slot.remove(aula_para_remover)
                if not aulas_no_slot: del horarios_turma[horario]
                if not horarios_turma: del sabado_obj['horarios_alocados'][turma_apelido]
                
                salvar_dados(dados)
                return jsonify({"status": "success", "message": "Aula removida."})

        return jsonify({"status": "error", "message": "Aula não encontrada para remover."})
    
    return app