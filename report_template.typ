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

Pedidos de transporte são requisitados consoante a hora do dia, com origem em diferentes partes da cidade.  Podem requisitar ser atendidos rapidamente, como também optar por uma viagem ecológica. A empresa tem à sua disposição carros elétricos (baratos de operar, mas com autonomia limitada e de recarga demorada) e carros a combustão (rápidos de abastecer, mas caros e poluentes).

O nosso trabalho é criar o programa para gerir esta operação. Um sistema inteligente que decide, em tempo real:
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
  - *Trânsito*: Simulado com **Ruído de Perlin 3D** e curvas Gaussianas para horas de ponta (08:30, 13:00, 18:00, 21:00), afetando a velocidade nas arestas.
  - *Meteorologia*: Um sistema probabilístico altera o estado entre Sol, Nublado, Chuva e Tempestade, aplicando penalizações de velocidade.
  - *Falhas de Infraestrutura*: As estações de carregamento têm uma probabilidade de falha (`0.01%` por tick).
- **Reprodutibilidade**: Utilizamos *seeds* fixas (gerador de pedidos: `12345`, frota: `42`) no gerador de números pseudo-aleatórios para garantir benchmarks justos.

== Agentes (Pedidos)
Os pedidos não são homogéneos; cada cliente tem características que afetam o lucro e a urgência.

=== Geração de Pedidos (Processo de Poisson)
A taxa de chegada $lambda(t)$ varia ao longo do dia:
- **Madrugada** (00:00-06:30): 0.1-0.16 pedidos/min
- **Manhã** (07:30-09:30): 0.62 pedidos/min (pico)
- **Almoço** (12:00-14:00): 0.38 pedidos/min
- **Tarde** (17:00-19:30): 0.74 pedidos/min (pico máximo)
- **Pré-noite** (19:30-21:00): 0.32 pedidos/min
- **Noite** (22:00-00:00): 0.26 pedidos/min

Intervalo até próximo pedido: $Delta t = -ln(U) / lambda(t)$, onde $U tilde "Uniforme"(0,1)$

=== Características dos Pedidos
- **Prioridade (1-5)**: 
  - Definida pela hora do dia e aleatoriedade
  - VIP (prioridade 5): 20% durante picos, 5% durante horas normais
  - Normal (1-4): Distribuição uniforme
- **Preço Dinâmico**: 
  - Base: €2.50
  - Por km: €0.80
  - Multiplicador para grupos grandes (>4 passageiros): ×1.3
  - Fórmula: $P = (2.50 + 0.80 times D) times M$
- **Preferência Ecológica**: 30% dos clientes preferem veículos elétricos
- **Passageiros**: 1-4 (90%), 5-7 (10%)
- **Timeout Escalonado**: 
  - Prioridade 1: 30 minutos
  - Prioridade 5 (VIP): 10 minutos
  - Fórmula: $T_"max" = 30 - (("Prio" - 1) times 5)$

= Modelação e Implementação

== Ambiente de Simulação
Utilizamos um mapa real da cidade de Braga obtido via `OSMnx` e serializado em `braga_map_cache.pkl`.

=== Grafo de Navegação
Os nós representam intersecções e as arestas segmentos de estrada. As distâncias são calculadas via fórmula de Haversine (distância na esfera terrestre), permitindo navegação precisa no ambiente urbano.

=== Trânsito Dinâmico
O `TrafficManager` simula ofluxo de tráfego utilizando uma combinação sofisticada de:

- **Curvas Gaussianas**: Para modelar picos de hora de ponta:
  - Manhã (08:30): intensidade 0.6, largura 1.5
  - Almoço (13:00): intensidade 0.2, largura 1.2
  - Tarde (18:00): intensidade 0.8, largura 1.8 (pico máximo)
  - Noite (21:00): intensidade 0.1, largura 1.5
  - Base: 0.1

- **Fórmula de Ganho Linear**: $"gain" = "rush_intensity" times 5.0$
  - Esta formulação aumenta o trânsito proporcionalmente à intensidade de pico
  - Durante picos, intensidade 0.8 → ganho ≈ 4.0

