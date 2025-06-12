from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import json
import os
import csv
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATA_FILE = 'horarios_v2.json'

# --- CONSTANTES ---
GRADE_HORARIOS_FIXOS_POR_CATEGORIA = {
    "Ensino Médio": {"Manhã": {"07:10 - 08:00": "1º", "08:00 - 08:50": "2º", "08:50 - 09:40": "3º", "09:40 - 10:00": "INTERVALO", "10:00 - 10:50": "4º", "10:50 - 11:40": "5º", "11:40 - 12:30": "6º"}, "Tarde": {"12:40 - 13:30": "1º Tarde", "13:30 - 14:20": "2º Tarde", "14:20 - 15:10": "3º Tarde", "15:10 - 15:30": "INTERVALO", "15:30 - 16:20": "4º Tarde", "16:20 - 17:10": "5º Tarde", "17:10 - 18:00": "6º Tarde"}, "Noturno": {"16:20 - 17:10": "1º Noturno", "17:10 - 18:00": "2º Noturno", "18:00 - 18:20": "INTERVALO", "18:20 - 19:10": "3º Noturno", "19:10 - 20:00": "4º Noturno", "20:00 - 20:50": "5º Noturno", "20:50 - 21:05": "INTERVALO", "21:05 - 21:55": "6º Noturno", "21:55 - 22:45": "7º Noturno"}, "Integral": {"07:10 - 08:00": "1º", "08:00 - 08:50": "2º", "08:50 - 09:40": "3º", "09:40 - 10:00": "INTERVALO", "10:00 - 10:50": "4º", "10:50 - 11:40": "5º", "11:40 - 12:40": "Almoço", "12:40 - 13:30": "1º Tarde", "13:30 - 14:20": "2º Tarde", "14:20 - 15:10": "3º Tarde", "15:10 - 15:30": "INTERVALO"}},
    "Curso Técnico": {"Manhã": {"07:10 - 08:00": "1º", "08:00 - 08:50": "2º", "08:50 - 09:40": "3º", "09:40 - 10:00": "INTERVALO", "10:00 - 10:50": "4º", "10:50 - 11:40": "5º", "11:40 - 12:30": "6º"}, "Tarde": {"12:40 - 13:30": "1º Tarde", "13:30 - 14:20": "2º Tarde", "14:20 - 15:10": "3º Tarde", "15:10 - 15:30": "INTERVALO", "15:30 - 16:20": "4º Tarde", "16:20 - 17:10": "5º Tarde", "17:10 - 18:00": "6º Tarde"}, "Noturno": {"19:00 - 20:55": "1º Bloco", "20:55 - 21:05": "INTERVALO", "21:05 - 23:00": "2º Bloco"}}
}
PERIODO_MAP = {"1": "Manhã", "2": "Tarde", "3": "Noturno", "4": "Integral"}
CATEGORIAS_CURSO = ["Ensino Médio", "Curso Técnico"]

