# portal/scheduler_engine.py

from constraint import Problem, AllDifferentConstraint
from datetime import datetime, timedelta

# =============================================
# CONSTANTES E FUNÇÕES AUXILIARES
# =============================================

TEMPO_MINIMO_TRANSLADO = timedelta(minutes=20)
INTERVALO_MINIMO_POS_EXTERNO = timedelta(minutes=660)

def parse_horario(horario_str, parte='inicio'):
    try:
        partes = horario_str.split(' - ')
        idx = 0 if parte == 'inicio' else 1
        return datetime.strptime(partes[idx].strip(), '%H:%M')
    except (ValueError, IndexError):
        return None
    

def formatar_solucao(solucao_bruta, turma_map, prof_map, sala_map, matriz_map, disciplina_map):
    """
    Converte a saída do solver (dicionário de variáveis) para o formato padrão de 'horarios_alocados' usado no resto da aplicação.

    Args:
        solucao_bruta (dict): A solução retornada pelo solver.(outros args): Mapas para buscar nomes a partir de IDs.

    Returns:
        dict: A solução formatada.
    """
    horarios_formatados = {}
    if not solucao_bruta:
        return horarios_formatados

    for variavel, alocacao in solucao_bruta.items():
        if not alocacao or alocacao[0] is None:
            continue

        turma_id, dia, horario = variavel
        matriz_id, prof_id, sala_id = alocacao
        
        turma_apelido = turma_map.get(turma_id, {}).get('apelido', '??')
        item_matriz = matriz_map.get(matriz_id, {})
        disciplina_id = item_matriz.get('id_disciplina')
        disciplina_obj = disciplina_map.get(disciplina_id, {})
        
        aula_info = {
            "matriz_id": matriz_id,
            "disciplina": disciplina_obj.get('componente', '??'),
            "professor": prof_map.get(prof_id, {}).get('apelido', '??'),
            "sala": sala_map.get(sala_id, {}).get('nome', '??')
        }
        horarios_formatados.setdefault(turma_apelido, {}).setdefault(dia, {}).setdefault(horario, []).append(aula_info)
        
    return horarios_formatados

# =============================================
# FUNÇÕES DE RESTRIÇÃO CUSTOMIZADAS
# =============================================
def no_professor_conflict(*aulas):
    """Garante que não há IDs de professores repetidos nas aulas fornecidas."""
    # Filtra None e extrai o ID do professor (posição 1 na tupla de alocação)
    professores_alocados = [aula[1] for aula in aulas if aula and aula[1] is not None]
    # A restrição é válida se o número de professores for igual ao número de professores únicos
    return len(professores_alocados) == len(set(professores_alocados))

def no_sala_conflict(*aulas):
    """Garante que não há IDs de salas repetidos nas aulas fornecidas."""
    # Filtra None e extrai o ID da sala (posição 2 na tupla de alocação)
    salas_alocadas = [aula[2] for aula in aulas if aula and aula[2] is not None]
    # A restrição é válida se o número de salas for igual ao número de salas únicas
    return len(salas_alocadas) == len(set(salas_alocadas))

