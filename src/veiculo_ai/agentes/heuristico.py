import heapq
import itertools
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from .base import AgenteBase
from src.veiculo_ai.ambiente.transito import Acao

class AgenteHeuristico(AgenteBase):
    def __init__(self, nome: str = "A-Estrela (Heurístico)"):
        super().__init__(nome)
        self.caminho_planejado: List[Acao] = []

    def _heuristica(self, atual: Tuple[int, int], destino: Tuple[int, int]) -> int:
        # calcula a Distância de Manhattan entre dois pontos na grade
        # como o agente só se move em cruz em uma grade, essa é a heurística que melhor se encaixa
        return abs(atual[0] - destino[0]) + abs(atual[1] - destino[1])

    def _obter_coordenada_acao(self, estado: Tuple[int, int], acao: Acao) -> Tuple[int, int]:
        # encapsula o cálculo do próximo estado isolando a lógica matemática
        linha, coluna = estado 

        # retorna a nova coordenada dependendo da direção escolhida
        if acao == Acao.CIMA: return linha - 1, coluna 
        if acao == Acao.BAIXO: return linha + 1, coluna
        if acao == Acao.ESQUERDA: return linha, coluna - 1
        if acao == Acao.DIREITA: return linha, coluna + 1
        return linha, coluna # se for parar retorna a coordenada sem alteração

    def _reconstruir_caminho(self, pais: Dict, estado_atual: Tuple[int, int]) -> List[Acao]:
        # reconstrói o caminho ótimo do destino até a origem
        caminho = []
        while estado_atual in pais:
            estado_atual, acao = pais[estado_atual] # pega o estado pai e a ação que foi tomada para chegar no estado atual
            caminho.append(acao) # adiciona a ação na lista
        caminho.reverse() # como foi iterado do destino para a origem a lista ficou invertida, então é preciso inverter para ter a ordem correta
        return caminho

    def _planejar_caminho(self, estado_inicial: Tuple[int, int], ambiente) -> List[Acao]:
        destino = ambiente.posicao_destino # obtem a coordenada do destino no ambiente

        # junta todos os obstáculos (fixos e dinâmicos) em um conjunto (set)
        obstaculos_bloqueantes = set(ambiente.obstaculos + ambiente.carros_dinamicos) 
        tamanho = ambiente.tamanho_grade

        # cria um gerador de números sequencias para usar como critério de desempate
        contador_desempate = itertools.count()

        # inicializa a fila de prioridade com o nó inicial
        fila = [(self._heuristica(estado_inicial, destino), next(contador_desempate), estado_inicial)]

        custos_g: Dict[Tuple[int, int], int] = {estado_inicial: 0}
        pais: Dict[Tuple[int, int], Tuple[Tuple[int, int], Acao]] = {} # dicionário de rastreamento

        while fila:
            _, _, atual = heapq.heappop(fila) # remove o nó com o menor f_score da fila, os dois primeiros valores são ignorados com '_'

            if atual == destino: # se nó removido da fila é o destino, o caminho ótimo foi encontrado
                return self._reconstruir_caminho(pais, atual)

            linha, coluna = atual # desempacota a coordenada atual para gerar os vizinhos

            # descobre qual foi a ação que trouxe o agente até o estado atual (se houver)
            ultima_acao_tomada = None
            if atual in pais:
                _, ultima_acao_tomada = pais[atual]

            # mapeia a ação oposta para proibir o retrocesso imediato passo a passo
            opostas = {
                Acao.CIMA: Acao.BAIXO,
                Acao.BAIXO: Acao.CIMA,
                Acao.ESQUERDA: Acao.DIREITA,
                Acao.DIREITA: Acao.ESQUERDA
            }
            acao_proibida = opostas.get(ultima_acao_tomada)

            movimentos = [
                (linha - 1, coluna, Acao.CIMA),
                (linha + 1, coluna, Acao.BAIXO),
                (linha, coluna - 1, Acao.ESQUERDA),
                (linha, coluna + 1, Acao.DIREITA)
            ]

            # analisa cada um dos 4 vizinhos
            for prox_linha, prox_coluna, acao in movimentos:
                # se a ação gerada for exatamente a oposta da que o trouxe aqui, ignora (não regride)
                if acao == acao_proibida:
                    continue

                prox_estado = (prox_linha, prox_coluna)
                
                # verifica se a coordenada está dentro dos limites do mapa
                dentro_limites_linha = 0 <= prox_linha < tamanho
                dentro_limites_coluna = 0 <= prox_coluna < tamanho
                dentro_do_mapa = dentro_limites_linha and dentro_limites_coluna

                # verifica se a coordenada não é uma parede ou outro carro
                caminho_livre = prox_estado not in obstaculos_bloqueantes

                # a condição final vira um texto claro e sem números soltos
                if dentro_do_mapa and caminho_livre:
                    
                    novo_custo_g = custos_g[atual] + 1 # o custo g(n) do vizinho é o custo do nó atual + 1 (peso do passo)
                    
                    # relaxamento de aresta: se o vizinho nunca foi visitado ou se foi encontrado um caminho mais barato que o caminho anterior
                    if novo_custo_g < custos_g.get(prox_estado, float('inf')):
                        pais[prox_estado] = (atual, acao) # registra que o melhor caminho para o vizinho vem do nó atual
                        custos_g[prox_estado] = novo_custo_g # atualiza o custo oficial para chegar nele
                        f_score = novo_custo_g + self._heuristica(prox_estado, destino) # calcula a função f(n) = g(n) + h(n)
                        
                        heapq.heappush(fila, (f_score, next(contador_desempate), prox_estado)) # adiciona na fila de prioridade para ser explorado no futuro
                        
        return [] # se a fila esvaziar e o destino não for encontrado o caminho é impossível, retorna vazio

    # método que decide o que o carro vai fazer (chamado a cada turno)
    def escolher_acao(self, estado: Tuple[int, int], ambiente) -> Acao:
        # se não há plano na memória aciona o A-Estrela para calcular um
        if not self.caminho_planejado:
            self.caminho_planejado = self._planejar_caminho(estado, ambiente)

        if self.caminho_planejado:
            # verifica a próxima ação sem removê-la ainda
            proxima_acao = self.caminho_planejado[0]
            # prevê onde o carro vai parar se executar a ação
            prox_estado = self._obter_coordenada_acao(estado, proxima_acao)

            # se tiver um pedestre no próximo bloco o agente deve parar, o plano não é descartado, apenas freia por esse turno
            if prox_estado in ambiente.pedestres:
                return Acao.PARAR 

            # se tiver um carro no próximo bloco, a rota foi bloqueada
            if prox_estado in ambiente.carros_dinamicos:
                self.caminho_planejado = self._planejar_caminho(estado, ambiente) # joga o plano fora e calcula uma nova rota
                if self.caminho_planejado: # se encontrou um desvio válido, remove a primeira ação do novo plano e executa
                    return self.caminho_planejado.pop(0)
                return Acao.PARAR # se não há desvio possível o agente está preso e deve parar
                
            return self.caminho_planejado.pop(0) # se o caminho está livre de pedestres e carros dinâmicos, tira a ação da lista e a devolve para o ambiente executar
            
        return Acao.PARAR # caso de fallback extremo (destino inalcançável e sem plano), não faz nada
    