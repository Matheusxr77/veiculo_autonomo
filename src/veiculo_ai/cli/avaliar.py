import os
import time
import sys
from src.veiculo_ai.ambiente.transito import Transito
from src.veiculo_ai.agentes.heuristico import AgenteHeuristico
from src.veiculo_ai.agentes.qlearning import AgenteQLearning
from src.veiculo_ai.agentes.genetico import AgenteGenetico

def rodar_avaliacao(agente, ambiente, episodios=3500):
    # inicialização dos contadores das métricas
    sucessos = 0
    atropelamentos = 0
    colisoes = 0
    timeouts = 0

    # variáveis para calcular médias depois que o loop terminar
    total_passos_sucesso = 0
    total_recompensa = 0.0
    
    # se o agente precisa aprender antes de ser avaliado
    if hasattr(agente, 'treinar'):
        print(f"[{agente.nome}] Iniciando treinamento de {episodios} episódios (Aguarde)...")
        agente.treinar(ambiente, episodios=episodios) # aciona o treinamento antes de começar a avaliação
        
    inicio_tempo = time.time() # marca o tempo que a avaliação começa
    
    # avaliação oficial 
    for ep in range(episodios):
        # reinicia o ambiente para a posição inicial e reseta as variáveis da simulação
        estado = ambiente.reset() 
        finalizado = False
        passos_episodio = 0
        
        while not finalizado:
            acao = agente.escolher_acao(estado, ambiente) # agente escolhe uma ação com base no estado atual
            estado, recompensa, finalizado, info = ambiente.step(acao) # executa ação e receba as consequências

            # atualiza os acumuladores de passos e recompensas da simulação
            passos_episodio += 1
            total_recompensa += recompensa
            
        status = info.get("status", "") # pega a string de status de dentro do dicionário retornado pelo ambiente

        if info.get("sucesso", False): # se sucesso, então chegou ao destino
            sucessos += 1
            total_passos_sucesso += passos_episodio
        # se não houve sucesso, verifica qual tipo exato de falha
        elif "Atropelamento" in status:
            atropelamentos += 1
        elif "Colisão" in status:
            colisoes += 1
        elif "Tempo Esgotado" in status:
            timeouts += 1

        # barra de progresso de atualização durante o treino (deve se atualizar 10 vezes durante o processo)
        frequencia_atualizacao = max(1, episodios // 10)
        if (ep + 1) % frequencia_atualizacao == 0 or (ep + 1) == episodios:
            progresso = (ep + 1) / episodios # calcula a porcentagem
            tamanho_barra = 40
            preenchido = int(tamanho_barra * progresso) # calcula quantos blocos da barra devem estar preenchidos
            barra = '█' * preenchido + '-' * (tamanho_barra - preenchido) # monta a barra
            percentual = progresso * 100
            
            sys.stdout.write(f'\rAvaliação: |{barra}| {percentual:.1f}% ({ep + 1}/{episodios})')
            sys.stdout.flush()
            
    print() 
    
    tempo_execucao = time.time() - inicio_tempo # calcula o tempo total gasto na avaliação
    
    taxa_sucesso = (sucessos / episodios) * 100 # calcula a porcentagem de vitórias em relação ao total de simulações
    if sucessos > 0: # verifica se houve ao menos um sucesso para evitar erro de divisão por zero
        media_passos_sucesso = total_passos_sucesso / sucessos
    else:
        media_passos_sucesso = 0.0    

    return {
        "Agente": agente.nome,
        "Taxa de Sucesso (%)": round(taxa_sucesso, 2),
        "Taxa de Atropelamento (%)": round((atropelamentos / episodios) * 100, 2),
        "Taxa de Colisão (%)": round((colisoes / episodios) * 100, 2),
        "Taxa de Timeout (%)": round((timeouts / episodios) * 100, 2),
        "Passos Médios (Sucesso)": round(media_passos_sucesso, 2),
        "Recompensa (Média)": round(total_recompensa / episodios, 2),
        "Tempo (Segundos)": round(tempo_execucao, 4)
    }

def main():
    ambiente = Transito() 
    agentes = [
        AgenteHeuristico(),
        AgenteQLearning(nome="Q-Learning"),
        AgenteGenetico(nome="Algoritmo Genético")
    ] 
    
    resultados = [] # acumula os dicionários retornados por rodar_avaliacao
    num_episodios = 5000 # carga de testes
    
    print(f"Iniciando Avaliação Robusta ({num_episodios} episódios por agente)...\n")
    
    # passa agente por agente realizando os testes
    for agente in agentes:
        print(f"Avaliando {agente.nome}...")
        metricas = rodar_avaliacao(agente, ambiente, episodios=num_episodios) # chama a rotina de avaliação e captura o dicionário de resultados
        resultados.append(metricas) # salva o resultado na lista
        print("-" * 60)
        
    print("\n" + "="*70)
    print("RELATÓRIO DE MÉTRICAS ROBUSTAS DOS AGENTES")
    print("="*70)
    # percorre a lista de dicionários e formata a saída na tela
    for res in resultados:
        print(f"Agente: {res['Agente']}")
        print(f"  - Taxa de Sucesso:        {res['Taxa de Sucesso (%)']}%")
        print(f"  - Taxa de Atropelamento:  {res['Taxa de Atropelamento (%)']}%")
        print(f"  - Taxa de Colisão:        {res['Taxa de Colisão (%)']}%")
        print(f"  - Taxa de Timeout:        {res['Taxa de Timeout (%)']}%")
        print(f"  - Passos Médios(Sucesso): {res['Passos Médios (Sucesso)']}")
        print(f"  - Recompensa Média:       {res['Recompensa (Média)']}")
        print(f"  - Tempo de Teste:         {res['Tempo (Segundos)']}s")
        print("-" * 70)

    # cria o arquivo e registra os resultados
    os.makedirs("results", exist_ok=True)
    with open("results/comparacao_agentes.txt", "w", encoding="utf-8") as f:
        f.write("RELATÓRIO DE MÉTRICAS DOS AGENTES\n")
        f.write("="*80 + "\n")
        for res in resultados:
            f.write(f"[{res['Agente']}] "
                    f"Sucesso: {res['Taxa de Sucesso (%)']}% | "
                    f"Atropelamento: {res['Taxa de Atropelamento (%)']}% | "
                    f"Colisão: {res['Taxa de Colisão (%)']}% | "
                    f"Timeout: {res['Taxa de Timeout (%)']}% | "
                    f"Passos: {res['Passos Médios (Sucesso)']} | "
                    f"Recompensa: {res['Recompensa (Média)']}\n")
    print("\nResultados detalhados salvos em 'results/comparacao_agentes.txt'.")

if __name__ == "__main__":
    main()
