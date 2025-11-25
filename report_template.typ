#import "cover.typ": cover
#import "template.typ": *

#show: project

// ----------------------------------------------------------------------
// CAPA
// ----------------------------------------------------------------------

#cover(title: "Inteligência Artificial", authors: (
  (name: "Tiago Alves", number: "A106883"),
  (name: "Nuno Fernandes", number: "A107317"),
  (name: "Salomé Faria", number: "A108487"),
  (name: "Pedro Esteves", number: "A106839")),
  datetime.today().display("[month repr:long] [day], [year]"))

#pagebreak()

// ----------------------------------------------------------------------
// AVALIAÇÃO PELOS PARES
// ----------------------------------------------------------------------

= Avaliação pelos Pares

Distribuição do esforço e contribuição de cada membro do grupo para a realização deste trabalho.

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

// ----------------------------------------------------------------------
// ÍNDICES
// ----------------------------------------------------------------------

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

#outline(
  title: [Lista de Figuras],
  target: figure.where(kind: image),
)

#outline(
  title: [Lista de Tabelas],
  target: figure.where(kind: table),
)

// Reiniciar numeração para o conteúdo
#set page(numbering: "1", number-align: center)
#counter(page).update(1)

#set enum(indent: 2em)
#set enum(numbering: "1.1.", full: true)
#set list(indent: 2em)
#set par(first-line-indent: 1em, justify: true)

// ----------------------------------------------------------------------
// CONTEÚDO DO RELATÓRIO
// ----------------------------------------------------------------------

= Introdução

Este relatório apresenta as informações relativas ao projeto da Unidade Curricular de Inteligência Artificial, pertencente ao 3º Ano da Licenciatura em Engenharia Informática, realizada no ano letivo 2025/2026, na Universidade do Minho.

O objetivo foi desenvolver algoritmos de procura que permitam otimizar a gestão de uma frota de táxis heterogénea, composta por veículos a combustão e elétricos, garantindo a eficiência operacional, a redução de custos energéticos e o cumprimento de critérios ambientais. 

A solução implementada utiliza técnicas avançadas de Inteligência Artificial, nomeadamente algoritmos de procura informada (A\*) e algoritmos de otimização local estocástica (Simulated Annealing) para resolver o problema de despacho de veículos em tempo real.

== Objetivos
O objetivo principal é desenvolver e comparar algoritmos de procura e otimização para:
- Maximizar o lucro operacional (Receita - Custos).
- Minimizar o tempo de espera dos clientes.
- Garantir a sustentabilidade ambiental (redução de CO2).
- Gerir eficazmente as restrições de autonomia dos veículos elétricos (EVs).

= Descrição do Problema

A *TaxiGreen* é uma empresa moderna de transporte urbano que enfrenta um desafio complexo: gerir uma frota mista de veículos (elétricos e a combustão) numa cidade movimentada como Braga. O objetivo não é apenas levar passageiros do ponto A ao ponto B, mas fazê-lo da forma mais eficiente e sustentável possível.

Pedidos de transporte são requisitados todo o dia, com origem em diferentes partes da cidade.  Podem requisitar ser atendidos rapidamente, como optar por uma viagem ecológica. A empresa tem à sua disposição carros elétricos (baratos de operar, mas com autonomia limitada e necessidade de recarga demorada) e carros a combustão (rápidos de abastecer, mas caros e poluentes).

O nosso trabalho é criar o "cérebro" desta operação. Um sistema inteligente que decide, em tempo real:
1.  Que veículo deve atender qual pedido?
2.  Qual o melhor caminho para lá chegar, fugindo ao trânsito?
3.  Quando é que um carro elétrico deve parar para carregar antes que fique sem bateria?

Para resolver isto, transformamos a cidade num **Grafo** (uma rede de nós e conexões) obtido através do _OSMnx_ e utilizamos algoritmos de Inteligência Artificial para encontrar as melhores soluções de navegação e atribuição.

= Formulação do Problema

Para responder ao desafio de gestão de frota da TaxiGreen, o problema foi modelado como um problema de Otimização Combinatória Dinâmica, resolvido através de uma pesquisa local estocástica (Simulated Annealing).

Ao contrário de um problema de navegação simples (resolvido via A\*), o desafio aqui não é encontrar apenas um caminho, mas sim encontrar a configuração de alocação ótima entre veículos e pedidos num determinado instante, considerando restrições de capacidade e autonomia.

== Definição do Estado (S)

Definimos o estado do sistema num instante $t$ como um tuplo $S_t = (A, B, V)$, onde:

