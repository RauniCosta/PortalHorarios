import json

ARQUIVO_DADOS = 'dados.json'

def analisar_carga_horaria_vs_disponibilidade():
    """
    Verifica se a carga horária atribuída a cada professor na matriz curricular
    é compatível com o total de horários disponíveis que ele cadastrou.
    """
    print("--- Iniciando Script de Validação de Dados ---")
    
    try:
        with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Erro ao carregar o arquivo de dados: {e}")
        return

    professores = dados.get('professores', [])
    matriz = dados.get('matriz_curricular', [])
    
    if not professores or not matriz:
        print("Arquivo de dados não contém professores ou matriz curricular.")
        return

    print(f"\nAnalisando {len(professores)} professores...\n")
    
    conflitos_encontrados = 0
    
    for professor in professores:
        prof_id = professor.get('id')
        prof_nome = professor.get('nome', 'Sem Nome')
        
        # 1. Calcula o total de aulas atribuídas a este professor na matriz
        total_aulas_atribuidas = sum(
            item.get('aulas_necessarias', 0) 
            for item in matriz if item.get('id_professor') == prof_id
        )
        
        # 2. Calcula o total de horários em que o professor está 'disponivel'
        disponibilidade = professor.get('disponibilidade', {})
        total_horarios_disponiveis = 0
        for dia, horarios in disponibilidade.items():
            for status in horarios.values():
                if status == 'disponivel':
                    total_horarios_disponiveis += 1
        
        # Se a chave 'disponibilidade' não existir, consideramos todos os horários como disponíveis
        # (Esta é uma simplificação, o ideal é que todos tenham disponibilidade preenchida)
        if not disponibilidade:
             # Total de slots no dia (ex: 17) * 5 dias = 85
             total_horarios_disponiveis = 85 

        print(f"Professor: {prof_nome} (ID: {prof_id})")
        print(f"  - Aulas Atribuídas na Matriz: {total_aulas_atribuidas}")
        print(f"  - Slots Disponíveis na Semana: {total_horarios_disponiveis}")
        
        # 3. Compara os dois valores
        if total_aulas_atribuidas > total_horarios_disponiveis:
            print(f"  --> ALERTA! Conflito encontrado. Este professor tem mais aulas ({total_aulas_atribuidas}) do que horários disponíveis ({total_horarios_disponiveis}).")
            conflitos_encontrados += 1
        print("-" * 30)
        
    if conflitos_encontrados == 0:
        print("\n✅ Verificação concluída. Nenhum conflito óbvio de carga horária vs. disponibilidade foi encontrado.")
        print("O problema provavelmente está na combinação das outras regras de negócio (jornada, etc.).")
    else:
        print(f"\n❌ Verificação concluída. {conflitos_encontrados} professor(es) com conflitos de carga horária.")
        print("É matematicamente impossível gerar um horário com estes dados. Corrija a disponibilidade ou a matriz curricular.")

if __name__ == '__main__':
    analisar_carga_horaria_vs_disponibilidade()