def criar_restricao_jornada_professor(variaveis_do_professor):
    """
    Cria e retorna uma função de restrição que aplica um conjunto de regras de jornada de trabalho para um professor específico. Esta é uma "fábrica" de funções.
    
    Args:
        variaveis_do_professor (list): A lista de todos os slots de horário (variáveis) onde este professor PODE ser alocado.
                                       
    Returns:
        function: A função de restrição que será efetivamente chamada pelo solver.
    """
    
    def restricao_jornada(*aulas_alocadas):
        """
        Esta é a função que o solver irá executar. Ela recebe as aulas que foram efetivamente alocadas para este professor em seus possíveis slots.
        
        Args:
            *aulas_alocadas: Uma tupla de alocações (matriz_id, prof_id, sala_id). Muitos podem ser None se o professor não foi alocado naquele slot.
        """
        
        # --- PREPARAÇÃO DOS DADOS ---
        # Filtra apenas as alocações reais e mapeia para informações úteis.
        aulas_com_info = []
        for i, alocacao in enumerate(aulas_alocadas):
            # Ignora slots onde o professor não foi alocado
            if not alocacao or not alocacao[0]:
                continue
            
            var_info = variaveis_do_professor[i]
            aulas_com_info.append({
                "dia": var_info[1],
                "inicio": parse_horario(var_info[2], 'inicio'),
                "fim": parse_horario(var_info[2], 'fim')
            })

        # Se não houver aulas, a restrição é válida.
        if not aulas_com_info:
            return True

        # --- REGRA 4: MÁXIMO DE 6 AULAS SEGUIDAS ---
        aulas_por_dia = {}
        for aula in aulas_com_info:
            if aula['dia'] not in aulas_por_dia:
                aulas_por_dia[aula['dia']] = []
            aulas_por_dia[aula['dia']].append(aula)
            
        for dia, lista_aulas in aulas_por_dia.items():
            if len(lista_aulas) > 6:
                lista_aulas.sort(key=lambda x: x['inicio'])
                aulas_seguidas = 1
                for i in range(len(lista_aulas) - 1):
                    # Verifica se o fim de uma aula é exatamente o início da próxima
                    if lista_aulas[i]['fim'] == lista_aulas[i+1]['inicio']:
                        aulas_seguidas += 1
                        if aulas_seguidas > 6:
                            return False  # Violação: Mais de 6 aulas seguidas
                    else:
                        aulas_seguidas = 1 # Reseta a contagem se houver uma janela
        
        # --- REGRA 5: DESCANSO DE 11 HORAS ENTRE DIAS ---
        dias_ordenados = ['segunda-feira', 'terca-feira', 'quarta-feira', 'quinta-feira']
        for i in range(len(dias_ordenados)):
            dia_atual_str = dias_ordenados[i]
            dia_seguinte_str = dias_ordenados[i+1]
            
            aulas_dia_atual = aulas_por_dia.get(dia_atual_str)
            aulas_dia_seguinte = aulas_por_dia.get(dia_seguinte_str)

            if aulas_dia_atual and aulas_dia_seguinte:
                ultima_aula_do_dia = max(aula['fim'] for aula in aulas_dia_atual)
                primeira_aula_do_dia_seguinte = min(aula['inicio'] for aula in aulas_dia_seguinte)
                
                # timedelta(days=1) simula a passagem para o dia seguinte
                descanso = (primeira_aula_do_dia_seguinte + timedelta(days=1)) - ultima_aula_do_dia
                
                if descanso < timedelta(hours=11):
                    return False  # Violação: Descanso entre jornadas menor que 11 horas

        # Se passou por todas as verificações, a jornada do professor é válida
        return True
        
    return restricao_jornada

# =============================================
# FUNÇÃO PRINCIPAL DO MOTOR
# =============================================

