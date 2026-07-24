from abc import ABC, abstractmethod
from src.veiculo_ai.ambiente.transito import Acao

class AgenteBase(ABC):
    """
    Contrato base para todos os agentes.
    Garante que todos possam ser executados pelo mesmo script de avaliação.
    """
    def __init__(self, nome: str):
        self.nome = nome

    @abstractmethod
    def escolher_acao(self, estado, ambiente) -> Acao:
        """
        Analisa o estado atual e retorna a ação decidida pelo agente.
        """
        pass

    def treinar(self, ambiente, episodios: int):
        """
        Método de treinamento prévio. 
        Implementado apenas por agentes que aprendem (Q-Learning e Genético).
        """
        pass
    