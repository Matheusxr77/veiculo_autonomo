# Veículo Autônomo

Simulador 2D em grade para comparar estratégias de controle de um veículo autônomo em um cenário urbano simplificado. O projeto modela ruas, prédios, carros dinâmicos e pedestres, e permite observar como diferentes agentes se comportam diante de obstáculos estáticos e eventos aleatórios durante a navegação até um destino fixo.

## O que o projeto faz

O sistema executa uma simulação em um mapa 10x10, com o veículo partindo da posição inicial `(0, 0)` e tentando chegar ao destino `(9, 9)`. A cada passo, o ambiente pode gerar carros e pedestres dinamicamente, o que força os agentes a adaptar a rota ou parar para evitar colisões.

O projeto oferece três estratégias de decisão:

- `A-Estrela / heurístico`: planeja rotas usando busca informada com heurística.
- `Q-Learning`: aprende uma política por tentativa e erro com tabela-Q e penalidades/recompensas do ambiente.
- `Algoritmo Genético`: evolui sequências de ações e combina busca em largura com mutação, crossover e elitismo.

Além da simulação visual, o projeto também gera uma comparação quantitativa entre os agentes, registrando métricas como taxa de sucesso, colisões, atropelamentos, timeout, média de passos e recompensa média.

## Estrutura do projeto

- `src/veiculo_ai/ambiente/transito.py`: define o ambiente, a grade, os obstáculos, as recompensas e a lógica de avanço da simulação.
- `src/veiculo_ai/agentes/base.py`: contrato base compartilhado pelos agentes.
- `src/veiculo_ai/agentes/heuristico.py`: implementa o agente heurístico com planejamento de caminho.
- `src/veiculo_ai/agentes/qlearning.py`: implementa o agente de aprendizado por reforço.
- `src/veiculo_ai/agentes/genetico.py`: implementa o agente baseado em algoritmo genético.
- `src/veiculo_ai/cli/assistir.py`: abre a interface gráfica para observar a simulação e alternar entre os agentes.
- `src/veiculo_ai/cli/avaliar.py`: executa avaliações em lote e salva o relatório em `results/comparacao_agentes.txt`.

## Requisitos

- Python 3.10 ou superior.
- `pygame`.

## Instalação

Crie e ative um ambiente virtual, se desejar, e instale as dependências:

```bash
pip install -r requirements.txt
```

## Como executar

### Interface gráfica

Para abrir a visualização interativa e observar o veículo em tempo real:

```bash
python -m src.veiculo_ai.cli.assistir
```

Na interface, os botões laterais permitem alternar entre os três agentes. O painel também exibe o estado atual da simulação, o número de passos e o status do episódio.

### Avaliação comparativa

Para treinar os agentes que precisam de aprendizado e executar a comparação entre eles:

```bash
python -m src.veiculo_ai.cli.avaliar
```

Uma observação sobre esse comando é que o número definido de testes foi 5000, dependendo da máquina o processo pode ficar lento, como alternativa, recomenda-se instalar o [Pypy](https://pypy.org/download.html) e executar com o seguinte comando:

```bash
pypy -m src.veiculo_ai.cli.avaliar
```

Esse comando executa vários episódios por agente, exibe o progresso no terminal e grava um resumo final em:

```text
results/comparacao_agentes.txt
```

## Métricas geradas

O relatório de avaliação inclui:

- Taxa de sucesso.
- Taxa de atropelamento.
- Taxa de colisão.
- Taxa de esgotamento.
- Passos médios quando há sucesso.
- Recompensa média.
- Tempo total de execução.

## Como o ambiente funciona

O ambiente usa uma grade com ruas e áreas ocupadas por prédios. O veículo só pode se mover em quatro direções e recebe penalizações por andar, regressar, colidir ou ficar parado por muito tempo. O episódio termina quando o veículo chega ao destino, sofre uma colisão ou esgota o limite de passos.

Eventos dinâmicos tornam o cenário mais desafiador:

- Carros aparecem e desaparecem ao longo da simulação.
- Pedestres podem surgir em posições aleatórias válidas.
- O agente precisa evitar travessias ocupadas e rotas bloqueadas.

## Estratégias implementadas

### Agente heurístico

Usa planejamento do tipo A* com distância para calcular um caminho até o destino. Se um carro ou pedestre bloqueia a próxima jogada, o agente tenta recalcular a rota ou aguarda para evitar colisão.

### Agente Q-Learning

Mantém uma tabela-Q por estado e aprende com exploração inicial alta, que vai decaindo ao longo dos episódios. A política final prioriza movimentos seguros, evita ciclos curtos e desvia de obstáculos dinâmicos quando possível.

### Algoritmo genético

Gera populações de sequências de ações, avalia cada indivíduo no ambiente e evolui as melhores soluções com elitismo, torneio, crossover e mutação. O agente também usa BFS para apoiar a geração inicial e desvios durante a execução.

## Saída gerada

Ao final da avaliação, o projeto cria o arquivo `results/comparacao_agentes.txt` com um resumo textual das métricas obtidas por cada estratégia. O diretório `results/` já existe no projeto e pode ser reaproveitado para novas execuções.

## Observações

- O projeto foi pensado para rodar localmente com interface gráfica via `pygame`.
- O treinamento do `Q-Learning` e a evolução do algoritmo genético podem levar alguns minutos, dependendo da máquina.
- Se a interface não abrir corretamente, verifique se o ambiente virtual está ativo e se o `pygame` foi instalado com sucesso.