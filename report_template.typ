#import "cover.typ": cover
#import "template.typ": *

#show: project

// INFO CAPA

#cover(title: "Inteligência Artificial", authors: (
  (name: "Tiago Alves", number: "A106883"),
  (name: "Nuno Fernandes", number: "A107317"),
  (name: "Salomé Faria", number: "A108487"),
  (name: "Pedro Esteves", number: "A106839")),
  datetime.today().display("[month repr:long] [day], [year]"))

#pagebreak()

= Avaliação pelos Pares

Conforme exigido, apresenta-se a distribuição do esforço e contribuição de cada membro do grupo para a realização deste trabalho. A soma dos deltas é igual a 0.

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, center, center),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    
    [*Nome*], [*Número*], [*Delta*],
    [Tiago Alves], [A106883], [0],
    [Nuno Fernandes], [A107317], [0],
    [Salomé Faria], [A108487], [0],
    [Pedro Esteves], [A106839], [0],
  ),
  caption: [Distribuição de Deltas],
)

#pagebreak()

#set page(numbering: "i", number-align: center)
#counter(page).update(1)

#show outline: it => {
    show heading: set text(size: 18pt)
    it
}

// INDICE, FIGURAS, TABELAS

#{  show outline.entry.where(level: 1): it => {
    v(5pt)
    strong(it)
  }

  outline(
    title: [Índice]
  )
}

#v(-0.4em)
#outline(
  title: none,
  target: figure.where(kind: "attachment"),
  indent: n => 1em,
)

// #outline(
//   title: [Lista de Figuras],
//   target: figure.where(kind: image),
// )

// #outline(
//   title: [Lista de Tabelas],
//   target: figure.where(kind: table),
// )

// Make the page counter reset to 1
#set page(numbering: "1", number-align: center)
#counter(page).update(1)

#set enum(indent: 2em)
#set enum(numbering: "1.1.", full: true)
#set list(indent: 2em)
#set par(first-line-indent: 1em)

// BODY

= Introdução

Este relatório apresentará informações relativas do projeto da Unidade Curricular Inteligência Artificial, pertencente ao 3º Ano da Licenciatura em Engenharia Informática, realizada no ano letivo 2025/2026, na Universidade do Minho.

O objetivo foi desenvolver algoritmos de procura que permitam otimizar a gestão de uma frota de táxis heterogénea, composta por veículos a combustão e elétricos, garantindo a eficiência operacional, a redução de custos energéticos e o cumprimento de critérios ambientais.

Foram implementadas as funcionalidades: procuras, e algoritmos de atribuição avançados (Simulated Annealing).

== Objetivos
O objetivo principal é desenvolver e comparar algoritmos de procura e otimização para:
- Maximizar o lucro operacional (Receita - Custos).
- Minimizar o tempo de espera dos clientes.
- Garantir a sustentabilidade ambiental (redução de CO2).
- Gerir eficazmente as restrições de autonomia dos veículos elétricos (EVs).

= Descrição do Problema

A TaxiGreen é uma empresa moderna de transporte urbano que enfrenta um desafio complexo: gerir uma frota mista de veículos (elétricos e a combustão) numa cidade movimentada como Braga. O objetivo não é apenas levar passageiros do ponto A ao ponto B, mas fazê-lo da forma mais eficiente e sustentável possível.

Pedidos de transporte chegam a todo o momento, vindos de diferentes partes da cidade. Alguns clientes têm pressa, outros preferem uma viagem ecológica. A empresa tem à sua disposição carros elétricos (baratos de operar, mas com autonomia limitada e necessidade de recarga demorada) e carros a combustão (rápidos de abastecer, mas caros e poluentes).

O nosso trabalho é criar o "cérebro" desta operação. Um sistema inteligente que decide, em tempo real:
1.  Que veículo deve atender qual pedido?
2.  Qual o melhor caminho para lá chegar, fugindo ao trânsito?
3.  Quando é que um carro elétrico deve parar para carregar antes que fique sem bateria?

Para resolver isto, transformamos a cidade num **Grafo** (uma rede de nós e conexões) e utilizamos algoritmos de Inteligência Artificial para encontrar as melhores soluções de navegação e atribuição.