def carregar_dados():
    if not os.path.exists(DATA_FILE): return {"turmas": [], "professores": [], "disciplinas": [], "matriz_curricular": [], "horarios_alocados": {}, "salas": []}
    with open(DATA_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
    data.setdefault('salas', [])
    return data
def salvar_dados(dados):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(dados, f, indent=4, ensure_ascii=False)

@app.route('/')
def index(): return render_template('index.html', grade_horarios_fixos_por_categoria=GRADE_HORARIOS_FIXOS_POR_CATEGORIA)
@app.route('/api/horarios')
def get_horarios(): return jsonify(carregar_dados())
@app.route('/admin/api/salas')
def get_salas(): return jsonify({"salas": [s.get('nome') for s in carregar_dados().get("salas", [])]})

# --- ROTAS DE ADMIN ---
@app.route('/admin')
def admin_dashboard(): return render_template('admin_dashboard.html')

@app.route('/admin/importar', methods=['POST'])
def importar_quadro_aulas_csv():
    if 'csv_file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('admin_dashboard'))

    if file and file.filename.endswith('.csv'):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(filepath)
        
        novos_dados, lookup, next_id = {"turmas": [], "professores": [], "disciplinas": [], "matriz_curricular": []}, {"turmas": {}, "professores": {}, "disciplinas": {}}, {"turmas": 1, "professores": 1, "disciplinas": 1}
        summary = {"processed": 0, "skipped": 0}
        skipped_rows_details = []
        try:
            with open(filepath, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for i, row in enumerate(reader, start=2):
                    apelido_turma, componente, prof, periodo, cat = row.get("Turma Apelido","").strip(), row.get("Componente","").strip(), row.get("Professor Ministrando","").strip(), row.get("Período","").strip(), row.get("Categoria","").strip()
                    qtde_aulas_str = row.get("Qtde Aulas", "0").strip().replace(',', '.')
                    reason, is_valid_qtde = [], False
                    if not all([apelido_turma, componente, prof, periodo, cat]): reason.append("Campos essenciais vazios")
                    if reason:
                        summary["skipped"] += 1; skipped_rows_details.append({"line_number": i, "data": row, "reason": ", ".join(reason)}); continue
                    
                    matriz_entry = {"aulas_necessarias": 0, "tipo_bloco": "Normal"}
                    if cat == "Curso Técnico" and periodo == "3":
                        if qtde_aulas_str == "2.5": matriz_entry.update({"aulas_necessarias": 1, "tipo_bloco": "1º Bloco"}); is_valid_qtde = True
                        elif qtde_aulas_str == "5": matriz_entry.update({"aulas_necessarias": 1, "tipo_bloco": "2º Bloco"}); is_valid_qtde = True
                    else:
                        try:
                            qtde = float(qtde_aulas_str)
                            if qtde > 0: matriz_entry.update({"aulas_necessarias": int(qtde)}); is_valid_qtde = True
                        except (ValueError, TypeError): is_valid_qtde = False
                    
                    if not is_valid_qtde:
                        summary["skipped"] += 1; skipped_rows_details.append({"line_number": i, "data": row, "reason": f"Qtde Aulas ('{row.get('Qtde Aulas')}') inválida"}); continue
                    
                    summary["processed"] += 1
                    if prof not in lookup["professores"]:
                        prof_id = next_id["professores"]; lookup["professores"][prof] = prof_id; novos_dados["professores"].append({"id": prof_id, "nome": prof}); next_id["professores"] += 1
                    prof_id = lookup["professores"][prof]
                    if componente not in lookup["disciplinas"]:
                        disc_id = next_id["disciplinas"]; lookup["disciplinas"][componente] = disc_id; novos_dados["disciplinas"].append({"id": disc_id, "componente": componente, "sigla": componente[:3].upper()}); next_id["disciplinas"] += 1
                    disc_id = lookup["disciplinas"][componente]
                    if apelido_turma not in lookup["turmas"]:
                        turma_id = next_id["turmas"]; lookup["turmas"][apelido_turma] = turma_id; novos_dados["turmas"].append({"id": turma_id, "nome_completo": row.get("Turma","").strip(), "apelido": apelido_turma, "periodo": periodo, "categoria": cat}); next_id["turmas"] += 1
                    turma_id = lookup["turmas"][apelido_turma]
                    matriz_entry.update({"id_turma": turma_id, "id_disciplina": disc_id, "id_professor": prof_id, "origem": row.get("Origem","").strip()})
                    novos_dados["matriz_curricular"].append(matriz_entry)
            if summary["processed"] > 0:
                novos_dados["horarios_alocados"] = {}; salvar_dados(novos_dados)
            return render_template('admin_import_report.html', summary=summary, skipped_rows=skipped_rows_details)
        except Exception as e:
            flash(f'Ocorreu um erro crítico durante a importação: {e}', 'error'); return redirect(url_for('admin_dashboard'))
        finally:
            if os.path.exists(filepath): os.remove(filepath)
    else:
        # --- BLOCO CORRIGIDO ---
        # Adiciona o tratamento para arquivos com formato inválido
        flash('Formato de arquivo inválido. Por favor, envie um arquivo .csv', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/view/<string:data_key>')
def admin_view_data(data_key):
    dados = carregar_dados()
    title_map = {"turmas": "Turmas", "disciplinas": "Disciplinas", "professores": "Professores"}
    if data_key not in title_map: flash(f"A seção '{data_key}' não foi encontrada.", 'error'); return redirect(url_for('admin_dashboard'))
    headers_map = {
        "turmas": [("ID","id"),("Nome Completo","nome_completo"),("Apelido","apelido"),("Período","periodo"),("Categoria","categoria")],
        "disciplinas": [("ID","id"),("Componente","componente"),("Sigla","sigla")],
        "professores": [("ID","id"),("Nome","nome")]
    }
    page_title, headers = title_map.get(data_key), [h[0] for h in headers_map.get(data_key, [])]
    rows = [{"id": item.get('id', 0), "data": [item.get(h[1], 'N/A') for h in headers_map.get(data_key, [])]} for item in dados[data_key]]
    return render_template('admin_view_data.html', title=page_title, headers=headers, rows=rows, data_key=data_key)

# --- ROTA DA MATRIZ CURRICULAR (CORRIGIDA) ---
@app.route('/admin/matriz')
def admin_view_matriz():
    dados = carregar_dados()
    
    # Cria mapas para facilitar a busca de nomes a partir de IDs
    turma_map = {t['id']: t for t in dados.get('turmas', [])}
    disciplina_map = {d['id']: d for d in dados.get('disciplinas', [])}
    professor_map = {p['id']: p for p in dados.get('professores', [])}
    
    # Constrói uma lista detalhada para exibição
    matriz_detalhada = []
    for item in dados.get('matriz_curricular', []):
        matriz_detalhada.append({
            "turma": turma_map.get(item['id_turma'], {}).get('apelido', 'ID Inválido'),
            "disciplina": disciplina_map.get(item['id_disciplina'], {}).get('componente', 'ID Inválido'),
            "professor": professor_map.get(item['id_professor'], {}).get('nome', 'ID Inválido'),
            "qtde": item.get('aulas_necessarias', '?'), # Usa a chave correta
            "origem": item.get('origem', '?')
        })
    
    headers = ["Turma", "Disciplina", "Professor", "Qtde Aulas", "Origem"]
    # Prepara as linhas no formato que o template 'admin_view_data.html' espera
    rows = [{'id': None, 'data': list(row.values())} for row in matriz_detalhada]
    
    # Renderiza o template, passando os dados. Como add_url/edit_url não são passados, os botões não aparecerão.
    return render_template('admin_view_data.html', title="Matriz Curricular Completa", headers=headers, rows=rows)

# --- NOVAS ROTAS DE API PARA ALOCAÇÃO ---
@app.route('/admin/api/available_rooms', methods=['POST'])
def available_rooms():
    check_data = request.json
    dia, horario = check_data['dia'], check_data['horario']
    
    dados = carregar_dados()
    todas_as_salas = [sala['nome'] for sala in dados.get('salas', [])]
    
    salas_ocupadas = set()
    for turma, dias in dados.get('horarios_alocados', {}).items():
        if dia in dias and horario in dias[dia]:
            # Acessa a LISTA de aulas no horário
            lista_de_aulas = dias[dia][horario]
            # Itera sobre cada aula na lista
            for aula_alocada in lista_de_aulas:
                if 'sala' in aula_alocada:
                    salas_ocupadas.add(aula_alocada['sala'])
            
    salas_disponiveis = [sala for sala in todas_as_salas if sala not in salas_ocupadas]
    
    return jsonify({"available_rooms": sorted(salas_disponiveis)})

# --- ROTAS CRUD PARA TURMAS ---
@app.route('/admin/turmas/add', methods=['GET', 'POST'])
def turmas_add():
    if request.method == 'POST':
        dados = carregar_dados(); new_id = max([t.get('id',0) for t in dados['turmas']] + [0]) + 1
        dados['turmas'].append({"id":new_id, "nome_completo":request.form['nome_completo'], "apelido":request.form['apelido'], "periodo":request.form['periodo'], "categoria":request.form['categoria']})
        salvar_dados(dados); flash('Turma adicionada!', 'success'); return redirect(url_for('admin_view_data', data_key='turmas'))
    return render_template('admin_turma_form.html', title="Adicionar Turma", item=None, categorias=CATEGORIAS_CURSO, form_action=url_for('turmas_add'), cancel_url=url_for('admin_view_data', data_key='turmas'))

@app.route('/admin/turmas/edit/<int:item_id>', methods=['GET', 'POST'])
def turmas_edit(item_id):
    dados = carregar_dados()
    item = next((t for t in dados['turmas'] if t['id'] == item_id), None)
    if not item: return "Item não encontrado", 404
    if request.method == 'POST':
        item.update({"nome_completo":request.form['nome_completo'], "apelido":request.form['apelido'], "periodo":request.form['periodo'], "categoria":request.form['categoria']})
        salvar_dados(dados); flash('Turma atualizada!', 'success'); return redirect(url_for('admin_view_data', data_key='turmas'))
    return render_template('admin_turma_form.html', title="Editar Turma", item=item, categorias=CATEGORIAS_CURSO, form_action=url_for('turmas_edit', item_id=item_id), cancel_url=url_for('admin_view_data', data_key='turmas'))

@app.route('/admin/turmas/delete/<int:item_id>', methods=['POST'])
def turmas_delete(item_id):
    dados = carregar_dados(); dados['turmas'] = [t for t in dados['turmas'] if t['id'] != item_id]; dados['matriz_curricular'] = [m for m in dados['matriz_curricular'] if m['id_turma'] != item_id]; salvar_dados(dados)
    flash('Turma e referências excluídas!', 'success'); return redirect(url_for('admin_view_data', data_key='turmas'))

# --- ROTAS CRUD PARA DISCIPLINAS ---
@app.route('/admin/disciplinas/add', methods=['GET', 'POST'])
def disciplinas_add():
    if request.method == 'POST':
        dados, new_id = carregar_dados(), max([d.get('id',0) for d in dados['disciplinas']] + [0]) + 1
        dados['disciplinas'].append({"id":new_id, "componente":request.form['componente'], "sigla":request.form['sigla']}); salvar_dados(dados)
        flash('Disciplina adicionada!', 'success'); return redirect(url_for('admin_view_data', data_key='disciplinas'))
    return render_template('admin_form.html', title="Adicionar Disciplina", fields=[{'name':'componente','label':'Componente'},{'name':'sigla','label':'Sigla'}], item=None, form_action=url_for('disciplinas_add'), cancel_url=url_for('admin_view_data', data_key='disciplinas'))

@app.route('/admin/disciplinas/edit/<int:item_id>', methods=['GET', 'POST'])
def disciplinas_edit(item_id):
    dados = carregar_dados()
    item = next((d for d in dados['disciplinas'] if d['id'] == item_id), None)
    if not item: return "Item não encontrado", 404
    if request.method == 'POST':
        item.update({"componente":request.form['componente'], "sigla":request.form['sigla']}); salvar_dados(dados)
        flash('Disciplina atualizada!', 'success'); return redirect(url_for('admin_view_data', data_key='disciplinas'))
    return render_template('admin_form.html', title="Editar Disciplina", fields=[{'name':'componente','label':'Componente'},{'name':'sigla','label':'Sigla'}], item=item, form_action=url_for('disciplinas_edit', item_id=item_id), cancel_url=url_for('admin_view_data', data_key='disciplinas'))

@app.route('/admin/disciplinas/delete/<int:item_id>', methods=['POST'])
def disciplinas_delete(item_id):
    dados = carregar_dados(); dados['disciplinas'] = [d for d in dados['disciplinas'] if d['id'] != item_id]; dados['matriz_curricular'] = [m for m in dados['matriz_curricular'] if m['id_disciplina'] != item_id]; salvar_dados(dados)
    flash('Disciplina e referências excluídas!', 'success'); return redirect(url_for('admin_view_data', data_key='disciplinas'))

# --- ROTAS CRUD PARA PROFESSORES ---
@app.route('/admin/professores/add', methods=['GET', 'POST'])
def professores_add():
    if request.method == 'POST':
        dados, new_id = carregar_dados(), max([p.get('id',0) for p in dados['professores']] + [0]) + 1
        dados['professores'].append({"id":new_id, "nome":request.form['nome']}); salvar_dados(dados)
        flash('Professor adicionado!', 'success'); return redirect(url_for('admin_view_data', data_key='professores'))
    return render_template('admin_form.html', title="Adicionar Professor", fields=[{'name':'nome','label':'Nome'}], item=None, form_action=url_for('professores_add'), cancel_url=url_for('admin_view_data', data_key='professores'))

@app.route('/admin/professores/edit/<int:item_id>', methods=['GET', 'POST'])
def professores_edit(item_id):
    dados = carregar_dados()
    item = next((p for p in dados['professores'] if p['id'] == item_id), None)
    if not item: return "Item não encontrado", 404
    if request.method == 'POST':
        item.update({"nome":request.form['nome']}); salvar_dados(dados)
        flash('Professor atualizado!', 'success'); return redirect(url_for('admin_view_data', data_key='professores'))
    return render_template('admin_form.html', title="Editar Professor", fields=[{'name':'nome','label':'Nome'}], item=item, form_action=url_for('professores_edit', item_id=item_id), cancel_url=url_for('admin_view_data', data_key='professores'))

@app.route('/admin/professores/delete/<int:item_id>', methods=['POST'])
def professores_delete(item_id):
    dados = carregar_dados(); dados['professores'] = [p for p in dados['professores'] if p['id'] != item_id]; dados['matriz_curricular'] = [m for m in dados['matriz_curricular'] if m['id_professor'] != item_id]; salvar_dados(dados)
    flash('Professor e referências excluídos!', 'success'); return redirect(url_for('admin_view_data', data_key='professores'))

# --- ROTAS PARA ALOCAÇÃO DE HORÁRIOS ---
@app.route('/admin/alocacao')
def admin_alocacao():
    dados = carregar_dados()
    return render_template('admin_alocacao.html', turmas=dados['turmas'])

@app.route('/admin/api/dados_alocacao/<string:turma_apelido>')
def get_dados_alocacao(turma_apelido):
    dados = carregar_dados()
    turma = next((t for t in dados['turmas'] if t['apelido'] == turma_apelido), None)
    if not turma: return jsonify({"error": "Turma não encontrada"}), 404
    
    periodo_numerico = str(turma.get('periodo', '1'))
    periodo_nome = PERIODO_MAP.get(periodo_numerico, "Manhã")
    categoria = turma.get('categoria', 'Ensino Médio')
    horarios_grade = GRADE_HORARIOS_FIXOS_POR_CATEGORIA.get(categoria, {}).get(periodo_nome, {})
    
    turma_id = turma['id']
    matriz_turma = [item for item in dados['matriz_curricular'] if item['id_turma'] == turma_id]
    disciplina_map = {d['id']: d for d in dados['disciplinas']}
    professor_map = {p['id']: p for p in dados['professores']}

    for item in matriz_turma:
        item['disciplina'] = disciplina_map.get(item['id_disciplina'], {}).get('componente', 'N/A')
        item['professor'] = professor_map.get(item['id_professor'], {}).get('nome', 'N/A')
        item['id_matriz'] = f"{item['id_turma']}-{item['id_disciplina']}-{item['id_professor']}"

    horarios_alocados_turma = dados.get('horarios_alocados', {}).get(turma_apelido, {})
    for item in matriz_turma:
        count = 0
        for dia_aulas in horarios_alocados_turma.values():
            for lista_de_aulas_no_horario in dia_aulas.values():
                # Adiciona uma verificação para garantir que a lista é, de fato, uma lista
                if isinstance(lista_de_aulas_no_horario, list):
                    for aula_alocada in lista_de_aulas_no_horario:
                        # Adiciona uma verificação para garantir que a aula é um dicionário
                        if isinstance(aula_alocada, dict) and aula_alocada.get('id_matriz') == item['id_matriz']:
                            count += 1
        item['alocadas'] = count

    return jsonify({
        "matriz_turma": matriz_turma,
        "horarios_alocados": horarios_alocados_turma,
        "horarios_grade": horarios_grade
    })
    
# Rota dedicada para listar e gerenciar Salas
@app.route('/admin/salas')
def admin_salas():
    dados = carregar_dados()
    return render_template('admin_salas.html', salas=dados.get('salas', []))

# Adicionar Sala
@app.route('/admin/salas/add', methods=['GET', 'POST'])
def salas_add():
    if request.method == 'POST':
        dados = carregar_dados()
        new_id = max([s.get('id',0) for s in dados['salas']] + [0]) + 1
        dados['salas'].append({"id":new_id, "nome":request.form['nome']})
        salvar_dados(dados)
        flash('Sala adicionada com sucesso!', 'success')
        # Redirecionamento CORRETO para a lista de salas
        return redirect(url_for('admin_salas'))
    
    # Exibe o formulário de adição
    return render_template('admin_form.html', title="Adicionar Nova Sala", 
                           fields=[{'name':'nome','label':'Nome da Sala'}], 
                           item=None, 
                           form_action=url_for('salas_add'), 
                           cancel_url=url_for('admin_salas'))

# Editar Sala
@app.route('/admin/salas/edit/<int:item_id>', methods=['GET', 'POST'])
def salas_edit(item_id):
    dados = carregar_dados()
    item = next((s for s in dados['salas'] if s['id'] == item_id), None)
    if not item: return "Sala não encontrada", 404
    
    if request.method == 'POST':
        item['nome'] = request.form['nome']
        salvar_dados(dados)
        flash('Sala atualizada com sucesso!', 'success')
        return redirect(url_for('admin_salas'))
    
    return render_template('admin_form.html', title="Editar Sala", 
                           fields=[{'name':'nome','label':'Nome da Sala'}], 
                           item=item, 
                           form_action=url_for('salas_edit', item_id=item_id), 
                           cancel_url=url_for('admin_salas'))

# Excluir Sala
@app.route('/admin/salas/delete/<int:item_id>', methods=['POST'])
def salas_delete(item_id):
    dados = carregar_dados()
    sala_removida = next((s['nome'] for s in dados['salas'] if s['id'] == item_id), None)
    dados['salas'] = [s for s in dados['salas'] if s['id'] != item_id]
    if sala_removida:
        for turma, dias in dados.get('horarios_alocados', {}).items():
            for dia, horarios in dias.items():
                for horario, aula in list(horarios.items()):
                    if aula.get('sala') == sala_removida:
                        del dados['horarios_alocados'][turma][dia][horario]
    salvar_dados(dados)
    flash('Sala excluída e suas alocações foram removidas!', 'success')
    return redirect(url_for('admin_salas'))


# --- NOVA LÓGICA DE ALOCAÇÃO DE HORÁRIOS ---
@app.route('/admin/api/alocar', methods=['POST'])
def admin_api_alocar():
    req = request.json
    dados = carregar_dados()
    
    turma_proposta, dia_proposto, horario_proposto, sala_proposta = req['turma_apelido'], req['dia'], req['horario'], req['sala']

    # --- Verificação de Conflito de Sala (Atualizada para a nova estrutura) ---
    for turma_existente, dias in dados.get('horarios_alocados', {}).items():
        if dia_proposto in dias and horario_proposto in dias[dia_proposto]:
            # Itera sobre a LISTA de aulas naquele horário
            for aula_existente in dias[dia_proposto][horario_proposto]:
                if aula_existente.get('sala') == sala_proposta:
                    return jsonify({"status": "error", "message": f"Conflito: A sala '{sala_proposta}' já está sendo usada pela turma '{turma_existente}'."})

    # --- Lógica de Alocação (Atualizada para usar listas) ---
    id_t, id_d, id_p = map(int, req['id_matriz'].split('-'))
    disciplina = next((d['componente'] for d in dados['disciplinas'] if d['id'] == id_d), "?")
    professor = next((p['nome'] for p in dados['professores'] if p['id'] == id_p), "?")
    
    nova_aula = {
        "id_matriz": req['id_matriz'], 
        "disciplina": disciplina, 
        "professor": professor, 
        "sala": sala_proposta
    }

    # Garante que a estrutura exista e que o horário seja uma lista
    dia_horarios = dados['horarios_alocados'].setdefault(turma_proposta, {}).setdefault(dia_proposto, {})
    
    if horario_proposto not in dia_horarios:
        dia_horarios[horario_proposto] = [] # Se não existe, cria como uma lista vazia
    
    # Adiciona a nova aula à lista do horário
    dia_horarios[horario_proposto].append(nova_aula)
    
    salvar_dados(dados)
    return jsonify({"status": "success"})

@app.route('/admin/api/remover', methods=['POST'])
def admin_api_remover():
    req = request.json
    dados = carregar_dados()
    
    turma_apelido, dia, horario, id_matriz = req['turma_apelido'], req['dia'], req['horario'], req['id_matriz']
    
    # Verifica se o horário existe
    if horario in dados.get('horarios_alocados', {}).get(turma_apelido, {}).get(dia, {}):
        lista_aulas = dados['horarios_alocados'][turma_apelido][dia][horario]
        
        # Encontra e remove a aula específica da lista pelo id_matriz
        aula_para_remover = next((aula for aula in lista_aulas if aula['id_matriz'] == id_matriz), None)
        
        if aula_para_remover:
            lista_aulas.remove(aula_para_remover)
            # Se a lista ficar vazia, remove a chave do horário
            if not lista_aulas:
                del dados['horarios_alocados'][turma_apelido][dia][horario]
            
            salvar_dados(dados)
            return jsonify({"status": "success"})
            
    return jsonify({"status": "error", "message": "Aula não encontrada para remover."})


if __name__ == '__main__':
    app.run(debug=True)