- **Ruído de Perlin (3D)**: Para introduzir variabilidade espacial e temporal orgânica, evitando padrões repetitivos. O ruído é aplicado nas coordenadas $(x,y,t)$ onde $x$ e $y$ são coordenadas geográficas e $t$ é o tempo simulado.

=== Sistema Meteorológico
Um sistema de clima dinâmico que afeta globalmente a velocidade dos veículos:
- **Sol** (45% do tempo): penalização 1.0× (sem impacto)
- **Nublado** (20% do tempo): penalização 1.0× (sem impacto)
- **Chuva** (20% do tempo): penalização 1.3×
- **Tempestade** (15% do tempo): penalização 1.6×

A transição entre estados meteorológicos é feita através de Ruído de Perlin 1D sobre o tempo, garantindo mudanças suaves e realistas.

=== Hotspots (Zonas de Alta Densidade)
A distribuição de pedidos não é uniforme. Implementamos um sistema de **Hotspots** que modela zonas de alta procura:

**Principais Hotspots**:
- Universidade do Minho (ativa 07:00-23:00, peso 3.0)
- Estação de Comboios (ativa 06:00-22:00, peso 2.5)
- Braga Parque (ativa 09:00-22:00, peso 2.0)
- Hospital de Braga (ativa 24h, peso 1.5)
- Centro Histórico (ativa 09:00-01:00, peso 2.0)

**Padrões de Geração de Pedidos**:
- 40%: Hotspot → Destino Aleatório
- 30%: Origem Aleatória → Hotspot
- 20%: Hotspot → Hotspot
- 10%: Aleatório → Aleatório

Este sistema garante que os pedidos se concentram em zonas realistas (universidades de manhã, centro à noite, etc.).

=== Falhas de Infraestrutura
As estações de carregamento (EV) e de abastecimento (combustão) podem falhar estocasticamente:
- **Probabilidade de Falha**: 0.01% por tick de simulação
- **Tempo de Recuperação**: 120 minutos (2 horas)
- **Impacto**: Veículos precisam de desviar para estações alternativas, aumentando custos operacionais

== Agentes (Veículos)
A frota é heterogénea, composta por veículos com atributos distintos. A configuração padrão inclui:

=== Veículos a Combustão (Gas)
- **Quantidade**: 5 veículos (frota fixa)
- **Autonomia**: Entre 600-900 km
- **Tempo de Reabastecimento**: 5 minutos
- **Custo Operacional**: €0.15/km (combustível + manutenção)
- **Emissões**: ~120g CO₂/km
- **Vantagens**: Alta autonomia, reabastecimento rápido
- **Desvantagens**: Custo elevado, poluente

=== Veículos Elétricos (EV)
- **Quantidade**: 5 veículos (frota fixa)
- **Autonomia**: Entre 200-420 km
- **Tempo de Recarga**: 
  - Nível 1 (lento): 45-60 minutos
  - Nível 2 (rápido): 20-30 minutos
- **Custo Operacional**: €0.04/km (eletricidade)
- **Emissões**: 0g CO₂/km (localmente)
- **Vantagens**: Custo muito reduzido, zero emissões locais
- **Desvantagens**: Autonomia limitada, tempo de recarga elevado

=== Gestão de Bateria/Combustível
O sistema implementa uma lógica de gestão preventiva:
- **Limiar Crítico**: 30 km de autonomia restante
- **Penalização Exponencial**: Quando a autonomia \< 30 km, a função de custo aplica uma penalização quadrática: 
  $P_"bateria" = W_"bateria" times ((30 - "autonomia") / 30)^2$
- **Decisão de Recarga**: Veículos são enviados para estações quando:
  - Autonomia restante \< 50 km E não há pedidos urgentes
  - Após completar um pedido, se autonomia \< 80 km