= Formulação do Problema

Para responder ao desafio de gestão de frota da TaxiGreen, o problema foi modelado como um problema de Otimização Combinatória Dinâmica, resolvido através de uma pesquisa local estocástica (Simulated Annealing).

Ao contrário de um problema de navegação simples (resolvido via A\*), o desafio aqui não é encontrar um caminho, mas sim encontrar a configuração de alocação ótima entre veículos e pedidos num determinado instante, considerando restrições de capacidade e autonomia.

== Definição do Estado (S)

Definimos o estado do sistema num instante $t$ como um tuplo $S_t = (A, B, V)$, onde:

- **A (Matriz de Atribuições)**: Um mapeamento $V -> R union {emptyset}$, onde $V$ é o conjunto de todos os veículos da frota e $R$ é o conjunto de pedidos ativos. Se $A[v] = r$, significa que o veículo $v$ está a servir o pedido $r$. Se $A[v] = emptyset$, o veículo está livre.
- **B (Backlog/Fila de Espera)**: O conjunto de pedidos pendentes $R_"pend"$ que foram recebidos mas ainda não foram atribuídos a nenhum veículo.
- **V (Estado Projetado da Frota)**: Um vetor contendo o estado futuro estimado de cada veículo $v in V$ após cumprir a atribuição atual. Para cada veículo, projeta-se:
  - $"Pos"_"final"$: Localização após a entrega.
  - $"Bat"_"final"$: Autonomia restante estimada após a entrega.
  - $"Tempo"_"livre"$: Instante de tempo simulado em que o veículo ficará novamente disponível.

#figure(
  rect(width: 80%, height: 100pt, fill: luma(240), stroke: 1pt + gray),
  caption: [Representação do Estado Projetado (Inserir Imagem Aqui)],
)

*Nota*: Esta representação permite ao algoritmo avaliar não apenas o custo imediato, mas também a viabilidade futura (ex: evitar atribuir um pedido a um veículo que ficaria com autonomia negativa).

== Operadores (Espaço de Ações)

Para navegar no espaço de estados e encontrar soluções melhores, definimos cinco operadores de transição que modificam o estado $S$ para gerar um estado vizinho $S'$:

1.  **Assign(v, r)**: Retira um pedido $r$ do Backlog ($B$) e atribui-o a um veículo livre $v$.
2.  **Unassign(v)**: Remove a atribuição atual de um veículo $v$, devolvendo o pedido ao Backlog ($B$). Útil para libertar veículos para pedidos mais prioritários que possam surgir.
3.  **Swap(v1, v2)**: Troca os pedidos atribuídos entre dois veículos $v_1$ e $v_2$. Este operador permite otimizar a frota trocando, por exemplo, um pedido de curta distância de um veículo a combustão para um elétrico, e vice-versa.
4.  **Move(v_src, v_dst)**: Move um pedido de um veículo ocupado para um livre.
5.  **Replace(v, r_new)**: Substitui o pedido atual de um veículo por um do backlog (útil se o novo for muito mais prioritário).

== Teste Objetivo e Função de Custo (E)

Sendo um problema de otimização, o "Teste Objetivo" não é binário (atingiu/não atingiu), mas sim a minimização de uma Função de Energia (Custo) Global $E(S)$. O algoritmo procura $S^*$ tal que $E(S^*) <= E(S), forall S$.

A função de avaliação multiobjetivo é definida como:
$ E(S) = sum_(v in "Frota") C_"op"(v) + sum_(r in "Backlog") C_"espera"(r) + P_"viabilidade" $