def gerar_sugestao_horario(dados, grade_horarios_fixos, periodo_map):
    """
    Orquestra a criação e resolução do problema de satisfação de restrições.
    """
    try:
        problem = Problem()

        # --- 1. PREPARAÇÃO DOS DADOS ---
        print("[MOTOR] Iniciando preparação dos dados...")
        turmas = dados.get('turmas', [])
        professores = dados.get('professores', [])
        matriz = dados.get('matriz_curricular', [])
        salas = dados.get('salas', [])
        
        prof_map = {p['id']: p for p in professores}
        turma_map = {t['id']: t for t in turmas}
        sala_map = {s['id']: s for s in salas}
        disciplina_map = {d['id']: d for d in dados.get('disciplinas', [])}
        matriz_map = {m['matriz_id']: m for m in matriz}
        print("[MOTOR] Preparação dos dados concluída.")

        # --- 2. DEFINIÇÃO DE VARIÁVEIS E DOMÍNIOS ---
        print("[MOTOR] Iniciando definição de variáveis e domínios...")
        todas_variaveis = []
        
        for turma in turmas:
            turma_id = turma.get('id')
            categoria = turma.get('categoria')
            periodo_id = str(turma.get('periodo', '1'))
            periodo_nome = periodo_map.get(periodo_id)

            if not all([turma_id, categoria, periodo_nome]): continue

            grade_da_turma = grade_horarios_fixos.get(categoria, {}).get(periodo_nome, {})
            horarios_letivos_turma = [h for h, apelido in grade_da_turma.items() if apelido.upper() not in ["INTERVALO", "ALMOÇO"]]

            for dia in ['segunda-feira', 'terca-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira']:
                for horario in horarios_letivos_turma:
                    variavel = (turma_id, dia, horario)
                    dominio = []
                    matriz_da_turma = [item for item in matriz if item.get('id_turma') == turma_id]

                    for item_matriz in matriz_da_turma:
                        prof_id = item_matriz.get('id_professor')
                        professor = prof_map.get(prof_id)
                        if not professor: continue
                        
                        disponibilidade_dia = professor.get('disponibilidade', {}).get(dia, {})
                        status_professor = disponibilidade_dia.get(horario, 'disponivel')
                        
                        if status_professor in ['indisponivel', 'externo']: continue

                        for sala in salas:
                            dominio.append((item_matriz['matriz_id'], prof_id, sala['id']))
                    
                    if not dominio:
                        dominio.append((None, None, None))

                    problem.addVariable(variavel, dominio)
                    todas_variaveis.append(variavel)
        
        print("[MOTOR] Definição de variáveis e domínios concluída.")

        # --- 3. ADIÇÃO DAS RESTRIÇÕES ---
        print("[MOTOR] EXECUTANDO EM MODO 'TESTE DE SANIDADE'")
        print("[MOTOR] AVISO: Apenas restrições de conflito de professor/sala estão ativas.")
        
        # Restrição para não usar o valor 'None'
        #problem.addConstraint(lambda *aulas: all(a[0] is not None for a in aulas if a is not None), todas_variaveis)
        
        # CORREÇÃO: Restrições de Conflito de Professor e Sala
        slots_por_dia_horario = {}
        for var in todas_variaveis:
            chave = (var[1], var[2]) # (dia, horario)
            if chave not in slots_por_dia_horario:
                slots_por_dia_horario[chave] = []
            slots_por_dia_horario[chave].append(var)

        for chave, variaveis in slots_por_dia_horario.items():
            if len(variaveis) > 1:
                problem.addConstraint(no_professor_conflict, variaveis)
                problem.addConstraint(no_sala_conflict, variaveis)

        """ # Restrição de Carga Horária Semanal
        for item_matriz in matriz:
            aulas_necessarias = item_matriz.get('aulas_necessarias', 0)
            matriz_id_alvo = item_matriz.get('matriz_id')
            if aulas_necessarias == 0 or not matriz_id_alvo: continue

            variaveis_da_turma = [var for var in todas_variaveis if var[0] == item_matriz['id_turma']]
            
            # Usando uma função nomeada para melhor depuração em vez de lambda
            def criar_restricao_contagem(target_id, required_count):
                def restricao( *alocacoes):
                    count = sum(1 for alocacao in alocacoes if alocacao and alocacao[0] == target_id)
                    return count == required_count
                return restricao
            
            problem.addConstraint(criar_restricao_contagem(matriz_id_alvo, aulas_necessarias), variaveis_da_turma)
 """
        print("[MOTOR] Definição de restrições de sanidade concluída.")

        # --- 4. RESOLUÇÃO, AVALIAÇÃO E FORMATAÇÃO ---
        print("[MOTOR] Solucionando o problema. Buscando até 10 soluções viáveis...")
        
        # Etapa 1: Gerar um conjunto de soluções válidas
        solucao_iter = problem.getSolutionIter()
        solucoes_brutas_encontradas = []
        # Tenta encontrar até 10 soluções para ter um bom conjunto para avaliar.
        # Aumentar este número pode dar resultados melhores, mas levará mais tempo.
        for i in range(10): 
            try:
                solucoes_brutas_encontradas.append(next(solucao_iter))
            except StopIteration:
                break # Para se não houver mais soluções

        if not solucoes_brutas_encontradas:
            print("[MOTOR] Nenhuma solução encontrada que atenda às regras RÍGIDAS.")
            return {"error": "Não foi possível encontrar uma solução que atenda a todas as restrições obrigatórias. Verifique a disponibilidade dos professores e a carga horária das turmas."}

        print(f"[MOTOR] Sucesso! {len(solucoes_brutas_encontradas)} solução(ões) encontrada(s). Formatando e avaliando...")

        # Etapa 2: Formatar todas as soluções encontradas
        solucoes_formatadas = []
        for solucao_bruta in solucoes_brutas_encontradas:
            solucao_formatada = formatar_solucao(
                solucao_bruta, turma_map, prof_map, sala_map, matriz_map, disciplina_map
            )
            solucoes_formatadas.append(solucao_formatada)

        # Etapa 3: Avaliar e escolher a melhor solução com base nas regras suaves
        melhor_solucao = avaliar_e_escolher_melhor_solucao(solucoes_formatadas, matriz_map)
        
        # Etapa 4: Retornar apenas a melhor solução encontrada
        return melhor_solucao

    except Exception as e:
        print(f"[MOTOR] CRASH! Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        raise e

def calcular_pontuacao(solucao_formatada, matriz_map):
    """
    Dá uma nota para uma grade de horário baseada nas regras suaves (preferências).
    Quanto maior a pontuação, melhor a grade.

    Args:
        solucao_formatada (dict): A grade de horário no formato de 'horarios_alocados'.
        matriz_map (dict): O mapa da matriz curricular para consulta rápida.

    Returns:
        int: A pontuação final da solução.
    """
    pontuacao = 1000
    
    aulas_por_turma_disciplina = {}
    aulas_por_professor = {}

    # --- Organiza os dados para facilitar a avaliação ---
    for turma, dias in solucao_formatada.items():
        for dia, horarios in dias.items():
            for horario, aulas in horarios.items():
                if not aulas: continue
                alocacao = aulas[0]
                matriz_id = alocacao['matriz_id']
                prof_apelido = alocacao['professor']

                # Agrupa por turma e disciplina para a Regra 7
                chave_disciplina = (turma, matriz_id)
                if chave_disciplina not in aulas_por_turma_disciplina:
                    aulas_por_turma_disciplina[chave_disciplina] = []
                aulas_por_turma_disciplina[chave_disciplina].append({'dia': dia, 'horario': horario})

                # Agrupa por professor para a Regra 3 (janelas)
                if prof_apelido not in aulas_por_professor:
                    aulas_por_professor[prof_apelido] = []
                aulas_por_professor[prof_apelido].append({'dia': dia, 'inicio': parse_horario(horario, 'inicio')})

    # --- APLICAÇÃO DAS REGRAS SUAVES ---

    # REGRA 7 (OTIMIZAÇÃO): Penalizar aulas que deveriam ser seguidas e não são.
    for (turma, matriz_id), alocacoes in aulas_por_turma_disciplina.items():
        item_matriz = matriz_map.get(matriz_id, {})
        # Usando sua sugestão: se aulas_necessarias > 1, tentamos agrupar.
        if item_matriz.get('aulas_necessarias', 1) > 1:
            # Agrupa por dia para verificar se estão no mesmo dia
            aulas_no_dia = {}
            for aloc in alocacoes:
                if aloc['dia'] not in aulas_no_dia: aulas_no_dia[aloc['dia']] = []
                aulas_no_dia[aloc['dia']].append(aloc)
            
            # Se as aulas de uma mesma disciplina estão em dias diferentes, penaliza.
            if len(aulas_no_dia) > (len(alocacoes) / 2): # Heurística simples
                pontuacao -= 5 # Penalidade por espalhar demais as aulas

    # REGRA 3 (OTIMIZAÇÃO): Penalizar "janelas" na grade do professor
    for prof, aulas in aulas_por_professor.items():
        aulas_por_dia_prof = {}
        for a in aulas:
            if a['dia'] not in aulas_por_dia_prof: aulas_por_dia_prof[a['dia']] = []
            aulas_por_dia_prof[a['dia']].append(a)
        
        for dia, lista_aulas in aulas_por_dia_prof.items():
            lista_aulas.sort(key=lambda x: x['inicio'])
            for i in range(len(lista_aulas) - 1):
                fim_aula_atual = parse_horario(lista_aulas[i]['horario'], 'fim')
                inicio_aula_seguinte = lista_aulas[i+1]['inicio']
                
                # Se o intervalo entre as aulas é maior que o de um intervalo normal (ex: 20 min)
                # e menor que um turno (ex: 4 horas), consideramos uma janela.
                if timedelta(minutes=25) < (inicio_aula_seguinte - fim_aula_atual) < timedelta(hours=4):
                    pontuacao -= 2 # Penalidade por cada janela encontrada

    return pontuacao


def avaliar_e_escolher_melhor_solucao(solucoes_formatadas, matriz_map):
    """
    Recebe uma lista de soluções formatadas, calcula a pontuação de cada uma
    e retorna a que tiver a maior pontuação.
    """
    if not solucoes_formatadas:
        return None
        
    melhor_solucao = None
    maior_pontuacao = -float('inf')

    print(f"[AVALIADOR] Avaliando {len(solucoes_formatadas)} soluções...")
    for i, solucao in enumerate(solucoes_formatadas):
        pontuacao = calcular_pontuacao(solucao, matriz_map)
        print(f"[AVALIADOR] Solução {i+1} - Pontuação: {pontuacao}")
        if pontuacao > maior_pontuacao:
            maior_pontuacao = pontuacao
            melhor_solucao = solucao
    
    print(f"[AVALIADOR] Melhor solução escolhida com pontuação {maior_pontuacao}.")
    return melhor_solucao