**Composição Detalhada da Frota (10 veículos)**:
- **EVs** (5 total): 1×3 pax (250km), 2×4 pax (300-350km), 2×7 pax (380-420km)
- **Gas** (5 total): 1×3 pax (600km), 2×4 pax (700-750km), 2×7 pax (800-900km)

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
    - *Heurística*: Usamos o **tempo de viagem em linha reta** à velocidade máxima como estimativa admissível:
      $h(n) = "distância_Haversine"(n, "destino") / 120 "km/h"$
    - *Por que é o melhor?*: Como a estimativa é admissível (nunca sobrestima o custo real), o A\* garante matematicamente que encontra o caminho mais rápido possível.
    - *Complexidade*: Temporal e espacial $O(b^d)$, onde $b$ é o fator de ramificação e $d$ a profundidade da solução.

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
    -  *Como funciona?*: Algoritmo de otimização estocástica inspirado no processo físico de recozimento de metais. No início (alta temperatura) aceita soluções piores probabilisticamente para explorar o espaço. À medida que "arrefece", foca-se em melhorar a solução.
    - *Parâmetros Implementados*:
      - Temperatura Inicial ($T_0$): 200.0
      - Fator de Arrefecimento ($alpha$): 0.96
      - Critério de Aceitação: $P("aceitar") = e^(-Delta E / T)$
      - Operadores de Vizinhança: Assign, Unassign, Swap, Move, Replace
    - *Vantagem*: Escapa aos mínimos locais, encontrando soluções globais melhores para a gestão da frota a longo prazo.
    - *Desvantagem*: Mais lento que greedy, requer afinação de parâmetros.

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

= Correspondência com as Tarefas do Enunciado

Esta secção mapeia explicitamente cada tarefa solicitada no enunciado à nossa implementação:

#figure(
  table(
    columns: (auto, 1fr),
    align: (center, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0  { luma(230) } else if calc.odd(row) { luma(250) } else { white },
    
    [*Tarefa*], [*Implementação*],
    
    [Formular o problema\ como procura], 
    [✓ Definido como Otimização Combinatória Dinâmica com estado $S_t = (A, B, V)$, operadores (Assign, Swap, Move, etc.), e função de energia multiobjetivo (Secção "Formulação do Problema")],
    
    [Representar cidade\ como grafo],
    [✓ Grafo real de Braga via OSMnx, nós=intersecções, arestas=estradas com distâncias Haversine (Secção "Ambiente de Simulação")],
    
    [Desenvolver estratégias\ informadas e não\ informadas],
    [✓ Implementados BFS (não informada), Greedy, A\\* (informadas). A\\* usa heurística $h(n) = d_"Haversine" / 120$ (Secção "Algoritmos de Navegação")],
    
    [Implementar sistema\ de simulação dinâmica],
    [✓ Simulador com chegadas de pedidos via Processo de Poisson, trânsito dinâmico (Perlin + Gaussianas), meteorologia, falhas de infraestrutura (Secções "Modelação", "Dinâmica de Execução")],
    
    [Avaliar eficiência\ com métricas],
    [✓ Benchmark com 9 combinações de algoritmos, métricas: Lucro, Taxa de Ocupação, Tempo de Espera, km Vazios, CO2 (Secção "Resultados")],
    
    [Simular condições\ dinâmicas],
    [✓ Trânsito variável (picos de hora), meteorologia (Sol/Chuva/Tempestade), falhas de estações (0.01%/tick) (Secção "Ambiente de Simulação")],
  ),
  caption: [Correspondência Tarefa-Implementação],
)

== Funcionalidades Extra Implementadas
Além dos requisitos base, implementámos:

1. **Hotspots Geográficos**: Sistema de zonas de alta densidade (Universidades, Estação, Hospital) com ativação temporal e ponderação, modelando padrões realistas de procura urbana.

2. **Gestão Preventiva de Bateria**: Penalização quadrática para autonomia \< 30 km, forçando planeamento antecipado de recargas.

3. **Sistema de Prioridade Escalonado**: Timeouts diferenciados (VIP: 10 min, Normal: 30 min), simulando clientes premium vs. standard.

4. **Trânsito com Picos Realistas**: Modelagem de congestionamento via curvas Gaussianas + Ruído de Perlin 3D, simulando variação espacial e temporal do tráfego.

5. **Benchmark Automatizado Paralelo**: Sistema de testes concorrentes (`ProcessPoolExecutor`) para comparar 9 configurações de algoritmos em 28 dias simulados.

6. **Reprodutibilidade Total**: Seeds fixas (42) garantem que benchmarks são justos e replicáveis.

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