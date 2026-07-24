import os
import time
import pygame
from src.veiculo_ai.ambiente.transito import Transito, Acao
from src.veiculo_ai.agentes.heuristico import AgenteHeuristico
from src.veiculo_ai.agentes.genetico import AgenteGenetico
from src.veiculo_ai.agentes.qlearning import AgenteQLearning

# configurações de cores
COR_ASFALTO = (50, 50, 50)
COR_PREDIO = (150, 50, 50)
COR_CARRO = (50, 150, 255)
COR_DESTINO = (50, 200, 50)
COR_TEXTO = (255, 255, 255)

class Visualizador:
    def __init__(self, ambiente, tamanho_tile=50):
        pygame.init()
        self.ambiente = ambiente
        self.tamanho_tile = tamanho_tile
        
        largura = (ambiente.tamanho_grade * tamanho_tile) + 300
        altura = ambiente.tamanho_grade * tamanho_tile
        
        self.tela = pygame.display.set_mode((largura, altura))
        pygame.display.set_caption("Simulador Veículo Autônomo")
        self.fonte = pygame.font.SysFont("consolas", 18)
        self.usar_imagens = False 
        
        # definição das posições dos botões no painel
        self.x_painel = self.ambiente.tamanho_grade * self.tamanho_tile
        self.btn_heuristico = pygame.Rect(self.x_painel + 20, 250, 260, 40)
        self.btn_qlearning = pygame.Rect(self.x_painel + 20, 310, 260, 40)
        self.btn_genetico = pygame.Rect(self.x_painel + 20, 370, 260, 40)

    def desenhar_grade(self):
        # definição das paletas de cores padrão para os elementos do cenário urbano
        COR_RUA = (60, 60, 60)
        COR_FAIXA = (200, 200, 200)
        COR_GRAMA = (80, 160, 80)
        COR_PAREDE = (200, 180, 140)
        COR_TELHADO = (180, 60, 60)
        
        for linha in range(self.ambiente.tamanho_grade):
            for coluna in range(self.ambiente.tamanho_grade):
                x = coluna * self.tamanho_tile
                y = linha * self.tamanho_tile
                rect_base = pygame.Rect(x, y, self.tamanho_tile, self.tamanho_tile)
                
                terreno = self.ambiente.mapa[linha][coluna]

                # desenha o destino final se for a posição alvo
                if (linha, coluna) == self.ambiente.posicao_destino:
                    pygame.draw.rect(self.tela, COR_DESTINO, rect_base) 
                    pygame.draw.rect(self.tela, (0, 0, 0), rect_base, 3) 

                # desenha ruas com uma faixa pontilhada central
                elif terreno == 0:
                    pygame.draw.rect(self.tela, COR_RUA, rect_base)
                    traco_x = x + (self.tamanho_tile // 2) - 2
                    traco_y = y + (self.tamanho_tile // 2) - 8
                    pygame.draw.rect(self.tela, COR_FAIXA, (traco_x, traco_y, 4, 16))

                # desenha áreas de grama/calçada
                elif terreno == 1:
                    pygame.draw.rect(self.tela, COR_GRAMA, rect_base)

                # desenha construções/prédios com grama ao fundo, paredes e telhado
                elif terreno == 2:
                    pygame.draw.rect(self.tela, COR_GRAMA, rect_base) 
                    margem = 10
                    rect_casa = pygame.Rect(x + margem, y + margem, self.tamanho_tile - (margem*2), self.tamanho_tile - (margem*2))
                    pygame.draw.rect(self.tela, COR_PAREDE, rect_casa)
                    pygame.draw.rect(self.tela, COR_TELHADO, rect_casa)
                    pygame.draw.rect(self.tela, (50, 50, 50), rect_casa, 2) 

                # desenha carros no tráfego
                if (linha, coluna) in self.ambiente.carros_dinamicos:
                    self._desenhar_veiculo(linha, coluna, cor_carro=(200, 40, 40))

                # desenha pedestres ativos na travessia
                if (linha, coluna) in self.ambiente.pedestres:
                    self._desenhar_pedestre(linha, coluna)

    # desenha o veículo principal controlado pelo agente
    def desenhar_agente(self):
        linha, coluna = self.ambiente.posicao_agente
        self._desenhar_veiculo(linha, coluna, cor_carro=(40, 100, 200))

    # desenha uma seta indicativa sobre o veículo mostrando a direção da ação escolhida no turno
    def desenhar_seta(self, acao_tomada):
        # se o agente decidiu parar ou nenhuma ação foi informada, encerra o método sem desenhar
        if acao_tomada == Acao.PARAR or acao_tomada is None:
            return
            
        linha, coluna = self.ambiente.posicao_agente
        x_centro = coluna * self.tamanho_tile + (self.tamanho_tile // 2)
        y_centro = linha * self.tamanho_tile + (self.tamanho_tile // 2)
        offset = self.tamanho_tile // 4 
        cor_seta = (255, 255, 0)
        
        if acao_tomada == Acao.CIMA:
            pontos = [(x_centro, y_centro - offset), (x_centro - offset, y_centro + offset), (x_centro + offset, y_centro + offset)]
        elif acao_tomada == Acao.BAIXO:
            pontos = [(x_centro, y_centro + offset), (x_centro - offset, y_centro - offset), (x_centro + offset, y_centro - offset)]
        elif acao_tomada == Acao.ESQUERDA:
            pontos = [(x_centro - offset, y_centro), (x_centro + offset, y_centro - offset), (x_centro + offset, y_centro + offset)]
        elif acao_tomada == Acao.DIREITA:
            pontos = [(x_centro + offset, y_centro), (x_centro - offset, y_centro - offset), (x_centro - offset, y_centro + offset)]
            
        pygame.draw.polygon(self.tela, cor_seta, pontos)
        pygame.draw.polygon(self.tela, (0, 0, 0), pontos, 2)

    # renderiza o painel lateral escuro de telemetria e controle de interface
    def desenhar_painel(self, agente_nome, info, acao_tomada, indice_ativo):
        # desenha o retângulo de fundo do painel lateral alocado à direita da grade
        pygame.draw.rect(self.tela, (30, 30, 30), (self.x_painel, 0, 300, self.tela.get_height()))

        # converte a enumeração da ação em string legível, ou define "Nenhuma" se estiver nula
        texto_acao = acao_tomada.name if acao_tomada is not None else "Nenhuma"

        # agrupa as informações de telemetria e o cabeçalho dos botões em uma lista de textos
        textos = [
            f"AGENTE: {agente_nome}",
            f"PASSOS: {self.ambiente.passos_dados}/{self.ambiente.limite_passos}",
            f"TENTOU IR: {texto_acao}", 
            f"STATUS: {info.get('status', 'Navegando')}",
            "",
            "SELECIONE O AGENTE:"
        ]

        # renderiza e posiciona cada linha de texto informacional verticalmente no painel
        for i, texto in enumerate(textos):
            superficie = self.fonte.render(texto, True, COR_TEXTO)
            self.tela.blit(superficie, (self.x_painel + 20, 30 + (i * 30)))

        # desenha os botões interativos
        botoes = [
            (self.btn_heuristico, "A-Estrela", 0),
            (self.btn_qlearning, "Q-Learning", 1),
            (self.btn_genetico, "Algoritmo Genético", 2)
        ]

        for rect, texto, idx in botoes:
            cor_fundo = (50, 150, 255) if idx == indice_ativo else (70, 70, 70)
            pygame.draw.rect(self.tela, cor_fundo, rect, border_radius=5)
            pygame.draw.rect(self.tela, (200, 200, 200), rect, 2, border_radius=5) 
            
            # centraliza o texto no botão
            surf_texto = self.fonte.render(texto, True, COR_TEXTO)
            text_rect = surf_texto.get_rect(center=rect.center)
            self.tela.blit(surf_texto, text_rect)

    # atualiza e desenha todos os elementos visuais do simulador a cada frame da interface, chamando todas as funções auxiliares pré definidas
    def renderizar(self, agente_nome, info, acao_tomada, indice_ativo):
        self.tela.fill((0, 0, 0))
        self.desenhar_grade()
        self.desenhar_agente()
        self.desenhar_seta(acao_tomada) 
        self.desenhar_painel(agente_nome, info, acao_tomada, indice_ativo)
        pygame.display.flip()

    # método auxiliar para desenhar o modelo 2D estilizado de um veículo na grade
    def _desenhar_veiculo(self, linha, coluna, cor_carro):
        x = coluna * self.tamanho_tile
        y = linha * self.tamanho_tile
        
        largura_carro = self.tamanho_tile * 0.5
        altura_carro = self.tamanho_tile * 0.7
        offset_x = x + (self.tamanho_tile - largura_carro) // 2
        offset_y = y + (self.tamanho_tile - altura_carro) // 2
        
        rect_carro = pygame.Rect(offset_x, offset_y, largura_carro, altura_carro)
        pygame.draw.rect(self.tela, cor_carro, rect_carro, border_radius=5)
        
        vidro = pygame.Rect(offset_x + 4, offset_y + 10, largura_carro - 8, 12)
        pygame.draw.rect(self.tela, (150, 200, 255), vidro)
        
        t_larg, t_alt = 6, 12
        pygame.draw.rect(self.tela, (20, 20, 20), (offset_x - 4, offset_y + 5, t_larg, t_alt)) 
        pygame.draw.rect(self.tela, (20, 20, 20), (offset_x + largura_carro - 2, offset_y + 5, t_larg, t_alt)) 
        pygame.draw.rect(self.tela, (20, 20, 20), (offset_x - 4, offset_y + altura_carro - 15, t_larg, t_alt)) 
        pygame.draw.rect(self.tela, (20, 20, 20), (offset_x + largura_carro - 2, offset_y + altura_carro - 15, t_larg, t_alt))

    # método auxiliar para desenhar um ícone de pedestre estilizado (boneco de palito)
    def _desenhar_pedestre(self, linha, coluna):
        x = coluna * self.tamanho_tile
        y = linha * self.tamanho_tile
        cx = x + self.tamanho_tile // 2
        cy = y + self.tamanho_tile // 2
        
        cor = (255, 255, 255) 
        espessura = 3
        
        pygame.draw.circle(self.tela, cor, (cx, cy - 12), 5, espessura)
        pygame.draw.line(self.tela, cor, (cx, cy - 7), (cx, cy + 6), espessura)
        pygame.draw.line(self.tela, cor, (cx, cy - 4), (cx - 8, cy + 2), espessura)
        pygame.draw.line(self.tela, cor, (cx, cy - 4), (cx + 8, cy - 2), espessura)
        pygame.draw.line(self.tela, cor, (cx, cy + 6), (cx - 8, cy + 18), espessura)
        pygame.draw.line(self.tela, cor, (cx, cy + 6), (cx + 8, cy + 18), espessura)

def main():
    ambiente = Transito()
    
    agentes = [
        AgenteHeuristico(),
        AgenteQLearning(nome="Q-Learning"),
        AgenteGenetico(nome="Algoritmo Genético")
    ]
    
    # o Q-Learning precisa ser treinado antes de usar a interface
    print("Treinando Q-Learning nos bastidores (Aguarde)...")
    agentes[1].treinar(ambiente, episodios=5000)
    print("Treinamento concluído! Iniciando interface gráfica...")

    visualizador = Visualizador(ambiente) 
    estado = ambiente.reset()
    rodando = True
    
    indice_agente_ativo = 0
    info = {"status": "Navegando"}
    acao = None
    
    while rodando:
        # rastreio de eventos e cliques do mouse
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1: 
                    pos_mouse = pygame.mouse.get_pos()
                    
                    # verifica em qual botão o usuário clicou e reseta a simulação
                    if visualizador.btn_heuristico.collidepoint(pos_mouse):
                        indice_agente_ativo = 0
                        estado = ambiente.reset()
                        info = {"status": "Navegando"}
                        acao = None
                    elif visualizador.btn_qlearning.collidepoint(pos_mouse):
                        indice_agente_ativo = 1
                        estado = ambiente.reset()
                        info = {"status": "Navegando"}
                        acao = None
                    elif visualizador.btn_genetico.collidepoint(pos_mouse):
                        indice_agente_ativo = 2
                        estado = ambiente.reset()
                        info = {"status": "Navegando"}
                        acao = None

        agente = agentes[indice_agente_ativo]

        # executa a lógica apenas se o percurso não estiver finalizado
        if not ambiente.finalizado:
            acao = agente.escolher_acao(estado, ambiente)
            estado, recompensa, finalizado, info = ambiente.step(acao)
            
        # renderiza a tela enviando o índice do agente para pintar o botão correto
        visualizador.renderizar(agente.nome, info, acao_tomada=acao, indice_ativo=indice_agente_ativo)
        
        # se o carro bateu, não precisa de sleep longo, apenas escuta o mouse
        if not ambiente.finalizado:
            time.sleep(0.4) 
        else:
            time.sleep(0.05) 

    pygame.quit()

if __name__ == "__main__":
    main()
    