- **A (Atribuições)**: Um mapeamento $V -> R union {emptyset}$, onde $V$ é o conjunto de todos os veículos da frota e $R$ é o conjunto de pedidos ativos. Se $A[v] = r$, significa que o veículo $v$ está a servir o pedido $r$. Se $A[v] = emptyset$, o veículo está livre.
- **B (Backlog/Fila de Espera)**: O conjunto de pedidos pendentes $R_"pendentes"$ que foram recebidos mas ainda não foram atribuídos a nenhum veículo.
- **V (Estado Projetado da Frota)**: Um vetor contendo o estado futuro estimado de cada veículo $v in V$ após cumprir a atribuição atual. Para cada veículo, projeta-se:
  - $"Posição"_"final"$: Localização após a entrega.
  - $"Autonomia"_"final"$: Autonomia restante estimada após a entrega.
  - $"Tempo"_"livre"$: Instante de tempo simulado em que o veículo ficará novamente disponível.

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
    
    [*Peso*],       [*Constante Código*], [*Valor*],      [*Significado / Objetivo*],
    [w₁],           [`WEIGHT_AGE`],             [4.0],         [Penaliza tempo de espera dos pedidos],
    [w₂],           [`WEIGHT_ISOLATION`],       [1.0],         [Penaliza km percorridos longe de hotspots],
    [w₃],           [`WEIGHT_PROFIT`],          [10.0],        [Importância do lucro],
    [w₄],           [`BACKLOG_BASE_PENALTY`],   [160.0],       [Penalização severa por deixar pedidos na fila],
    [*Outras*], [], [], [],
    [Eco],          [`ENV_MISMATCH`],           [15.0 / km],   [Uso de veículo a combustão em pedido “Eco”],
    [Bateria],      [`WEIGHT_BATTERY`],         [20.0],        [Fator de risco por bateria fraca (\<30km)],
  ),
  caption: [Pesos e Penalizações da Função de Custo],
)

Onde:

- $C_"op"(v)$ (**Custo Operacional**): Inclui o tempo de viagem (calculado via A\*), distância percorrida e o custo monetário da energia (mais baixo para EVs, mais alto para combustão).
- $C_"espera"(r)$ (**Penalização de Backlog**): Custo elevado para pedidos que ficam na fila, ponderado pela sua prioridade ($"Prio"$) e tempo de espera acumulado ($"Age"$).
  - Fórmula: $K_"base" times "Prio" times (1 + "Age")$.
- $P_"viabilidade"$ (**Penalizações**): Um valor proibitivo ($infinity$) aplicado se o estado projetado $V$ violar restrições "duras" (ex: autonomia final < 0 ou capacidade de passageiros insuficiente).

== Dinâmica de Execução

O algoritmo de procura não é executado apenas uma vez. O sistema opera em regime de **Planeamento Contínuo (Replanning)**. O processo de procura é reiniciado sempre que ocorre um evento significativo no ambiente:
- Chegada de um novo pedido de cliente.
- Um veículo torna-se disponível (termina viagem ou recarga).
- Falha de uma infraestrutura (ex: estação de recarga avariada).
- **Timeouts Escalonados**: O tempo máximo de espera depende da prioridade do cliente.
  - Clientes normais (Prioridade 1) esperam até **30 minutos**.
  - Clientes VIP (Prioridade 5) cancelam o pedido após apenas **10 minutos**.
  - Fórmula: $"Timeout" = 30 - (("Prio" - 1) times 5)$.

Desta forma, o sistema adapta-se dinamicamente, reavaliando decisões anteriores se uma nova configuração apresentar menor custo global.

== Determinismo Estocástico (Criação de Pedidos)

A geração de pedidos segue um **Processo de Poisson Não-Homogéneo**, onde a taxa de chegada $lambda(t)$ varia ao longo do dia para simular picos de procura (manhã, almoço, fim de tarde).

- **Distribuição Exponencial**: O intervalo de tempo até ao próximo pedido é dado por $Delta t = -ln(U) / lambda(t)$, onde $U tilde U(0,1)$ e $lambda(t)$ é a taxa de procura no instante $t$. Isto cria intervalos menores (mais pedidos) quando $lambda(t)$ é alto (horas de ponta).
- **Hotspots**: A origem e destino dos pedidos não são puramente aleatórios. O sistema utiliza "Hotspots" (zonas de alta densidade como Estações e Universidades, ex: *Universidade do Minho*, *Braga Parque*). A geração de pedidos é enviesada espacialmente.
- **Trânsito e Meteorologia**: O ambiente não é estático.
  - *Trânsito*: Simulado com **Ruído de Perlin 3D** e curvas Gaussianas para horas de ponta (08:30, 18:00), afetando a velocidade nas arestas.
  - *Meteorologia*: Um sistema probabilístico altera o estado entre Sol, Chuva e Tempestade, aplicando penalizações de velocidade.
  - *Falhas de Infraestrutura*: As estações de carregamento têm uma probabilidade de falha (`0.01%` por tick).
