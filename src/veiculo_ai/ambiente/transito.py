from enum import IntEnum
from typing import Tuple, Dict, Any
import random

class Acao(IntEnum):
    CIMA = 0
    BAIXO = 1
    ESQUERDA = 2
    DIREITA = 3
    PARAR = 4

class Transito:
    def __init__(self):
        self.tamanho_grade = 10
        self.posicao_inicial = (0, 0)
        self.posicao_destino = (9, 9)

        # matriz do mapa
        self.mapa = [
            [0, 0, 2, 2, 0, 0, 2, 2, 2, 2],
            [0, 0, 2, 2, 0, 0, 2, 2, 2, 2],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [2, 2, 0, 0, 2, 2, 0, 0, 2, 2],
            [2, 2, 0, 0, 2, 2, 0, 0, 2, 2],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [2, 2, 0, 0, 2, 2, 0, 0, 0, 0],
            [2, 2, 0, 0, 2, 2, 0, 0, 0, 0]
        ]

        # configuração dos obstáculos
        self.obstaculos = []
        for linha in range(self.tamanho_grade):
            for coluna in range(self.tamanho_grade):
                if self.mapa[linha][coluna] in [1, 2]:
                    self.obstaculos.append((linha, coluna))

        # armazena as posições dos carros atualmente ativos
        self.carros_dinamicos = []
        # armazena o tempo restante de cada carro ativo
        self.carros_timers = {}
        # armazena as posições dos pedestres atualmente ativos
        self.pedestres = []
        # armazena o tempo restante de cada pedestre ativo
        self.pedestres_timers = {}

        # configuração das recompensas
        self.limite_passos = 100
        self.recompensa_sucesso = 100.0
        self.recompensa_colisao = -100.0
        self.recompensa_esgotamento = -10.0
        self.recompensa_passo = -1.0
        self.recompensa_parar = -0.1
        self.recompensa_regressao = -5.0

        # posição atual do agente dentro da matriz
        self.posicao_agente = self.posicao_inicial

        # quantidade de passos realizados na simulação atual
        self.passos_dados = 0

        # indica se a simulação já foi encerrada
        self.finalizado = False

        # armazena a última ação de movimento realizada para identificar quando o agente está regressando
        self.ultima_acao = None

    def reset(self) -> Tuple[int, int]:
        # retorna o agente para a posição inicial
        self.posicao_agente = self.posicao_inicial
        # reinicia a quantidade de passos realizados
        self.passos_dados = 0
        # indica que uma nova simulação está começando
        self.finalizado = False
        # remove todos os carros ativos
        self.carros_dinamicos.clear()
        # remove os temporizadores dos carros
        self.carros_timers.clear()
        # remove todos os pedestres ativos
        self.pedestres.clear()
        # remove os temporizadores dos pedestres
        self.pedestres_timers.clear()
        # não existe ação anterior no início da simulação
        self.ultima_acao = None

        # retorna a posição inicial do agente
        return self.posicao_agente

    def _calcular_posicao_futura(self, posicao: Tuple[int, int], acao: Acao) -> Tuple[int, int]:
        # calcula a posição que o agente tentaria ocupar ao executar determinada ação
        linha, coluna = posicao

        # verifica se a ação consiste em subir uma linha
        if acao == Acao.CIMA:
            linha -= 1
        # verifica se a ação consiste em descer uma linha
        elif acao == Acao.BAIXO:
            linha += 1
        # verifica se a ação consiste em mover uma coluna para a esquerda
        elif acao == Acao.ESQUERDA:
            coluna -= 1
        # verifica se a ação consiste em mover uma coluna para a direita
        elif acao == Acao.DIREITA:

            coluna += 1

        # retorna a posição calculada sem alterar a posição real do agente
        return (linha, coluna)

    def tem_pedestre_na_frente(self, acao: Acao) -> bool:
        # a ação parar não possui uma posição futura
        if acao == Acao.PARAR:
            return False

        # calcula a posição que o agente tentaria ocupar
        nova_posicao = self._calcular_posicao_futura(self.posicao_agente, acao)

        # retorna True caso exista um pedestre exatamente na posição futura
        return (nova_posicao in self.pedestres)

    def tem_carro_na_frente(self, acao: Acao) -> bool:
        # a ação parar não possui uma posição futura
        if acao == Acao.PARAR:
            return False

        # calcula a posição que o agente tentaria ocupar
        nova_posicao = self._calcular_posicao_futura(self.posicao_agente, acao)

        # retorna True caso exista um carro exatamente na posição futura
        return (nova_posicao in self.carros_dinamicos)

    def movimento_valido(self, acao: Acao) -> bool:
        # parar sempre é uma ação válida porque não altera a posição do agente
        if acao == Acao.PARAR:
            return True

        # calcula a posição que o agente tentaria ocupar
        nova_posicao = self._calcular_posicao_futura(self.posicao_agente, acao)
        linha, coluna = nova_posicao

        # verifica se a posição futura está fora da matriz
        if (linha < 0 or linha >= self.tamanho_grade or coluna < 0 or coluna >= self.tamanho_grade):
            return False

        # verifica se a posição futura contém um obstáculo fixo
        if nova_posicao in self.obstaculos:
            return False

        # verifica se existe um carro ocupando a posição futura
        if nova_posicao in self.carros_dinamicos:
            return False

        # verifica se existe um pedestre ocupando a posição futura
        if nova_posicao in self.pedestres:
            return False

        # caso nenhuma condição de colisão seja encontrada o movimento pode ser executado
        return True

    def _atualizar_carros(self) -> None:
        # cria um novo dicionário contendo somente os carros que ainda permanecem ativos no ambiente
        carros_vivos = {}

        # percorre todos os carros atualmente ativos
        for pos, tempo_restante in self.carros_timers.items():
            # verifica se o carro ainda possui tempo de permanência
            if tempo_restante > 1:
                # mantém o carro ativo e reduz seu tempo de permanência
                carros_vivos[pos] = (tempo_restante - 1)

        # substitui os carros antigos pelos carros que ainda estão ativos
        self.carros_timers = carros_vivos

        # atualiza a lista de posições ocupadas pelos carros atualmente ativos
        self.carros_dinamicos = list(self.carros_timers.keys())

    def _atualizar_pedestres(self) -> None:
        # cria um novo dicionário contendo somente os pedestres que ainda permanecem ativos no ambiente
        pedestres_vivos = {}

        # percorre todos os pedestres atualmente ativos
        for pos, tempo_restante in self.pedestres_timers.items():
            # verifica se o pedestre ainda possui tempo de permanência
            if tempo_restante > 1:
                # mantém o pedestre ativo e reduz seu tempo de permanência
                pedestres_vivos[pos] = (tempo_restante - 1)

        # substitui os pedestres antigos pelos pedestres que ainda estão ativos
        self.pedestres_timers = pedestres_vivos

        # atualiza a lista de posições ocupadas pelos pedestres atualmente ativos
        self.pedestres = list(self.pedestres_timers.keys())

    def _gerar_evento_dinamico(self) -> None:
        # existe uma probabilidade de 20% de surgir um novo evento a cada passo da simulação
        if random.random() >= 0.20:
            return
        
        # sorteia aleatoriamente uma linha dentro da matriz
        nova_l = random.randint(0, self.tamanho_grade - 1)

        # sorteia aleatoriamente uma coluna dentro da matriz
        nova_c = random.randint(0, self.tamanho_grade - 1)

        # cria a posição sorteada para o novo evento
        pos = (nova_l, nova_c)

        # verifica se a posição sorteada está disponível
        posicao_livre = (
            pos != self.posicao_agente
            and
            pos != self.posicao_destino
            and
            pos not in self.obstaculos
            and
            pos not in self.carros_dinamicos
            and
            pos not in self.pedestres
        )

        # caso a posição não esteja livre nenhum novo evento será criado
        if not posicao_livre:
            return

        # existe 50% de chance de o evento ser um pedestre
        if random.random() < 0.5:
            # adiciona o pedestre com duração de 4 passos
            self.pedestres_timers[pos] = 4

            # atualiza a lista de posições dos pedestres
            self.pedestres = list(self.pedestres_timers.keys())
        # caso contrário, o evento será um carro
        else:
            # adiciona o carro com duração de 8 passos
            self.carros_timers[pos] = 8

            # atualiza a lista de posições dos carros
            self.carros_dinamicos = list(self.carros_timers.keys())


    def step(self, acao: Acao) -> Tuple[Tuple[int, int], float, bool, Dict[str, Any]]:
        # verifica se a simulação já foi finalizada anteriormente
        if self.finalizado:
            raise RuntimeError("A simulação acabou.")

        # incrementa a quantidade de passos realizados
        self.passos_dados += 1

        # inicializa as informações retornadas pela simulação
        info = {
            "status": "Navegando",
            "sucesso": False,
            "colisao": False
        }

        # atualiza o tempo de vida dos carros
        # antes de processar a ação atual
        self._atualizar_carros()

        # atualiza o tempo de vida dos pedestres
        # antes de processar a ação atual
        self._atualizar_pedestres()

        # quando o agente recebe a ação parar permanece na posição atual
        if acao == Acao.PARAR:
            # define o status atual da simulação
            info["status"] = "Parado aguardando"

            # aplica uma pequena penalização por permanecer parado
            recompensa = self.recompensa_parar

            # verifica se o limite máximo foi atingido enquanto parado
            if self.passos_dados >= self.limite_passos:
                # encerra a simulação por tempo esgotado
                self.finalizado = True

                # atualiza o status da simulação
                info["status"] = "Tempo Esgotado!"

                # aplica a penalização de timeout
                recompensa = self.recompensa_esgotamento

            # retorna a posição atual sem realizar movimento
            return (self.posicao_agente, recompensa, self.finalizado, info)

        # tenta gerar um novo carro ou pedestre para representar o trânsito dinâmico
        self._gerar_evento_dinamico()

        # inicialmente considera que não houve regressão
        regrediu = False

        # verifica se existe uma ação anterior
        if self.ultima_acao is not None:
            # define quais ações são diretamente opostas
            opostas = {
                Acao.CIMA: Acao.BAIXO,
                Acao.BAIXO: Acao.CIMA,
                Acao.ESQUERDA: Acao.DIREITA,
                Acao.DIREITA: Acao.ESQUERDA
            }

            # verifica se a ação atual é oposta à última ação realizada
            if (opostas.get(self.ultima_acao) == acao):
                # registra que o agente voltou pelo caminho anterior
                regrediu = True

        # calcula a posição para a qual o agente tentará se mover
        nova_posicao = self._calcular_posicao_futura(self.posicao_agente, acao)

        # separa a posição futura em linha e coluna
        linha, coluna = nova_posicao

        # verifica se a linha ultrapassou os limites da matriz
        linha_fora_da_grade = (linha < 0 or linha >= self.tamanho_grade)

        # verifica se a coluna ultrapassou os limites da matriz
        coluna_fora_da_grade = (coluna < 0 or coluna >= self.tamanho_grade)

        # verifica se o agente tentou sair pelos limites da matriz
        bateu_borda = (linha_fora_da_grade or coluna_fora_da_grade)

        # verifica se a nova posição contém um obstáculo estático
        bateu_estatico = (nova_posicao in self.obstaculos)

        # verifica se existe um carro na posição que o agente deseja ir
        bateu_carro = (nova_posicao in self.carros_dinamicos)

        # verifica se existe um pedestre na posição para que o agente deseja ir
        atropelou = (nova_posicao in self.pedestres)

        # verifica se ocorreu algum tipo de colisão
        if (bateu_borda or bateu_estatico or bateu_carro or atropelou):
            # encerra a simulação imediatamente após ocorrer uma colisão
            self.finalizado = True

            # verifica o tipo de colisão e atualiza o respectivo status
            if atropelou:
                info["status"] = "Atropelamento!"
            elif bateu_carro:
                info["status"] = "Colisão com carro!"
            else:
                info["status"] = "Colisão Grave!"
            info["colisao"] = True

            # retorna a posição anterior do agente, a penalização e o estado finalizado
            return (self.posicao_agente, self.recompensa_colisao, self.finalizado, info)

        # atualiza a posição oficial do agente porque nenhum obstáculo foi atingido
        self.posicao_agente = nova_posicao

        # verifica se o agente chegou ao destino final
        if (self.posicao_agente == self.posicao_destino):
            # encerra a simulação porque o objetivo foi alcançado
            self.finalizado = True

            # atualiza o status da simulação
            info["status"] = "Destino Alcançado!"

            # informa que a execução terminou com sucesso
            info["sucesso"] = True

            # aplica a recompensa máxima
            recompensa = self.recompensa_sucesso

            # registra a última ação realizada
            self.ultima_acao = acao

            # retorna o resultado da execução
            return (self.posicao_agente, recompensa, self.finalizado, info)

        # verifica se o limite máximo de passos foi atingido
        if (self.passos_dados >= self.limite_passos):
            # encerra a simulação por esgotamento
            self.finalizado = True

            # atualiza o status da simulação
            info["status"] = "Tempo Esgotado!"

            # aplica a penalização de esgotamento
            recompensa = self.recompensa_esgotamento

            # registra a última ação realizada
            self.ultima_acao = acao

            # retorna o resultado final da simulação
            return (self.posicao_agente, recompensa, self.finalizado, info)

        # aplica a penalização padrão por realizar um passo incentivando o agente a encontrar caminhos mais curtos
        recompensa = self.recompensa_passo

        # verifica se o agente voltou diretamente para a posição anterior
        if regrediu:
            # adiciona a penalização de regressão
            recompensa += self.recompensa_regressao

        # registra a ação atual como a última ação realizada
        self.ultima_acao = acao

        # retorna a nova posição, recompensa, estado finalizado e informações adicionais
        return (self.posicao_agente, recompensa, self.finalizado, info)
    