#figure(
  table(
    columns: (auto, auto, 1.8fr, 2.5fr),
    align: (center, center, left, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if calc.odd(row) { luma(250) } else { white },
    
    [*Peso*],       [*Constante no código*], [*Valor*],      [*Significado / Objetivo*],
    [w₁],           [`WEIGHT_AGE`],             [4.0],         [Penaliza tempo de espera dos pedidos (4× mais importante que km vazio)],
    [w₂],           [`WEIGHT_ISOLATION`],       [1.0],         [Penaliza km percorridos “vazios” ou longe de hotspots],
    [w₃],           [`WEIGHT_PROFIT`],          [10.0],        [Importância do lucro / custo operacional],
    [w₄],           [`BACKLOG_BASE_PENALTY`],   [160.0],       [Penalização severa por deixar pedidos na fila (backlog)],
    [*Outras*], [], [], [],
    [Eco],          [—],                        [15.0 / km],   [Uso de veículo a combustão em pedido “Eco”],
    [Bateria],      [—],                        [20.0],        [Fator de risco por bateria fraca],
  ),
  caption: [Pesos e Penalizações da Função de Custo],
)

Onde:

- $C_"op"(v)$ (**Custo Operacional**): Inclui o tempo de viagem (calculado via A\*), distância percorrida e o custo monetário da energia (mais baixo para EVs, mais alto para combustão).
- $C_"espera"(r)$ (**Penalização de Backlog**): Custo elevado para pedidos que ficam na fila, ponderado pela sua prioridade ($"Prio"$) e tempo de espera acumulado ($"Age"$).
  - Fórmula: $K_"base" times "Prio" times (1 + "Age")$.
  #figure(
    rect(width: 50%, height: 50pt, fill: luma(240), stroke: 1pt + gray),
    caption: [Fórmula de Penalização de Backlog (Inserir Imagem Aqui)],
  )
- $P_"viabilidade"$ (**Penalizações**): Um valor proibitivo ($infinity$) aplicado se o estado projetado $V$ violar restrições "duras" (ex: autonomia final < 0 ou capacidade de passageiros insuficiente).

== Dinâmica de Execução

O algoritmo de procura não é executado apenas uma vez. O sistema opera em regime de **Planeamento Contínuo (Replanning)**. O processo de procura é reiniciado sempre que ocorre um evento significativo no ambiente:
- Chegada de um novo pedido de cliente.
- Um veículo torna-se disponível (termina viagem ou recarga).
- Falha de uma infraestrutura (ex: estação de recarga avariada).
- **Timeouts Escalonados**: O tempo máximo de espera depende da prioridade do cliente.
  - Clientes normais (Prio 1) esperam até **30 minutos**.
  - Clientes VIP (Prio 5) cancelam o pedido após apenas **10 minutos**.
  - Fórmula: $"Timeout" = 30 - (("Prio" - 1) times 5)$.
  - O cancelamento gera uma penalização financeira e conta como "Pedido Falhado".

Desta forma, o sistema adapta-se dinamicamente, reavaliando decisões anteriores se uma nova configuração apresentar menor custo global.

== Determinismo Estocástico (Criação de Pedidos)

A geração de pedidos segue um **Processo de Poisson Não-Homogéneo**, onde a taxa de chegada $lambda(t)$ varia ao longo do dia para simular picos de procura (manhã, almoço, fim de tarde).

- **Distribuição Exponencial**: O intervalo de tempo até ao próximo pedido é dado por $Delta t = -ln(U) / lambda(t)$, onde $U tilde U(0,1)$ e $lambda(t)$ é a taxa de procura no instante $t$. Isto cria intervalos menores (mais pedidos) quando $lambda(t)$ é alto (horas de ponta).
- **Hotspots**: A origem e destino dos pedidos não são puramente aleatórios. O sistema utiliza "Hotspots" (zonas de alta densidade como Estações e Universidades). A geração de pedidos é enviesada espacialmente: as coordenadas de origem e destino tendem a concentrar-se nas imediações destes pontos.
- **Trânsito e Meteorologia**: O ambiente não é estático.
  - *Trânsito*: Simulado com **Ruído de Perlin 3D** e curvas Gaussianas para horas de ponta (08:30, 18:00), afetando a velocidade nas arestas.
  - *Meteorologia*: Um sistema probabilístico altera o estado entre Sol, Chuva e Tempestade, aplicando penalizações de velocidade (até -60%) e aumentando o risco de atrasos.
  - *Falhas de Infraestrutura*: As estações de carregamento têm uma probabilidade de falha aleatória (`0.01%` por tick), ficando inoperacionais por 2 horas simuladas, forçando a frota a readaptar-se.
