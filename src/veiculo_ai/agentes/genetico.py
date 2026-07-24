import random
from collections import deque
from typing import List, Tuple

from .base import AgenteBase
from src.veiculo_ai.ambiente.transito import Acao


class AgenteGenetico(AgenteBase):
    def __init__(
        self,
        nome: str = "Algoritmo Genético",
        tamanho_populacao: int = 300,
        tamanho_cromossomo: int = 50
    ):
        super().__init__(nome)

        # define a quantidade de indivíduos existentes em cada geração
        self.tamanho_populacao = tamanho_populacao

        # define o tamanho máximo do cromossomo utilizado pelo algoritmo genético
        self.tamanho_cromossomo = tamanho_cromossomo

        # utiliza 'deque' para permitir a extração da primeira ação em tempo constante O(1)
        self.melhor_sequencia: deque[Acao] = deque()

        # armazena uma rota temporária utilizada quando a rota original fica bloqueada por um obstáculo dinâmico
        self.rota_desvio: deque[Acao] = deque()

        # armazena as posições visitadas durante a execução do agente para evitar que o agente fique andando em círculos
        self.posicoes_visitadas = set()

        # cache do mapa de distâncias reais calculado pelo BFS a partir do destino e respeitando os obstáculos estáticos
        self._mapa_distancias: dict[Tuple[int, int], int] = {}

        # define a maior distância utilizada quando uma posição não é alcançável
        self._pior_caso_distancia: int = 0

        # armazena a rota mínima encontrada pelo BFS no mapa estático
        self._rota_bfs: List[Acao] = []

    def _calcular_posicao_futura(self, estado: Tuple[int, int], acao: Acao) -> Tuple[int, int]:
        # separa a posição atual em linha e coluna
        linha, coluna = estado

        # movimenta o agente um bloco para cima
        if acao == Acao.CIMA:
            linha -= 1

        # movimenta o agente um bloco para baixo
        elif acao == Acao.BAIXO:
            linha += 1

        # move o agente um bloco para a esquerda
        elif acao == Acao.ESQUERDA:
            coluna -= 1

        # move o agente um bloco para a direita
        elif acao == Acao.DIREITA:
            coluna += 1

        # mantém o agente na posição atual
        return linha, coluna

    def _calcular_mapa_distancias(self, ambiente) -> None:
        # obtém a posição final que deve ser alcançada pelo agente
        destino = ambiente.posicao_destino

        # cria o dicionário que armazenará a menor distância entre cada posição acessível e o destino
        distancias = {
            destino: 0
        }

        # utiliza uma fila para realizar a busca em largura
        fila = deque([destino])

        # executa a busca enquanto existirem posições para visitar
        while fila:

            # remove a primeira posição da fila
            atual = fila.popleft()

            # separa a posição atual em linha e coluna
            linha, coluna = atual

            # define as quatro posições vizinhas possíveis
            vizinhos = [
                (linha - 1, coluna),
                (linha + 1, coluna),
                (linha, coluna - 1),
                (linha, coluna + 1)
            ]

            # percorre todas as posições vizinhas
            for vizinho in vizinhos:

                # separa a posição vizinha em linha e coluna
                vl, vc = vizinho

                # verifica se a posição está dentro dos limites da matriz
                dentro = (
                    0 <= vl < ambiente.tamanho_grade
                    and
                    0 <= vc < ambiente.tamanho_grade
                )

                # verifica se a posição é válida para navegação e se ainda não foi visitada
                if (dentro and vizinho not in distancias and vizinho not in ambiente.obstaculos):
                    # registra a distância mínima da posição vizinha até o destino
                    distancias[vizinho] = (distancias[atual] + 1)

                    # adiciona a nova posição ao final da fila
                    fila.append(vizinho)

        # salva o mapa de distâncias calculado pelo BFS
        self._mapa_distancias = distancias

        # define uma distância de segurança para posições que não foram alcançadas pelo BFS
        self._pior_caso_distancia = (ambiente.tamanho_grade * ambiente.tamanho_grade)

    def _distancia_real(self, posicao: Tuple[int, int]) -> int:
        # retorna a menor distância conhecida pelo BFS
        # caso a posição não exista no mapa, utiliza o pior caso
        return self._mapa_distancias.get(
            posicao,
            self._pior_caso_distancia
        )

    def _encontrar_rota_bfs(self, ambiente, inicio: Tuple[int, int]) -> List[Acao]:
        # obtém a posição final do agente
        destino = ambiente.posicao_destino

        # verifica se o agente já está no destino
        if inicio == destino:
            return []

        # cria uma fila contendo a posição inicial
        fila = deque([
            inicio
        ])

        # armazena a posição anterior de cada célula visitada
        anteriores = {
            inicio: None
        }

        # armazena a ação utilizada para chegar em cada posição
        acoes_usadas = {}

        # define os movimentos possíveis utilizados pelo BFS
        movimentos = [
            (Acao.CIMA, (-1, 0)),
            (Acao.BAIXO, (1, 0)),
            (Acao.ESQUERDA, (0, -1)),
            (Acao.DIREITA, (0, 1))
        ]

        # executa a busca enquanto existirem posições na fila
        while fila:

            # remove a primeira posição da fila
            atual = fila.popleft()

            # verifica se o destino foi encontrado
            if atual == destino:
                break

            # verifica cada movimento possível
            for acao, (dl, dc) in movimentos:

                # calcula a posição que seria alcançada
                nova_posicao = (
                    atual[0] + dl,
                    atual[1] + dc
                )

                # verifica se a nova posição está dentro do mapa
                dentro = (
                    0 <= nova_posicao[0] < ambiente.tamanho_grade
                    and
                    0 <= nova_posicao[1] < ambiente.tamanho_grade
                )

                # ignora posições fora dos limites da matriz
                if not dentro:
                    continue

                # ignora obstáculos estáticos
                if nova_posicao in ambiente.obstaculos:
                    continue

                # ignora posições já visitadas pelo BFS
                if nova_posicao in anteriores:
                    continue

                # registra de onde a nova posição foi alcançada
                anteriores[nova_posicao] = atual

                # registra qual ação foi utilizada para chegar na posição
                acoes_usadas[nova_posicao] = acao

                # adiciona a nova posição à fila
                fila.append(nova_posicao)

        # verifica se o destino não foi encontrado
        if destino not in anteriores:
            return []

        # cria uma lista temporária para reconstruir o caminho
        caminho = []

        # começa a reconstrução pelo destino
        atual = destino

        # percorre o caminho de trás para frente até chegar ao início
        while atual != inicio:

            # obtém a ação que levou até a posição atual
            acao = acoes_usadas[atual]

            # adiciona a ação ao caminho
            caminho.append(acao)

            # volta para a posição anterior
            atual = anteriores[atual]

        # inverte a sequência para obter a rota do início até o destino
        caminho.reverse()

        # retorna a rota mínima encontrada pelo BFS
        return caminho

    def _gerar_populacao_inicial(self, ambiente) -> List[List[Acao]]:
        # encontra a rota mínima entre o início e o destino
        rota_base = self._encontrar_rota_bfs(ambiente, ambiente.posicao_inicial)

        # salva a rota mínima encontrada pelo BFS
        self._rota_bfs = rota_base.copy()

        # cria a população inicial vazia
        populacao = []

        # adiciona a rota mínima diretamente à população
        # garantindo que o agente comece com pelo menos uma solução válida
        if rota_base:

            # completa a rota até o tamanho do cromossomo
            cromossomo = rota_base.copy()

            while len(cromossomo) < self.tamanho_cromossomo:

                # adiciona uma ação aleatória ao final do cromossomo
                cromossomo.append(
                    random.choice([
                        Acao.CIMA,
                        Acao.BAIXO,
                        Acao.ESQUERDA,
                        Acao.DIREITA
                    ])
                )

            # adiciona o indivíduo baseado na rota BFS
            populacao.append(
                cromossomo
            )

        # cria os demais indivíduos da população
        while len(populacao) < self.tamanho_populacao:

            # cria um novo cromossomo vazio
            individuo = []

            # gera cada gene do indivíduo
            for _ in range(self.tamanho_cromossomo):

                # não adiciona parar aos cromossomos porque a parada será controlada durante a execução
                individuo.append(
                    random.choice([
                        Acao.CIMA,
                        Acao.BAIXO,
                        Acao.ESQUERDA,
                        Acao.DIREITA
                    ])
                )

            # adiciona o indivíduo à população
            populacao.append(individuo)

        # retorna a população inicial criada
        return populacao
    
    def _calcular_aptidao(self, individuo: List[Acao], ambiente, repeticoes: int = 3) -> float:
        # avalia o mesmo indivíduo várias vezes
        # porque o ambiente possui eventos dinâmicos aleatórios
        notas = [
            self._avaliar_uma_vez(individuo, ambiente)
            for _ in range(repeticoes)
        ]

        # retorna a média das avaliações realizadas
        return sum(notas) / len(notas)

    def _avaliar_uma_vez(self, individuo: List[Acao], ambiente) -> float:
        # reinicia o ambiente para garantir que o indivíduo sempre comece a avaliação na posição inicial
        ambiente.reset()

        # obtém a posição inicial do agente
        estado = ambiente.posicao_agente

        # obtém a distância inicial até o destino utilizando BFS
        distancia_anterior = self._distancia_real(estado)

        # inicia a pontuação do indivíduo
        fitness = 0.0

        # armazena as posições visitadas durante a avaliação
        visitadas = set()

        # registra a posição inicial como visitada
        visitadas.add(estado)

        # executa cada ação existente no cromossomo
        for indice, acao in enumerate(individuo):

            # impede que o indivíduo continue sendo avaliado depois que o limite de passos foi atingido
            if indice >= ambiente.limite_passos:
                break

            # impede que parar seja utilizado durante o treinamento porque a parada deve ser utilizada para eventos dinâmicos
            if acao == Acao.PARAR:
                continue

            # executa a ação no ambiente
            novo_estado, recompensa, finalizado, info = ambiente.step(acao)

            # verifica se o agente alcançou o destino
            if info.get("sucesso", False):

                # concede uma grande recompensa pelo sucesso
                # e uma recompensa adicional pela eficiência da rota
                fitness += 10000.0

                # quanto menos passos forem utilizados,
                # maior será a recompensa final
                fitness += (ambiente.limite_passos - ambiente.passos_dados) * 20.0

                # encerra a avaliação porque o objetivo foi alcançado
                return fitness

            # verifica se ocorreu uma colisão
            if info.get("colisao", False):

                # aplica uma grande penalização pela colisão
                fitness -= 5000.0

                # calcula a distância restante até o destino
                distancia_atual = self._distancia_real(novo_estado)

                # ainda considera a distância restante
                # para diferenciar indivíduos que chegaram mais perto
                fitness += (100.0 / (distancia_atual + 1))

                # encerra a avaliação após a colisão
                return fitness

            # calcula a distância atual até o destino
            distancia_atual = self._distancia_real(novo_estado)

            # calcula quanto o indivíduo avançou em direção ao destino
            progresso = (distancia_anterior - distancia_atual)

            # recompensa movimentos que aproximam o agente do destino
            fitness += (progresso * 20.0)

            # penaliza movimentos que afastam o agente do destino
            if progresso < 0:

                # aplica uma penalização proporcional ao retrocesso
                fitness += (progresso * 30.0)

            # verifica se o agente voltou para uma posição já visitada
            if novo_estado in visitadas:

                # aplica uma penalização por ficar andando em círculos
                fitness -= 30.0

            # adiciona a nova posição ao conjunto de posições visitadas
            visitadas.add(novo_estado)

            # atualiza a distância anterior para o próximo passo
            distancia_anterior = distancia_atual

            # aplica uma pequena penalização por cada passo utilizado
            # incentivando o agente a encontrar caminhos menores
            fitness -= 1.0

            # verifica se o ambiente terminou por esgotamento de passos
            if finalizado:

                # aplica a penalização correspondente ao esgotamento do tempo
                fitness -= 1000.0

                # encerra a avaliação do indivíduo
                return fitness

        # ao terminar o cromossomo sem chegar ao destino,
        # recompensa o indivíduo de acordo com a proximidade final
        distancia_final = self._distancia_real(estado)

        # adiciona uma recompensa baseada na distância restante
        fitness += (500.0 / (distancia_final + 1))

        # retorna o fitness final calculado
        return fitness

    def _selecao_torneio(self, aptidoes: List[Tuple[List[Acao], float]], k: int = 3) -> List[Acao]:
        # seleciona aleatoriamente alguns indivíduos da população
        # permitindo que indivíduos bons e medianos tenham alguma chance de participar da reprodução
        competidores = random.sample(aptidoes, min(k, len(aptidoes)))

        # seleciona o indivíduo com maior valor de aptidão
        vencedor = max(competidores, key=lambda x: x[1])

        # retorna somente o cromossomo do indivíduo vencedor
        return vencedor[0]

    def _cruzar(self, pai1: List[Acao], pai2: List[Acao]) -> List[Acao]:
        # define aleatoriamente o ponto onde os cromossomos serão divididos
        ponto = random.randint(1, self.tamanho_cromossomo - 1)

        # combina a primeira parte do primeiro pai
        # com a segunda parte do segundo pai
        filho = (pai1[:ponto] + pai2[ponto:])

        # retorna o novo cromossomo gerado
        return filho

    def _mutar(self, filho: List[Acao], taxa_mutacao: float = 0.05) -> None:
        # percorre todos os genes existentes no cromossomo
        for i in range(len(filho)):
            # verifica se o gene sofrerá mutação
            if random.random() < taxa_mutacao:

                # substitui o gene por uma nova ação de movimento
                # parar não é utilizado durante a evolução
                filho[i] = random.choice([
                    Acao.CIMA,
                    Acao.BAIXO,
                    Acao.ESQUERDA,
                    Acao.DIREITA
                ])

    def treinar(self, ambiente, episodios: int = 100) -> None:
        # exibe uma mensagem informando o início do treinamento
        print(
            f"Evoluindo {self.nome} por {episodios} gerações..."
        )

        # calcula o mapa de distâncias utilizando BFS antes do início do processo evolutivo
        self._calcular_mapa_distancias(ambiente)

        # gera uma população inicial contendo indivíduos aleatórios e uma rota baseada no BFS
        populacao = self._gerar_populacao_inicial(ambiente)

        # executa o processo evolutivo durante a quantidade de gerações definida
        for geracao in range(episodios):
            # avalia todos os indivíduos da população atual
            aptidoes = [
                (
                    individuo,
                    self._calcular_aptidao(individuo, ambiente)
                )
                for individuo in populacao
            ]

            # ordena os indivíduos do melhor para o pior fitness
            aptidoes.sort(key=lambda x: x[1], reverse=True)

            # preserva os 10% melhores indivíduos para evitar que boas soluções sejam perdidas
            quantidade_elite = max(1, int(self.tamanho_populacao * 0.10))

            # copia os indivíduos elite para a próxima geração
            nova_populacao = [
                individuo.copy()
                for individuo, _ in aptidoes[
                    :quantidade_elite
                ]
            ]

            # continua criando novos indivíduos
            # até completar o tamanho da população
            while len(nova_populacao) < self.tamanho_populacao:

                # seleciona o primeiro pai utilizando torneio
                pai1 = self._selecao_torneio(aptidoes)

                # seleciona o segundo pai utilizando torneio
                pai2 = self._selecao_torneio(aptidoes)

                # realiza o cruzamento entre os dois pais
                filho = self._cruzar(pai1, pai2)

                # aplica mutação no novo indivíduo
                self._mutar(filho)

                # adiciona o novo indivíduo à população
                nova_populacao.append(filho)

            # substitui a população antiga pela nova geração
            populacao = nova_populacao

            # exibe o melhor fitness encontrado periodicamente
            if (geracao + 1) % 10 == 0:

                # obtém o melhor fitness da geração atual
                melhor_fitness = aptidoes[0][1]

                # exibe o progresso do treinamento
                print(
                    f"Geração {geracao + 1}: "
                    f"melhor fitness = {melhor_fitness:.2f}"
                )

        # realiza a avaliação final da população treinada
        aptidoes_finais = [
            (
                individuo,
                self._calcular_aptidao(individuo, ambiente)
            )
            for individuo in populacao
        ]

        # seleciona o indivíduo com maior fitness
        melhor_individuo = max(aptidoes_finais, key=lambda x: x[1])

        # obtém o cromossomo do melhor indivíduo
        melhor_lista = melhor_individuo[0]

        # obtém o fitness final do melhor indivíduo
        melhor_fitness = melhor_individuo[1]

        # salva a melhor sequência genética
        self.melhor_sequencia = deque(melhor_lista)

        # limpa qualquer rota temporária de desvio anterior
        self.rota_desvio.clear()

        # limpa o histórico de posições visitadas
        self.posicoes_visitadas.clear()

        # informa que o treinamento foi concluído
        print( "Treinamento concluído.")

        # exibe o fitness final encontrado pelo algoritmo genético
        print(
            f"Melhor fitness final: "
            f"{melhor_fitness:.2f}"
        )

    def _acao_segura(self, estado: Tuple[int, int], acao: Acao, ambiente) -> bool:
        # ignora a ação parar porque ela não representa um movimento
        if acao == Acao.PARAR:
            return True

        # calcula a posição que será alcançada pela ação
        nova_posicao = self._calcular_posicao_futura(estado, acao)

        # separa a nova posição em linha e coluna
        linha, coluna = nova_posicao

        # verifica se a nova posição está dentro dos limites da matriz
        dentro = (
            0 <= linha < ambiente.tamanho_grade
            and
            0 <= coluna < ambiente.tamanho_grade
        )

        # impede que o agente tente sair do mapa
        if not dentro:
            return False

        # impede colisões com obstáculos estáticos
        if nova_posicao in ambiente.obstaculos:
            return False

        # impede colisões com carros dinâmicos
        if nova_posicao in ambiente.carros_dinamicos:
            return False

        # impede que o agente avance sobre um pedestre ativo
        if nova_posicao in ambiente.pedestres:
            return False

        # se nenhuma condição de colisão foi encontrada,
        # considera a ação segura
        return True
    
    def _encontrar_desvio(self, estado: Tuple[int, int], ambiente) -> List[Acao]:
        # define os movimentos possíveis
        movimentos = [
            Acao.CIMA,
            Acao.BAIXO,
            Acao.ESQUERDA,
            Acao.DIREITA
        ]

        # cria uma fila contendo a posição atual
        fila = deque([estado])

        # armazena a posição anterior de cada célula visitada
        anteriores = {
            estado: None
        }

        # armazena a ação utilizada para chegar em cada posição
        acoes_usadas = {}

        # realiza uma busca em largura para encontrar
        # o caminho mais curto até o destino evitando obstáculos atuais
        while fila:

            # remove a primeira posição da fila
            atual = fila.popleft()

            # verifica se o destino foi encontrado
            if atual == ambiente.posicao_destino:
                break

            # verifica todos os movimentos possíveis
            for acao in movimentos:

                # calcula a posição que seria alcançada
                nova_posicao = self._calcular_posicao_futura(atual, acao)

                # verifica se a ação pode ser executada
                if not self._acao_segura(atual, acao, ambiente):
                    continue

                # evita posições que já foram visitadas pelo BFS
                if nova_posicao in anteriores:
                    continue

                # evita retornar para posições já percorridas pelo agente
                # sempre que existir uma alternativa disponível
                if (nova_posicao in self.posicoes_visitadas and nova_posicao != ambiente.posicao_destino):
                    continue

                # registra a posição anterior
                anteriores[nova_posicao] = atual

                # registra a ação utilizada
                acoes_usadas[nova_posicao] = acao

                # adiciona a posição à fila
                fila.append(
                    nova_posicao
                )

        # verifica se o destino não foi encontrado
        if ambiente.posicao_destino not in anteriores:
            return []

        # cria uma lista temporária para reconstruir a rota
        caminho = []

        # começa a reconstrução pelo destino
        atual = ambiente.posicao_destino

        # percorre o caminho de trás para frente
        while atual != estado:

            # recupera a ação utilizada para chegar na posição atual
            acao = acoes_usadas[atual]

            # adiciona a ação à rota
            caminho.append(acao)

            # retorna para a posição anterior
            atual = anteriores[atual]

        # inverte a rota para obter a ordem correta
        caminho.reverse()

        # retorna a rota temporária encontrada
        return caminho

    def escolher_acao(self, estado: Tuple[int, int], ambiente) -> Acao:
        # registra a posição atual como visitada
        self.posicoes_visitadas.add(estado)

        # verifica se o ambiente possui o método de identificação de pedestres
        if hasattr(ambiente, "tem_pedestre_na_frente"):

            # verifica se existe um pedestre bloqueando a próxima ação
            if (self.melhor_sequencia and ambiente.tem_pedestre_na_frente(self.melhor_sequencia[0])):
                # permanece parado até o pedestre desaparecer
                return Acao.PARAR

        # verifica se existe uma rota temporária disponível
        if self.rota_desvio:
            # obtém a próxima ação do desvio
            acao = self.rota_desvio[0]

            # verifica se a ação continua segura
            if self._acao_segura(estado, acao, ambiente):
                # remove a ação somente quando ela será executada
                self.rota_desvio.popleft()

                # retorna a ação do desvio
                return acao

            # descarta a rota temporária caso ela tenha ficado inválida
            self.rota_desvio.clear()

        # caso não existam mais ações na rota tenta encontrar uma nova rota utilizando BFS
        if not self.melhor_sequencia:

            # encontra uma rota segura até o destino
            nova_rota = self._encontrar_desvio(estado, ambiente)

            # salva a nova rota temporária
            self.rota_desvio = deque(nova_rota)

            # verifica se foi possível encontrar uma nova rota
            if self.rota_desvio:
                # remove e executa a primeira ação da nova rota
                return self.rota_desvio.popleft()

            # caso nenhuma rota seja encontrada permanece parado para evitar colisão
            return Acao.PARAR

        # consulta a primeira ação sem removê-la da sequência
        proxima_acao = self.melhor_sequencia[0]

        # verifica se a ação planejada pode ser executada
        if self._acao_segura(estado, proxima_acao, ambiente):
            # remove a ação da rota somente porque ela será executada neste passo
            self.melhor_sequencia.popleft()

            # retorna a ação planejada pelo algoritmo
            return proxima_acao

        # caso a próxima ação esteja bloqueada calcula uma nova rota temporária até o destino
        nova_rota = self._encontrar_desvio(estado, ambiente)

        # salva a nova rota encontrada
        self.rota_desvio = deque(nova_rota)

        # verifica se existe uma rota temporária válida
        if self.rota_desvio:
            # remove e executa a primeira ação do desvio
            return self.rota_desvio.popleft()

        # caso o agente não consiga encontrar nenhum movimento seguro permanece parado para evitar uma colisão
        return Acao.PARAR
