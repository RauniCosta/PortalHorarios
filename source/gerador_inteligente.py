# gerador_inteligente.py

import json
import random
import os

# --- CONFIGURAÇÕES ---
ARQUIVO_ENTRADA = 'dados.json'
ARQUIVO_SAIDA = 'dados_gerados.json'
STATUS_POSSIVEIS_RESTANTES = ['disponivel', 'indisponivel', 'externo']

def gerar_disponibilidade_inteligente(min_horarios_necessarios, todos_slots_semana):
    """
    Gera um mapa de disponibilidade garantindo um número mínimo de slots 'disponivel'.

    Args:
        min_horarios_necessarios (int): O número mínimo de aulas que este professor precisa dar.
        todos_slots_semana (list): Uma lista de todas as tuplas (dia, horario) possíveis na semana.

    Returns:
        dict: O dicionário de disponibilidade gerado.
    """
    disponibilidade_final = {}
    
    # Garante que temos slots suficientes na semana para a carga horária
    if min_horarios_necessarios > len(todos_slots_semana):
        print(f"ALERTA: Carga horária ({min_horarios_necessarios}) é maior que o total de slots na semana ({len(todos_slots_semana)}).")
        # Mesmo assim, torna todos os slots disponíveis para este professor
        min_horarios_necessarios = len(todos_slots_semana)

    # 1. Garante os horários mínimos
    # Escolhe aleatoriamente o número exato de slots necessários e os marca como 'disponivel'
    slots_disponiveis_garantidos = random.sample(todos_slots_semana, min_horarios_necessarios)
    
    # Constrói um mapa temporário com todos os slots e seus status
    mapa_semana_completo = {slot: 'pendente' for slot in todos_slots_semana}
    for dia, horario in slots_disponiveis_garantidos:
        mapa_semana_completo[(dia, horario)] = 'disponivel'

    # 2. Preenche os horários restantes de forma aleatória
    for slot, status in mapa_semana_completo.items():
        if status == 'pendente':
            mapa_semana_completo[slot] = random.choice(STATUS_POSSIVEIS_RESTANTES)
    
    # 3. Formata para o padrão final do JSON, omitindo os 'disponivel' para limpeza
    for (dia, horario), status in mapa_semana_completo.items():
        if status != 'disponivel':
            if dia not in disponibilidade_final:
                disponibilidade_final[dia] = {}
            disponibilidade_final[dia][horario] = status
            
    return disponibilidade_final


def preencher_disponibilidades_inteligente():
    """
    Função principal que lê os dados, calcula a carga horária de cada professor
    e gera uma disponibilidade compatível.
    """
    print("--- Iniciando Gerador Inteligente de Disponibilidade ---")
    
    try:
        with open(ARQUIVO_ENTRADA, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Erro ao carregar o arquivo de dados: {e}")
        return

    professores = dados.get('professores', [])
    matriz = dados.get('matriz_curricular', [])
    professores_atualizados = 0

    # Cria uma lista mestre de todos os slots de aula possíveis
    horarios_completos = [
        "07:10 - 08:00", "08:00 - 08:50", "08:50 - 09:40", "10:00 - 10:50", 
        "10:50 - 11:40", "11:40 - 12:30", "12:40 - 13:30", "13:30 - 14:20", 
        "14:20 - 15:10", "15:30 - 16:20", "16:20 - 17:10", "17:10 - 18:00",
        "18:20 - 19:10", "19:10 - 20:00", "20:00 - 20:50", "21:05 - 21:55", "21:55 - 22:45"
    ]
    dias_semana = ['segunda-feira', 'terca-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira']
    todos_os_slots_da_semana = [(dia, horario) for dia in dias_semana for horario in horarios_completos]

    for professor in professores:
        prof_id = professor.get('id')
        if not prof_id: continue

        # Calcula a carga horária total do professor a partir da matriz
        carga_horaria_prof = sum(
            item.get('aulas_necessarias', 0)
            for item in matriz if item.get('id_professor') == prof_id
        )

        # Gera uma nova disponibilidade garantindo que a carga horária seja atendida
        professor['disponibilidade'] = gerar_disponibilidade_inteligente(carga_horaria_prof, todos_os_slots_da_semana)
        professores_atualizados += 1
        print(f"Disponibilidade inteligente gerada para: {professor.get('nome')} (Carga: {carga_horaria_prof} aulas)")

    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
        
    print(f"\n--- Geração Concluída ---")
    print(f"A disponibilidade de {professores_atualizados} professores foi criada/sobrescrita.")
    print(f"O resultado completo foi salvo no arquivo: '{ARQUIVO_SAIDA}'")
    print("\nPróximo Passo: Renomeie este novo arquivo para 'dados.json' para utilizá-lo na aplicação.")


if __name__ == '__main__':
    preencher_disponibilidades_inteligente()