- **Reprodutibilidade**: Para garantir que os benchmarks são justos e comparáveis, utilizamos uma *seed* fixa (`seed=42`) no gerador de números pseudo-aleatórios. Isto garante que, embora a procura seja estocástica e variada, é exatamente a mesma para todos os algoritmos testados.

== Agentes (Pedidos)
Os pedidos não são homogéneos; cada cliente tem características que afetam o lucro e a urgência:
- **Prioridade (1-5)**: Define a urgência do cliente. Pedidos VIP (Prioridade 5) são mais frequentes nas horas de ponta (08:00-09:30, 17:30-19:30).
- **Preço Dinâmico**: O valor da viagem segue um modelo semelhante à Uber:
  - $P = ("Base" + "Dist" times "PreçoKm") times "Mult"$.
  - Onde $"Mult"$ é $1.3$ se o pedido for para mais de 4 passageiros (UberXL), recompensando o uso de veículos de maior capacidade.
- **Preferência Eco**: 30% dos clientes preferem veículos elétricos. Atribuir um veículo a combustão a estes clientes gera uma penalização na função de custo.

= Modelação e Implementação

== Ambiente de Simulação
Utilizamos um mapa real da cidade de Braga obtido via `OSMnx`.
- **Grafo de Navegação**: Os nós representam intersecções e as arestas segmentos de estrada. As distâncias são calculadas via fórmula de Haversine (distância na esfera).
- **Trânsito Dinâmico e Meteorologia**: O `TrafficManager` simula o fluxo de tráfego utilizando uma combinação de:
  - **Curvas Gaussianas**: Para modelar os picos de hora de ponta (08:30, 13:00, 18:00, 21:00).
  - **Ruído de Perlin (3D)**: Para introduzir variabilidade espacial e temporal orgânica, evitando padrões repetitivos.
  - **Meteorologia**: Um sistema de clima dinâmico (Sol, Chuva, Tempestade) que agrava os fatores de atraso em até 60%.

== Agentes (Veículos)
A frota é heterogénea, composta por veículos com atributos distintos que influenciam a decisão do algoritmo:

- **Atributos Comuns**:
  - `id`: Identificador único.
  - `capacity`: Capacidade de passageiros (1 a 7 lugares).
  - `condition`: Estado atual (Disponível, Em Viagem, A Carregar, etc.).
- **Veículos a Combustão**:
  - Alta autonomia (600 - 900 km) e reabastecimento rápido (5 min).
  - Custo operacional elevado (combustível + manutenção).
  - Emitem CO2 (aprox. 120g/km).
- **Veículos Elétricos (EV)**:
  - Autonomia limitada (200 - 420 km) e tempos de recarga variáveis.
  - Custo por km muito reduzido (eletricidade).
  - Zero emissões locais, mas requerem gestão cuidadosa de bateria (são penalizados se a carga baixar de 20%).
  - **Falha Crítica**: Se um veículo ficar sem autonomia (`remaining_km <= 0`) durante uma viagem, entra em estado `UNAVAILABLE`, o pedido atual é cancelado (com penalização financeira) e o veículo fica inoperacional até ser "rebocado" (reset manual ou fim da simulação).

= Algoritmos Desenvolvidos

== Algoritmos de Navegação (Pathfinding)
Para mover os veículos no mapa, implementamos três estratégias:

1.  **Breadth-First Search (BFS)**:
    - *Como funciona?*: Imagina uma onda que se espalha em todas as direções a partir do ponto de partida. O BFS explora todos os cruzamentos vizinhos, depois os vizinhos desses vizinhos, e assim por diante, camada por camada.
    - *Análise*: Garante o caminho com menos "saltos" (intersecções), mas ignora a distância real. Num mapa onde uma estrada pode ter 100m e outra 1km, o BFS pode escolher a de 1km só porque é um único "salto", tornando-o ineficiente para navegação rodoviária.

