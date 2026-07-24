import random
from typing import Dict, Tuple, List
from collections import deque
from .base import AgenteBase
from src.veiculo_ai.ambiente.transito import Acao

class AgenteQLearning(AgenteBase):
    def __init__(self, nome: str = "Q-Learning", alpha: float = 0.1, gamma: float = 0.9, epsilon: float = 1.0, epsilon_min: float = 0.01, decaimento: float = 0.995, janela_anticiclo: int = 6):
        super().__init__(nome)
        
        # a Tabela-Q mapeia um estado (tupla linha, coluna) para um dicionário de ações e seus respectivos valores numéricos
        self.q_tabela: Dict[Tuple[int, int], Dict[Acao, float]] = {}
        
        # Atributo para rastrear a última ação tomada e evitar o retrocesso imediato
        self.ultima_acao: Acao | None = None
        
        # alpha: Taxa de aprendizado (o quão rápido o agente substitui o conhecimento antigo pelo novo)
        self.alpha = alpha
        # gamma: Fator de desconto (a importância que o agente dá para recompensas de longo prazo em vez de imediatas)
        self.gamma = gamma
        # epsilon: Taxa de exploração aleatória inicial (1.0 significa 100% aleatório no começo)
        self.epsilon = epsilon
        # epsilon_min: O piso da exploração; garante que ele pare de decair quando chegar a esse limite
        self.epsilon_min = epsilon_min
        # decaimento: Fator multiplicativo que reduz o epsilon a cada episódio (decaimento exponencial)
        self.decaimento = decaimento

        self.historico_estados: List[Tuple[int, int]] = []
        self.janela_anticiclo = janela_anticiclo

    def _obter_q_valores(self, estado: Tuple[int, int]) -> Dict[Acao, float]:
        # recupera os valores-Q do estado atual. Se for um estado novo, inicializa todas as ações com 0.0
        if estado not in self.q_tabela:
            # inicializa de forma preguiçosa apenas quando o agente visita o bloco
            self.q_tabela[estado] = {acao: 0.0 for acao in Acao}
        return self.q_tabela[estado]

    def _obter_melhor_acao(self, q_valores, ultima_acao=None):
        # encontra a melhor ação e resolve empates de forma aleatória para evitar loops infinitos
        opostos = {
            Acao.CIMA: Acao.BAIXO, Acao.BAIXO: Acao.CIMA,
            Acao.ESQUERDA: Acao.DIREITA, Acao.DIREITA: Acao.ESQUERDA
        }
        acao_proibida = opostos.get(ultima_acao)

        # ordena por valor-Q decrescente
        ordenado = sorted(q_valores.items(), key=lambda x: x[1], reverse=True)
        # tenta achar o melhor valor entre as ações que não regridem
        melhor_valor_permitido = next((v for a, v in ordenado if a != acao_proibida), None)

        if melhor_valor_permitido is None:
            # não existe nenhuma ação além da oposta = não há escolha
            return ordenado[0][0]

        melhores = []
        for acao, valor in ordenado:
            if valor == melhor_valor_permitido and acao != acao_proibida:
                melhores.append(acao)

        return random.choice(melhores)

    def _calcula_proxima_posicao(self, estado: Tuple[int, int], acao: Acao) -> Tuple[int, int]:
        linha, coluna = estado
        if acao == Acao.CIMA: linha -= 1
        elif acao == Acao.BAIXO: linha += 1
        elif acao == Acao.ESQUERDA: coluna -= 1
        elif acao == Acao.DIREITA: coluna += 1
        return (linha, coluna)
 
    def _posicao_valida(self, pos: Tuple[int, int], ambiente) -> bool:
        linha, coluna = pos
        if not (0 <= linha < ambiente.tamanho_grade and 0 <= coluna < ambiente.tamanho_grade):
            return False
        if pos in ambiente.obstaculos:
            return False
        return True

    def _calcular_mapa_potencial(self, ambiente) -> None:
        destino = ambiente.posicao_destino
        dist = {destino: 0}
        fila = deque([destino])
 
        while fila:
            atual = fila.popleft()
            l, c = atual
            for viz in ((l - 1, c), (l + 1, c), (l, c - 1), (l, c + 1)):
                vl, vc = viz
                linha_dentro_da_grade = 0 <= vl < ambiente.tamanho_grade
                coluna_dentro_da_grade = 0 <= vc < ambiente.tamanho_grade
                dentro = linha_dentro_da_grade and coluna_dentro_da_grade
                if dentro and viz not in dist and viz not in ambiente.obstaculos:
                    dist[viz] = dist[atual] + 1
                    fila.append(viz)
 
        # potencial = -distância real até o destino
        self._mapa_potencial = {pos: -d for pos, d in dist.items()}
        # célula isolada (cercada de obstáculo, inalcançável) recebe o pior potencial possível
        self._pior_caso_potencial = -(2 * ambiente.tamanho_grade)
 
    def _potencial(self, estado: Tuple[int, int]) -> float:
        return self._mapa_potencial.get(estado, self._pior_caso_potencial)

    def treinar(self, ambiente, episodios: int = 1500) -> None:
        # preenche a Tabela-Q interagindo com o ambiente (Tentativa e Erro)
        print(f"Treinando {self.nome} por {episodios} episódios...")
 
        # cria a lista de ações permitidas para exploração uma vez aqui fora
        acoes_movimento = [a for a in Acao if a != Acao.PARAR]
 
        # calcula (ou recalcula) o mapa de potencial baseado em BFS antes de começar o treino
        self._calcular_mapa_potencial(ambiente)
 
        for _ in range(episodios):
            estado = ambiente.reset()
            finalizado = False
 
            # reseta a última ação no início de cada novo episódio
            self.ultima_acao = None
 
            while not finalizado:
                # recupera os valores do estado atual uma única vez para economizar processamento
                q_valores_atual = self._obter_q_valores(estado)
 
                # equilibra exploração aleatória e exploração consciente
                if random.uniform(0, 1) < self.epsilon:
                    # joga uma moeda; se cair na faixa de epsilon, toma uma ação totalmente aleatória (menos parar, só pode andar)
                    acao = random.choice(acoes_movimento)
                else:
                    # passa a self.ultima_acao para o método de escolha ativar o filtro anticiclo
                    acao = self._obter_melhor_acao(q_valores_atual, self.ultima_acao)
 
                # evita que o agente morra no treino por culpa de obstáculos dinâmicos que a Tabela-Q não tem capacidade de prever.
                prox_coord = self._calcula_proxima_posicao(estado, acao)
 
                if prox_coord in ambiente.pedestres or prox_coord in ambiente.carros_dinamicos:
                    acao = Acao.PARAR
 
                # captura o potencial do estado atual
                potencial_atual = self._potencial(estado)
 
                # o agente interage com o ambiente executando a ação selecionada
                prox_estado, recompensa, finalizado, _ = ambiente.step(acao)
 
                potencial_proximo = self._potencial(prox_estado)
                recompensa = recompensa + (self.gamma * potencial_proximo - potencial_atual)
 
                q_valores_prox = self._obter_q_valores(prox_estado)
 
                # estima a recompensa futura olhando para a melhor ação possível no próximo estado
                q_atual = q_valores_atual[acao]
                max_q_futuro = max(q_valores_prox.values())
 
                # atualiza a qualidade do par estado-ação somando o valor antigo com o erro temporal
                novo_q = q_atual + self.alpha * (recompensa + self.gamma * max_q_futuro - q_atual)
 
                # registra o aprendizado na Tabela-Q oficial
                self.q_tabela[estado][acao] = novo_q
 
                # atualiza a última ação executada antes de avançar o estado
                self.ultima_acao = acao
 
                # avança no tempo para o próximo estado
                estado = prox_estado
 
            # decaimento exponencial: reduz gradativamente a chance de agir aleatoriamente
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.decaimento

    def escolher_acao(self, estado: Tuple[int, int], ambiente) -> Acao:
        # registra o estado atual na memória de curto prazo (só usada aqui, nunca no treino)
        self.historico_estados.append(estado)
        if len(self.historico_estados) > self.janela_anticiclo:
            self.historico_estados.pop(0)
 
        q_valores = self._obter_q_valores(estado)
 
        # filtra os valores Q para ignorar o parar na exibição,
        # impedindo que o valor 0.0 não treinado vença os valores de movimento
        q_movimento = {acao: valor for acao, valor in q_valores.items() if acao != Acao.PARAR}
        candidatos = sorted(q_movimento.items(), key=lambda item: item[1], reverse=True)
 
        opostas = {
            Acao.CIMA: Acao.BAIXO,
            Acao.BAIXO: Acao.CIMA,
            Acao.ESQUERDA: Acao.DIREITA,
            Acao.DIREITA: Acao.ESQUERDA
        }
        acao_oposta = opostas.get(self.ultima_acao)
 
        # duas passadas: primeiro tenta respeitar regras rígidas (não regredir, não repetir
        # estado recente, não bater em obstáculo/borda, desviar de carro); se nenhuma opção sobrar (beco sem saída real), relaxa e aceita inclusive regressão como último recurso
        for rigido in (True, False):
            for acao, _ in candidatos:
                if rigido and acao == acao_oposta:
                    continue
 
                prox_estado = self._calcula_proxima_posicao(estado, acao)
 
                if not self._posicao_valida(prox_estado, ambiente):
                    continue  # nunca sai do mapa nem pisa em obstáculo estático
 
                if prox_estado in ambiente.carros_dinamicos:
                    continue  # obstáculo na simulação -> tenta desviar
 
                if rigido and prox_estado in self.historico_estados:
                    continue  # evita voltar a um estado visitado há pouco -> quebra ciclos maiores
 
                if prox_estado in ambiente.pedestres:
                    self.ultima_acao = Acao.PARAR
                    return Acao.PARAR
 
                self.ultima_acao = acao
                return acao
 
        # nenhuma opção sobrou nas duas passadas (beco sem saída real): só resta parar
        self.ultima_acao = Acao.PARAR
        return Acao.PARAR
    