import json
import random
import os

# --- CONFIGURAÇÕES ---
# Arquivo de entrada: seu arquivo de dados principal.
ARQUIVO_ENTRADA = 'dados.json'
# Arquivo de saída: um novo arquivo será criado com os dados completos.
ARQUIVO_SAIDA = 'dados_com_disponibilidade.json'

# Define os status possíveis. Repetir 'disponivel' aumenta a chance de ser escolhido.
STATUS_POSSIVEIS = ['disponivel', 'disponivel', 'disponivel', 'disponivel', 'indisponivel', 'externo']
# Define a probabilidade (de 0 a 1) de um horário manter o mesmo status do anterior.
# Isso ajuda a criar blocos de horários (ex: manhã inteira 'externo').
CHANCE_MANTER_STATUS = 0.8 

def gerar_disponibilidade_aleatoria():
    """
    Gera um mapa de disponibilidade completo para uma semana de trabalho,
    de forma aleatória, mas criando blocos lógicos para maior realismo.
    
    Returns:
        dict: Um dicionário representando a grade de disponibilidade.
    """
    disponibilidade = {}
    dias_semana = ['segunda-feira', 'terca-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira']
    
    # Lista completa de horários letivos (excluindo intervalos longos como almoço)
    # Em um sistema mais complexo, isso poderia ser lido da constante GRADE_HORARIOS.
    horarios_completos = [
        "07:10 - 08:00", "08:00 - 08:50", "08:50 - 09:40", "10:00 - 10:50", 
        "10:50 - 11:40", "11:40 - 12:30", "12:40 - 13:30", "13:30 - 14:20", 
        "14:20 - 15:10", "15:30 - 16:20", "16:20 - 17:10", "17:10 - 18:00",
        "18:20 - 19:10", "19:10 - 20:00", "20:00 - 20:50", "21:05 - 21:55", "21:55 - 22:45"
    ]
    
    for dia in dias_semana:
        disponibilidade[dia] = {}
        # Sorteia um status inicial para o primeiro horário do dia
        status_atual = random.choice(STATUS_POSSIVEIS)
        
        for horario in horarios_completos:
            # Lógica para criar blocos: há uma alta chance de manter o status anterior
            if random.random() > CHANCE_MANTER_STATUS:
                status_atual = random.choice(STATUS_POSSIVEIS)
            
            # Otimização: só armazenamos o status se ele NÃO for o padrão ('disponivel').
            # Isso mantém o arquivo dados.json mais limpo e legível.
            if status_atual != 'disponivel':
                disponibilidade[dia][horario] = status_atual
                
    return disponibilidade

def preencher_disponibilidades():
    """
    Função principal que lê o arquivo de dados, preenche as disponibilidades
    faltantes e salva o resultado em um novo arquivo.
    """
    print("--- Iniciando Script de Geração de Disponibilidade ---")
    
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"ERRO: Arquivo de entrada '{ARQUIVO_ENTRADA}' não foi encontrado.")
        return

    with open(ARQUIVO_ENTRADA, 'r', encoding='utf-8') as f:
        dados = json.load(f)

    professores = dados.get('professores', [])
    professores_atualizados = 0
    
    for professor in professores:
        # A condição principal: preenche apenas se a chave 'disponibilidade' não existir
        # ou se o dicionário de disponibilidade estiver vazio.
        if not professor.get('disponibilidade'):
            professor['disponibilidade'] = gerar_disponibilidade_aleatoria()
            professores_atualizados += 1
            print(f"Disponibilidade aleatória gerada para: {professor.get('nome')}")

    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
        
    print(f"\n--- Geração Concluída ---")
    if professores_atualizados > 0:
        print(f"{professores_atualizados} professores tiveram sua disponibilidade preenchida.")
        print(f"O resultado completo foi salvo no arquivo: '{ARQUIVO_SAIDA}'")
        print("\nPróximo Passo: Renomeie este novo arquivo para 'dados.json' para utilizá-lo na aplicação.")
    else:
        print("Todos os professores já possuíam registros de disponibilidade. Nenhum dado foi alterado.")


if __name__ == '__main__':
    preencher_disponibilidades()