2.  **Greedy Best-First Search**:
    - *Como funciona?*: É o algoritmo "guloso" e otimista. Em cada cruzamento, escolhe sempre a estrada que parece ir mais diretamente para o destino (em linha reta), sem querer saber o que vem depois.
    - *Análise*: É muito rápido, mas pode ser enganado. Pode entrar numa rua sem saída ou num caminho longo só porque inicialmente parecia apontar para o lado certo. Não garante o melhor caminho.

3.  **A\* (A-Star)**:
    - *Como funciona?*: É o "melhor dos dois mundos". Combina o custo real já percorrido (como o BFS/Dijkstra) com uma estimativa inteligente da distância que falta (como o Greedy). Ele planeia o caminho minimizando a soma $f(n) = g(n) + h(n)$.
    - *Heurística*: Usamos o tempo de viagem em linha reta à velocidade máxima como estimativa ($h(n)$).
    - *Por que é o melhor?*: Como a nossa estimativa nunca exagera o tempo real (é "admissível"), o A\* garante matematicamente que encontra o caminho mais rápido possível, sendo muito mais eficiente que o BFS pois não explora direções erradas.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: center,
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Algoritmo*], [*Complexidade Temporal*], [*Complexidade Espacial*], [*Ótimo?*],
    [BFS], [$O(b^d)$], [$O(b^d)$], [Não (em grafos ponderados)],
    [Greedy], [$O(b^m)$], [$O(b^m)$], [Não],
    [A\*], [$O(b^d)$], [$O(b^d)$], [Sim (com heurística admissível)],
  ),
  caption: [Comparação Teórica dos Algoritmos de Procura],
)

== Algoritmos de Atribuição (Assignment)
O problema de atribuir $N$ veículos a $M$ pedidos é combinatório.

1.  **Greedy Assignment**:
    - *Como funciona?*: Olha para todos os pedidos e veículos disponíveis e faz a combinação mais barata imediata. Repete até não haver mais pares.
    - *Problema*: É "míope". Pode atribuir o único carro elétrico disponível a uma viagem curta agora, impedindo-o de fazer uma viagem longa e lucrativa daqui a 5 minutos.

2.  **Hill Climbing**:
    - *Como funciona?*: Começa com uma solução aleatória e tenta fazer pequenas trocas (ex: trocar o pedido do carro A com o do carro B). Se a troca melhorar o custo, aceita. Se não, rejeita. Sobe a "colina" da eficiência até não conseguir subir mais.
    - *Implementação*: Utilizamos uma variante estocástica que gera vizinhos através de operadores de *Swap*, *Move* e *Replace*, aceitando apenas melhorias estritas na função de energia.
    - *Problema*: Fica preso em "mínimos locais". Pode achar uma solução razoável e parar lá, sem ver que uma solução muito melhor existia se tivesse aceitado piorar um pouco temporariamente.

3.  **Simulated Annealing**:
    - *Como funciona?*: Inspirado no arrefecimento de metais. No início (alta temperatura), o algoritmo é "louco" e aceita soluções piores para explorar o espaço e não ficar preso. À medida que "arrefece", torna-se mais exigente e foca-se em refinar a melhor solução encontrada.
    - *Vantagem*: Consegue escapar aos mínimos locais onde o Hill Climbing fica preso, encontrando soluções globais muito melhores para a gestão da frota a longo prazo.

== Otimização da Atribuição de Pedidos (Lógica de Despacho)

A função `assign_pending_requests` é o componente central da lógica de despacho da simulação. Em vez de uma abordagem simples (como "o veículo mais próximo aceita o pedido"), esta função implementa uma solução otimizada que modela o cenário como um Problema de Atribuição.

O processo é executado nos seguintes passos:

1. **Construção da Matriz de Custos**: É gerada uma matriz de custos bidimensional onde as linhas representam cada veículo disponível e as colunas representam cada pedido pendente. O valor em cada célula $(i,j)$ corresponde ao custo detalhado (tempo + penalizações) para o veículo $i$ atender o pedido $j$.

2. **Aplicação de Restrições (Pruning)**: Durante a construção da matriz, são aplicadas restrições. Se um veículo não tiver capacidade suficiente para um pedido, o custo é definido como infinito ($infinity$).