- **Reprodutibilidade**: Utilizamos uma *seed* fixa (`seed=42`) no gerador de números pseudo-aleatórios para garantir benchmarks justos.

== Agentes (Pedidos)
Os pedidos não são homogéneos; cada cliente tem características que afetam o lucro e a urgência:
- **Prioridade (1-5)**: Define a urgência do cliente.
- **Preço Dinâmico**: O valor da viagem segue um modelo semelhante à Uber ($"Base" + "Dist" times "PreçoKm"$).
- **Preferência Eco**: 30% dos clientes preferem veículos elétricos.

= Modelação e Implementação

== Ambiente de Simulação
Utilizamos um mapa real da cidade de Braga obtido via `OSMnx` e serializado em `braga_map_cache.pkl`.
- **Grafo de Navegação**: Os nós representam intersecções e as arestas segmentos de estrada. As distâncias são calculadas via fórmula de Haversine (distância na esfera).
- **Trânsito Dinâmico e Meteorologia**: O `TrafficManager` simula o fluxo de tráfego utilizando Ruído de Perlin.
  - **Curvas Gaussianas**: Para modelar os picos de hora de ponta (08:30, 13:00, 18:00, 21:00).
  - **Ruído de Perlin (3D)**: Para introduzir variabilidade espacial e temporal orgânica, evitando padrões repetitivos.
  - **Meteorologia**: Um sistema de clima dinâmico (Sol, Chuva, Tempestade) que agrava os fatores de atraso em até 60%.

== Agentes (Veículos)
A frota é heterogénea (10 veículos), composta por veículos com atributos distintos:

- **Veículos a Combustão (5 Unidades)**:
  - Alta autonomia (600 - 900 km) e reabastecimento rápido (5 min).
  - Custo operacional elevado (combustível + manutenção).
  - Emitem CO2 (aprox. 120g/km).
- **Veículos Elétricos (5 Unidades)**:
  - Autonomia limitada (200 - 420 km) e tempos de recarga variáveis.
  - Custo por km muito reduzido (eletricidade).
  - Zero emissões locais, mas requerem gestão cuidadosa de bateria (são penalizados se a carga baixar de 30%).

= Algoritmos Desenvolvidos

== Algoritmos de Navegação (Pathfinding)
Para mover os veículos no mapa, implementamos três estratégias:

1.  **Breadth-First Search (BFS)**:
    - *Como funciona?*: Explora camada por camada.
    - *Análise*: Garante o caminho com menos "saltos", mas ignora a distância real. Ineficiente para navegação rodoviária.

2.  **Greedy Best-First Search**:
    - *Como funciona?*: Escolhe sempre a estrada que parece ir mais diretamente para o destino (menor heurística $h(n)$).
    - *Análise*: Rápido, mas não garante o caminho ótimo.

3.  **A\* (A-Star)**:
    - *Como funciona?*: Combina o custo real já percorrido ($g(n)$) com uma estimativa da distância que falta ($h(n)$).
    - *Heurística*: Usamos o tempo de viagem em linha reta à velocidade máxima (120km/h) como estimativa.
    - *Por que é o melhor?*: Como a estimativa é admissível, o A\* garante matematicamente que encontra o caminho mais rápido possível.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: center,
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Algoritmo*], [*Complexidade Temporal*], [*Complexidade Espacial*], [*Ótimo?*],
    [BFS], [$O(b^d)$], [$O(b^d)$], [Não (em distância)],
    [Greedy], [$O(b^m)$], [$O(b^m)$], [Não],
    [A\*], [$O(b^d)$], [$O(b^d)$], [Sim],
  ),
  caption: [Comparação Teórica dos Algoritmos de Procura],
)

== Algoritmos de Atribuição (Assignment)
O problema de atribuir $N$ veículos a $M$ pedidos é combinatório.

1.  **Greedy Assignment**:
    - *Como funciona?*: Faz a combinação mais barata imediata.
    - *Problema*: É "míope".

2.  **Hill Climbing**:
    - *Como funciona?*: Tenta fazer pequenas trocas (*Swap*, *Move*, ...) numa solução inicial. Se melhorar, aceita.
    - *Problema*: Fica preso em "mínimos locais".