3. **Resolução do Problema de Atribuição**: Para encontrar a combinação ótima, a função utiliza o algoritmo selecionado (por defeito, **Simulated Annealing**). Este algoritmo explora o espaço de soluções para minimizar a energia total do sistema, equilibrando custos operacionais e penalizações de espera.

4. **Execução das Atribuições**: O algoritmo retorna o vetor de atribuições ótimas. O código itera sobre esta solução e, para cada atribuição válida, atualiza o estado do veículo para `ON_WAY_TO_CLIENT`, define a sua rota e move o pedido da lista de pendentes para a lista de recolha.

Ao utilizar esta abordagem, o simulador garante que, em cada passo, a frota opera com a máxima eficiência global, minimizando o tempo e a distância desperdiçados, em vez de tomar decisões "gulosas" que poderiam ser sub-ótimas a longo prazo.

= Metodologia de Testes e Resultados

Utilizámos um sistema de *benchmark* automatizado para testar 9 combinações de algoritmos (3 Rotas \* 3 Atribuições) durante 14 dias simulados.

== Métricas de Avaliação
- **Financeiras**: Lucro Líquido, Receita Total.
- **Operacionais**: Taxa de Ocupação (% km com passageiro), Tempo Médio de Espera, Km Vazios (Deadheading), Pedidos Rejeitados/Não Atendidos.
- **Ambientais**: Emissões Totais de CO2.

== Análise dos Resultados

Comparando os resultados obtidos nas simulações de 336 horas (2 semanas simuladas), observamos diferenças claras entre as abordagens:

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: center,
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Configuração*], [*Lucro (€)*], [*Tempo Médio Espera (min)*], [*Pedidos Completos*],
    [A\* + Sim. Annealing], [36.319,77], [12,73], [5928],
    [BFS + Greedy], [33.524,26], [16,32], [5556],
  ),
  caption: [Comparação de Performance (Dados Reais do Benchmark)],
)

1.  **Eficiência do A\***: A combinação utilizando A\* obteve um lucro cerca de **8% superior** (€36k vs €33k) e completou mais **372 pedidos** que a abordagem BFS. Isto deve-se ao facto do A\* encontrar rotas mais rápidas, permitindo aos veículos ficarem livres mais cedo para aceitar novos serviços.
2.  **Qualidade de Serviço**: O tempo médio de espera baixou de 16,3 min (BFS) para **12,7 min (A\*)**. O uso de uma heurística de tempo real e de um algoritmo de atribuição mais inteligente (Simulated Annealing) permitiu gerir melhor os picos de procura.
3.  **Sustentabilidade**: Apesar de ambos percorrerem distâncias semelhantes (~68.000 km), a eficiência do A\* permitiu uma taxa de ocupação ligeiramente superior (53% vs 50%), o que significa menos km percorridos "vazios" e um uso mais racional da energia.

= Conclusão e Reflexão

O sistema desenvolvido gere com sucesso uma frota mista em Braga. A combinação de **A\*** para navegação e **Simulated Annealing** para atribuição revelou-se a mais robusta, equilibrando lucro, satisfação do cliente e eficiência energética.

== Reflexão e Dificuldades
Durante o desenvolvimento, a maior dificuldade foi equilibrar as restrições dos Veículos Elétricos. Inicialmente, os EVs ficavam muitas vezes "presos" sem carga longe das estações. A implementação de uma lógica de "reserva de bateria" e a penalização na função de custo para estados de bateria fraca foram cruciais para resolver isto.
Além disso, a afinação dos parâmetros do Simulated Annealing (temperatura e arrefecimento) exigiu vários testes para evitar que o algoritmo demorasse demasiado tempo a decidir em situações de alta carga.
Aprendemos que num problema dinâmico e real, a solução "ótima" matemática nem sempre é a melhor solução prática se demorar muito a calcular; o equilíbrio entre rapidez de decisão e qualidade da decisão é fundamental.

= Referências
- Russell, S., & Norvig, P. "Artificial Intelligence: A Modern Approach".
- Documentação OSMnx e NetworkX.