3.  **Simulated Annealing**:
    - *Como funciona?*: No início (alta temperatura, $T=450$) aceita soluções piores para explorar o espaço. À medida que "arrefece" (fator $0.96$) foca-se em melhorar a solução.
    - *Vantagem*: Escapa aos mínimos locais, encontrando soluções globais melhores para a gestão da frota a longo prazo.

== Otimização da Atribuição de Pedidos (Lógica de Despacho)

A função `assign_pending_requests` é o componente central. O processo é executado nos seguintes passos:

1. **Construção da Matriz de Custos**: Uma matriz $N times M$ onde cada célula representa o custo detalhado (via `calculate_detailed_cost`) para o veículo $i$ atender o pedido $j$.
2. **Aplicação de Restrições (Pruning)**: Custos infinitos para capacidades insuficientes.
3. **Resolução**: O algoritmo selecionado (Simulated Annealing) encontra a permutação que minimiza a soma da matriz.
4. **Execução**: Aplica as atribuições, atualizando o estado dos veículos para `ON_WAY_TO_CLIENT`.

= Metodologia de Testes e Resultados

Utilizámos um sistema de *benchmark* automatizado (`BenchmarkRunner`) que executa simulações paralelas para testar 9 combinações de algoritmos durante 28 dias simulados.

== Métricas de Avaliação
- **Financeiras**: Lucro Líquido, Receita Total.
- **Operacionais**: Taxa de Ocupação, Tempo Médio de Espera, Km Vazios, Pedidos Falhados.
- **Ambientais**: Emissões Totais de CO2.

== Análise dos Resultados (Dados Reais)

Os dados recolhidos mostram uma clara vantagem para os algoritmos informados e de otimização global.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto, auto),
    align: center,
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Routing*], [*Assignment*], [*Lucro (€)*], [*Entregas*], [*Falhas*], [*Espera (min)*], [*CO2 (kg)*],
    [BFS], [Greedy], [76 271], [11 183], [2 907], [15.87], [6 599],
    [Greedy], [Hill Climbing], [76 414], [11 531], [2 559], [14.68], [6 131],
    [A\*], [Greedy], [79 628], [11 613], [2 477], [13.22], [6 391],
    [*A\**], [*Sim. Annealing*], [*79 348*], [*11 921*], [*2 168*], [*11.72*], [*6 029*],
  ),
  caption: [Comparação de Performance (28 dias de operação)],
)

1.  **Eficiência do A\***: A combinação **A\* + Simulated Annealing** completou o maior número de pedidos (**11 921**), com o menor número de falhas (**2 168**). O A\* permite encontrar rotas mais rápidas, libertando os veículos mais cedo.
2.  **Qualidade de Serviço**: O tempo médio de espera baixou drasticamente de 15.87 min (BFS) para **11.72 min** (A\* + SA).
3.  **Sustentabilidade**: A otimização global permitiu reduzir as emissões de CO2 para o valor mínimo registado (**6 029 kg**), demonstrando que uma frota bem gerida é mais ecológica.

= Conclusão e Reflexão

O sistema desenvolvido gere com sucesso uma frota mista em Braga. A combinação de **A\*** para navegação e **Simulated Annealing** para atribuição revelou-se a mais robusta, equilibrando lucro, satisfação do cliente e eficiência energética.

== Reflexão e Dificuldades
Durante o desenvolvimento, a maior dificuldade foi equilibrar as restrições dos Veículos Elétricos. Inicialmente, os EVs ficavam muitas vezes "presos" sem carga longe das estações. A implementação de uma lógica de "reserva de bateria" e a penalização exponencial (`BATTERY_RISK_EXPONENT = 2.0`) na função de custo foram cruciais para resolver isto.
Além disso, a afinação dos parâmetros do Simulated Annealing (temperatura inicial de 450.0) exigiu vários testes para evitar que o algoritmo convergisse prematuramente para ótimos locais.

Aprendemos que num problema dinâmico e real, a solução "ótima" matemática nem sempre é a melhor solução prática se demorar muito a calcular; o equilíbrio entre rapidez de decisão e qualidade da decisão é fundamental.

= Referências
- Russell, S., & Norvig, P. "Artificial Intelligence: A Modern Approach".
- Documentação OSMnx e NetworkX.
- Boeing, G. (2017). "OSMnx: New Methods for Acquiring, Constructing, Analyzing, and Visualizing Complex Street Networks".

#heading(numbering: none)[Anexos]

#figure(
  rect(width: 100%, height: 200pt, fill: luma(240), stroke: 1pt + gray)[
    \ \ \ *Inserir aqui: Diagrama UML de Classes do Simulador*
  ],
  caption: [Arquitetura do Sistema],
)