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

A solução implementada utiliza algoritmos lecionados na cadeira de Inteligência Artificial, nomeadamente algoritmos de procura informada e algoritmos de otimização local para resolver o problema de atribuição de veículos e pedidos em tempo real.

== Objetivos
O objetivo principal é desenvolver e comparar algoritmos de procura e otimização para:
- Maximizar o lucro operacional (Receita - Custos).
- Minimizar o tempo de espera dos clientes.
- Garantir a sustentabilidade ambiental (redução de CO2).
- Gerir eficazmente as restrições de autonomia dos veículos elétricos (EVs).

= Descrição do Problema

A *TaxiGreen* é uma empresa moderna de transporte urbano que enfrenta um desafio complexo: gerir uma frota mista de veículos (elétricos e a combustão) numa cidade movimentada como Braga. O objetivo não é apenas levar passageiros do ponto A ao ponto B, mas fazê-lo da forma mais eficiente e sustentável possível.

Pedidos de transporte são requisitados consoante a hora do dia, com origem e destino em diferentes partes da cidade.  Podem requisitar ser atendidos rapidamente, como também optar por uma viagem ecológica. A empresa tem à sua disposição carros elétricos (baratos de operar, mas com autonomia limitada e recarga demorada) e carros a combustão (rápidos de abastecer, mas caros e poluentes).

O nosso trabalho é criar um programa para gerir esta operação. Um sistema inteligente que decide, em tempo real:
1.  Que veículo deve atender qual pedido?
2.  Qual o melhor caminho para lá chegar, fugindo ao trânsito?
3.  Quando é que um carro elétrico deve parar para carregar antes que fique sem bateria?

Para resolver isto, transformamos a cidade num *Grafo* (uma rede de nós e arestas) obtido através do _OSMnx_ e utilizamos algoritmos de Inteligência Artificial para encontrar as melhores soluções de rota e atribuição.

= Formulação do Problema

Para responder ao desafio de gestão de frota da TaxiGreen, o problema foi modelado como um problema de Otimização Combinatória, resolvido através de uma pesquisa local.

Ao contrário de um problema de navegação simples, o desafio aqui não é encontrar apenas um caminho, mas sim encontrar a configuração de alocação ótima entre veículos e pedidos num determinado instante, considerando restrições de capacidade e autonomia.

== Definição do Estado (S)

Definimos o estado do sistema num instante $t$ como um tuplo $S_t = (A, B, V)$, onde:

- **A (Atribuições)**: Um mapeamento $V -> R union {emptyset}$, onde $V$ é o conjunto de todos os veículos da frota e $R$ é o conjunto de pedidos por recolher. Se $A[v] = r$, significa que o veículo $v$ está a servir o pedido $r$. Se $A[v] = emptyset$, o veículo está livre.
- **B (Fila de Espera)**: O conjunto de pedidos pendentes $R_"pendentes"$ que foram recebidos mas ainda não foram recolhidos por nenhum veículo.
- **V (Estado Projetado da Frota)**: Um vetor contendo o estado futuro estimado de cada veículo $v in V$ após cumprir a atribuição atual. Para cada veículo, projeta-se:
  - $"Posição"_"final"$: Localização após a entrega.
  - $"Autonomia"_"final"$: Autonomia restante estimada após a entrega.
  - $"Tempo"_"livre"$: Instante de tempo simulado em que o veículo ficará novamente disponível.

*Nota*: Esta representação permite ao algoritmo avaliar não apenas o custo imediato, mas também a viabilidade futura (ex: evitar atribuir um pedido a um veículo que ficaria com autonomia negativa).

=== Estado Inicial ($S_0$)

O estado inicial da simulação é configurado deterministicamente no arranque do sistema:

- **Atribuições Vazias**: $forall v in V: A[v] = emptyset$ — todos os 10 veículos começam livres, sem pedidos atribuídos.
- **Fila de Espera Vazia**: $B = emptyset$ — não existem pedidos pendentes no instante $t = 0$.
- **Frota Posicionada**: Cada veículo é colocado numa posição aleatória do grafo de Braga, determinada pela seed `42`. As posições são nós válidos da rede rodoviária.
- **Autonomia Aleatória**: Todos os veículos iniciam com o depósito/bateria com autonomia aleatória:
  - Veículos a combustão: 600-900 km (conforme especificação do veículo)
  - Veículos elétricos: 200-420 km (conforme especificação do veículo)
- **Tempo Simulado**: $t_0 = $ 00:00 do primeiro dia de simulação.

Formalmente: $S_0 = ({v_i -> emptyset}_(i=1)^(10), emptyset, {"pos": "random"(42), "autonomia": "random"(42), "tempo": t_0})$

=== Estado Objetivo ($S^*$)

Ao contrário de problemas de procura clássicos (como o puzzle de 8 peças ou navegação ponto-a-ponto), este problema de gestão de frota é um *problema de otimização contínua e dinâmica*. Não existe um estado objetivo discreto que, uma vez atingido, termine a execução.

Em vez disso, o objetivo é definido como a *minimização contínua* da função de energia ao longo do tempo:

$ S^* = arg min_S E(S) quad forall t $

*Características do Estado Objetivo*:

1. **Não-Terminal**: O sistema opera indefinidamente, processando novos pedidos à medida que chegam. Nunca existe um "estado final" onde o problema está "resolvido".

2. **Ótimo Local vs. Global**: Em cada instante $t$, procuramos o estado $S_t^*$ que minimiza $E(S_t)$. Contudo, decisões ótimas locais podem não ser globalmente ótimas (ex: aceitar um pedido agora pode impedir aceitar um VIP que chegará em 5 minutos).

3. **Satisfação de Restrições**: Um estado é considerado *válido* se:
   - $forall v: "autonomia"_"final"(v) >= 0$ (nenhum veículo fica sem combustível/bateria)
   - $forall v: "passageiros"(A[v]) <= "capacidade"(v)$ (capacidade respeitada)
   - Minimização da fila de espera $|B|$ (pedidos atendidos atempadamente)

4. **Critério Prático de Sucesso**: Na prática, consideramos que o sistema atinge um "bom estado" quando:
   - Taxa de pedidos falhados < 15%
   - Tempo médio de espera < 15 minutos
   - Lucro operacional positivo

== Operadores (Espaço de Ações)

Todas as ações que modificam o estado $S$ são tratadas como operadores. Dividimos em duas categorias: operadores de vizinhança (usados pelo algoritmo de otimização para explorar o espaço de soluções) e transições automáticas do ambiente (eventos que alteram o estado independentemente do algoritmo).

=== Operadores de Vizinhança (Algoritmo)

Para navegar no espaço de estados e encontrar soluções melhores, definimos cinco operadores que modificam o estado $S$ para gerar um estado vizinho $S'$:

1.  *Assign(v, r)*: Retira um pedido $r$ da fila de espera ($B$) e atribui-o a um veículo livre $v$.
2.  *Unassign(v)*: Remove a atribuição atual de um veículo $v$, devolvendo o pedido à fila de espera ($B$). Útil para tornar veículos disponíveis de forma a conseguirem ser atribuidos a pedidos com uma prioridade superior que possam surgir.
3.  *Swap(v1, v2)*: Troca os pedidos atribuídos entre dois veículos $v_1$ e $v_2$. Este operador permite otimizar a frota trocando, por exemplo, um pedido de curta distância de um veículo a combustão para um elétrico, e vice-versa.
4.  *Move(v_src, v_dst)*: Move um pedido de um veículo ocupado para um livre.
5.  *Replace(v, r_new)*: Substitui o pedido atual de um veículo por um da fila de espera.

=== Transições Automáticas do Ambiente

Além dos operadores controlados pelo algoritmo, existem transições de estado do ambiente:

1.  *Timeout(r)*: Remove um pedido $r$ da fila de espera ($B$) por expiração.
2.  *CompleteTrip(v)*: Quando um veículo $v$ completa uma viagem, liberta-o ($A[v] = emptyset$).
3.  *StartRecharge(v)*: Envia um veículo $v$ para uma estação de recarga. Altera o estado do veículo para indisponível.
4.  *CompleteRecharge(v)*: Restaura a autonomia do veículo e torna-o novamente disponível para atribuição.
5.  *NewRequest(r)*: Adiciona um novo pedido $r$ à fila de espera ($B$), o que obriga uma reavaliação do estado.

== Teste Objetivo e Função de Custo

Sendo um problema de otimização, o "Teste Objetivo" não é binário (atingiu/não atingiu), mas sim a minimização de uma Função de Energia (Custo) Global $E(S)$. O algoritmo procura $S^*$ tal que $E(S^*) <= E(S), forall S$.

=== Função de Energia Global

A função de avaliação do estado completo é:
$ E(S) = sum_(v in "Frota") C(v, A[v]) + sum_(r in "Fila") C_"espera"(r) + P_"viabilidade" $

Onde $C(v, A[v])$ é o custo de atribuição do veículo $v$ ao seu pedido atual, $C_"espera"(r)$ é a penalização por pedidos na fila, e $P_"viabilidade"$ são restrições que impossibilitam o estado.

=== Custo de Atribuição Individual

O custo de atribuir um veículo $v$ a um pedido $r$ é composto por 8 fatores:

$ C(v, r) = C_"tempo" + C_"espera" + C_"ambiente" + C_"capacidade" + C_"bateria" + C_"logística" + C_"oportunidade" + C_"lucro" $

#figure(
  table(
    columns: (auto, 2fr, auto),
    align: (left, left, center),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if calc.odd(row) { luma(250) } else { white },
    [*Componente*], [*Descrição*], [*Peso*],
    [$C_"tempo"$], [Tempo de viagem até ao cliente (via A\*)], [1.0],
    [$C_"espera"$], [Bónus negativo por tempo de espera e prioridade do pedido], [4.0 / 30.0],
    [$C_"ambiente"$], [Penalização se veículo a combustão atende pedido ecológico], [15.0/km],
    [$C_"capacidade"$], [Penalização por lugares não utilizados (desperdício)], [0.5/lugar],
    [$C_"bateria"$], [Risco se autonomia restante < 30km], [20.0],
    [$C_"logística"$], [Distância a postos de abastecimento e hotspots após entrega], [0.5 / 1.0],
    [$C_"oportunidade"$], [EVs em pedidos não-eco quando há pedidos eco na fila de espera], [50.0],
    [$C_"lucro"$], [Ajuste baseado no lucro projetado (negativo = mais atrativo)], [10.0],
  ),
  caption: [Componentes da Função de Custo de Atribuição],
) <tab:custo-atribuicao>

=== Penalização da Fila de Espera

Pedidos que permanecem na fila de espera incorrem num custo crescente:
$ C_"espera"(r) = 160 + ("Prio"^2 times 30) + ("Age" times 8) $

- $"Prio"$: Prioridade do pedido (1-5). O termo quadrático garante que VIPs (prio 5) custam 25× mais que normais (prio 1).
- $"Age"$: Tempo de espera em minutos desde a criação do pedido.

=== Restrições de Viabilidade

Um estado é considerado inválido ($P_"viabilidade" = infinity$) se:
- Autonomia final de qualquer veículo < 0 (ficaria sem combustível/bateria)
- Capacidade de passageiros insuficiente
- Impossibilidade de chegar a um posto de abastecimento após a entrega

== Dinâmica de Execução

O algoritmo de procura não é executado apenas uma vez. O sistema opera com um planeamento contínuo podendo alterar decisões anteriores de acordo com novos pedidos ou alterações dinâmicas (ex: trocar pedidos já atribuídos a veículos ). O processo de procura é reiniciado sempre que ocorre um evento significativo no ambiente:
- Chegada de um novo pedido.
- Um veículo torna-se disponível (termina viagem ou recarga).
- **Timeouts Escalonados**: O tempo máximo de espera depende da prioridade do cliente (ver @sec:atributos-pedidos).

Desta forma, o sistema adapta-se dinamicamente, reavaliando decisões anteriores se uma nova configuração apresentar menor custo global.

== Determinismo Estocástico (Reprodutibilidade)

Um aspeto crítico do sistema é a sua **reprodutibilidade total**. Apesar de utilizar processos estocásticos (aleatoriedade controlada), a simulação produz **exatamente os mesmos resultados** em cada execução, desde que os parâmetros iniciais se mantenham iguais.

=== Princípio de Funcionamento

Ao invés de usar o gerador global `random.random()`, cada componente da simulação utiliza uma instância isolada de `random.Random(seed)` — um _Pseudo-Random Number Generator_ (PRNG) determinístico. Dado o mesmo _seed_ (semente), a sequência de números "aleatórios" gerada é sempre idêntica.

Isto significa que:
- Duas execuções com os mesmos _seeds_ geram **pedidos idênticos** nos mesmos instantes de tempo.
- Os veículos são colocados nas **mesmas posições iniciais**.
- O **clima** (via Ruído de Perlin) segue a mesma evolução temporal.
- Os resultados dos benchmarks são **diretamente comparáveis** entre algoritmos.

=== Componentes com Seed Fixa

#figure(
  table(
    columns: (auto, auto, 1.5fr),
    align: (center, center, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Componente*], [*Seed*], [*O que controla*],
    [Gerador de Pedidos], [`12345`], [Intervalos de chegada, origens/destinos (incluindo hotspots), prioridades, preferências ecológicas],
    [Criação da Frota], [`42`], [Posições iniciais dos 10 veículos no mapa],
    [Trânsito (Perlin)], [`42`], [Padrões espaciais de congestionamento via ruído 3D],
    [Meteorologia (Perlin)], [`42`], [Transições de clima (Sol, Chuva, Tempestade)],
    [Falhas de Estações], [`42`], [Quando e quais estações falham (0.01% por tick)],
  ),
  caption: [Seeds Fixas Utilizadas na Simulação],
)

=== Processos Estocásticos Implementados

*Geração de Pedidos (Processo de Poisson Não-Homogéneo)*:
- A taxa de chegada $lambda(t)$ varia ao longo do dia para simular picos de procura.
- O intervalo até ao próximo pedido é dado por: $Delta t = -ln(U) / lambda(t)$
- Onde $U in (0, 1]$ é gerado pelo PRNG com seed `12345`.
- Isto cria intervalos menores (mais pedidos) quando $lambda(t)$ é alto (horas de ponta).

*Seleção de Hotspots*:
- Origens e destinos são selecionados com base em pesos dos hotspots ativos.
- A escolha ponderada usa `rng.choices()` com a mesma seed do gerador de pedidos.

*Trânsito e Meteorologia*:
- Ruído de Perlin 3D para variação espacial/temporal do tráfego.
- Ruído de Perlin 1D para transições suaves de clima.
- Ambos usam `seed=42` como base do ruído.

*Falhas de Infraestrutura*:
- Cada estação tem 0.01% de probabilidade de falhar por tick de simulação.
- Utiliza um PRNG dedicado (`station_rng`) com seed `42`.
- As mesmas estações falham nos mesmos momentos em cada execução.

=== Exceção (Componente Não-Determinístico)

O único componente que utiliza o gerador global `random.random()` não seeded é:
- **Operadores do Simulated Annealing**: A escolha probabilística de operadores de vizinhança (Swap, Move, Replace, etc.) introduz ligeira variabilidade.

Esta variabilidade é intencional nos algoritmos de otimização: permite explorar diferentes caminhos no espaço de soluções, enquanto o _workload_ (pedidos e condições ambientais) permanece idêntico entre execuções.

== Características dos Pedidos

Cada pedido de transporte é modelado como um agente com atributos que influenciam a atribuição e o custo. As características são geradas deterministicamente a partir da seed `12345`.

=== Taxa de Chegada (Processo de Poisson)

A taxa de chegada $lambda(t)$ varia ao longo do dia, calculada como: $lambda(t) = 0.2 + ("intensidade" times 0.6)$

*Nota sobre escala*: Os valores apresentados são proporcionais ao tamanho da frota simulada (10 veículos). Numa frota real com milhares de veículos, a taxa de pedidos seria proporcionalmente maior. Os padrões temporais (picos matinais e vespertinos excluindo os fim de semana) baseiam-se em dados reais do setor TVDE em Portugal#footnote[IMT (2025). Plataforma conjunta entre IMT, Bolt e Uber. Disponível em: https://www.imt-ip.pt].

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, center, center),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Período*], [*Intensidade*], [*Taxa (pedidos/min)*],
    [Madrugada (00:00-06:30)], [0.1], [0.26],
    [Manhã (07:30-09:30)], [0.7], [0.62 (pico)],
    [Almoço (12:00-14:00)], [0.3], [0.38],
    [Tarde (17:00-19:30)], [0.9], [0.74 (pico máximo)],
    [Pré-noite (19:30-21:00)], [0.2], [0.32],
    [Noite (22:00-00:00)], [0.1], [0.26],
  ),
  caption: [Taxa de Chegada de Pedidos por Período],
)

=== Atributos dos Pedidos <sec:atributos-pedidos>

- **Prioridade (1-5)**: VIP (prioridade 5) tem 20% de probabilidade durante picos, 5% noutros períodos. Prioridades 1-4 são uniformemente distribuídas.
- **Preço**: $P = (2.50 + 0.80 times D) times M$, onde $D$ é a distância em km e $M=1.3$ para grupos >4 passageiros.
- **Preferência Ecológica**: 30% dos clientes preferem veículos elétricos.
- **Passageiros**: 1-4 (90%), 5-7 (10%).
- **Timeout**: $T_"max" = 30 - (("Prio" - 1) times 5)$ minutos (VIP: 10 min, Normal: 30 min).

= Modelação e Implementação

== Ambiente de Simulação
Utilizamos um mapa real da cidade de Braga obtido via `OSMnx` e serializado em `braga_map_cache.pkl`.

#figure(
  image("Braga.PNG"),
    caption: [Grafo da cidade de Braga (obtido através do OSMnx)]
)

=== Grafo de Navegação
Os nós representam intersecções e as arestas segmentos de estrada. As distâncias são calculadas via fórmula de Haversine (distância na esfera terrestre), permitindo navegação precisa no ambiente urbano.

=== Trânsito Dinâmico
O `TrafficManager` simula o fluxo de tráfego utilizando uma combinação sofisticada de:

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
O clima é simulado através de Ruído de Perlin 1D sobre o tempo, garantindo transições suaves:
- **Sol** (noise < 0.45): penalização 1.0× (sem impacto)
- **Nublado** (noise 0.45-0.65): penalização 1.0× (sem impacto)
- **Chuva** (noise 0.65-0.85): penalização 1.3×
- **Tempestade** (noise > 0.85): penalização 1.6×

O valor de *noise* é normalizado para [0, 1] a partir do output do Perlin.

=== Hotspots (Zonas de Alta Densidade)
A distribuição de pedidos não é uniforme. Implementamos um sistema de **18 Hotspots** que modela zonas de alta procura na cidade de Braga:

**Principais Hotspots (por categoria)**:
- *Educação*: Universidade do Minho, Escola Sá de Miranda, Colégio D. Diogo de Sousa
- *Transportes*: Estação CP
- *Comercial*: Braga Parque, Nova Arcada, Minho Center
- *Saúde*: Hospital de Braga
- *Lazer*: Centro Histórico, Bares da Sé, Altice Fórum, Estádio Municipal
- *Tecnologia*: INL - Nanotecnologia
- *Industrial*: Parque Industrial

Este sistema garante que os pedidos se concentram em zonas realistas (universidades de manhã, bares à noite, hospital 24h, etc.).

=== Falhas de Infraestrutura
As estações de carregamento (EV) e de abastecimento (combustão) podem falhar:
- **Probabilidade de Falha**: 0.01% por tick de simulação
- **Tempo de Recuperação**: 120 minutos (2 horas)
- **Impacto**: Veículos precisam de desviar para estações alternativas, aumentando custos operacionais

== Agentes (Veículos)
A frota é heterogénea, composta por veículos com atributos distintos. A configuração padrão inclui:

#figure(
  table(
    columns: (auto, 1fr, 1fr),
    align: (left, center, center),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if calc.odd(row) { luma(250) } else { white },
    
    [*Característica*], [*Combustão (Gas)*], [*Elétrico (EV)*],
    [Quantidade], [5 veículos], [5 veículos],
    [Autonomia], [600-900 km], [200-420 km],
    [Tempo de Recarga], [5 minutos], [Lento: 45-60 min \ Rápido: 20-30 min],
    [Custo Operacional], [€0.12/km], [€0.04/km],
    [Emissões CO₂#footnote[Fonte: ACP Portugal, média nacional 2024]], [87g/km], [0g/km (local)],
    [Vantagens], [Alta autonomia, \ reabastecimento rápido], [Custo reduzido, \ zero emissões locais],
    [Desvantagens], [Custo elevado, \ poluente], [Autonomia limitada, \ recarga demorada],
  ),
  caption: [Comparação entre Tipos de Veículos da Frota],
)

=== Gestão de Bateria/Combustível
O sistema implementa uma lógica de gestão preventiva:
- **Limiar Crítico para Recarga**: Quando a autonomia restante \< 50 km, o veículo é automaticamente enviado para uma estação se não tiver nenhum pedido capaz de realizar.
- **Penalização na Função de Custo**: Quando a autonomia \< 30 km, a função de custo aplica uma penalização quadrática: 
  $P_"bateria" = W_"bateria" times ((30 - "autonomia") / 30)^2$
- **Tempo de Recarga**:
  - *Veículos a combustão*: Reabastecimento fixo de 5 minutos.
  - *Veículos elétricos*: Recarga proporcional à taxa da estação.

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
      $h(n) = "distância_Haversine"(n, "destino") / (2 "km/min")$
    - *Por que é o melhor?*: Como a estimativa é admissível (nunca sobrestima o custo real), o A\* garante matematicamente que encontra o caminho mais rápido possível.

== Algoritmos de Atribuição (Assignment)
O problema de atribuir $N$ veículos a $M$ pedidos é combinatório.

1.  **Greedy Assignment**:
    - *Como funciona?*: Faz a combinação mais barata imediata.
    - *Problema*: Não encontra a combinação ótima, pois descobre uma combinação e assume esta como resultado final.

2.  **Hill Climbing**:
    - *Como funciona?*: Tenta fazer trocas numa solução inicial. Se melhorar, aceita.
     - Operadores de Vizinhança: Assign, Unassign, Swap, Move, Replace
    - *Problema*: Fica preso em "mínimos locais".

3.  **Simulated Annealing**:
    -  *Como funciona?*: No início (alta temperatura) aceita soluções piores para explorar o espaço. À medida que "arrefece", foca-se em melhorar a solução.
    - *Parâmetros Implementados*:
      - Temperatura Inicial ($T_0$): 250.0 (aumenta para 450.0 quando há pedidos VIP)
      - Fator de Arrefecimento ($alpha$): 0.95
      - Critério de Aceitação: $P("aceitar") = e^(-Delta E / T)$
      - Operadores de Vizinhança: Assign, Unassign, Swap, Move, Replace
    - *Vantagem*: Escapa aos mínimos locais, encontrando soluções globais melhores para a gestão da frota a longo prazo.
    - *Desvantagem*: Mais lento que greedy, requer afinação de parâmetros.

=== Justificação das Escolhas de Design

A escolha do **Simulated Annealing** como algoritmo principal de atribuição resultou de uma análise cuidadosa das características do problema:

1. **Espaço de Estados Discreto e Combinatório**: O problema de atribuir $N$ veículos a $M$ pedidos gera um espaço de $(M+1)^N$ estados possíveis (cada veículo pode estar livre ou atribuído a qualquer um dos $M$ pedidos).
   
   *Cálculo para o nosso caso* (10 veículos, 20 pedidos pendentes):
   $ |S| = (20 + 1)^10 = 21^10  approx 1.66 times 10^13 $

      Se um computador avaliasse 1 milhão de estados por segundo, demoraria **mais de 500 anos** a explorar todas as combinações. Isto torna a procura exaustiva completamente impraticável, justificando o uso de Simulated Annealing.


2.  A função de custo do nosso problema possui múltiplos mínimos locais devido às interações entre restrições (autonomia, capacidade, preferências ecológicas). Algoritmos puramente greedy ou hill climbing ficam facilmente presos nos mínimos locais.

3. **Natureza Dinâmica do Problema**: Como novos pedidos chegam continuamente e o estado dos veículos muda (bateria, posição), o algoritmo é re-executado frequentemente. O SA adapta-se bem a este contexto porque cada execução parte de uma solução inicial diferente (estado atual), beneficiando da exploração aleatória inicial.

4. **Compromisso Tempo-Qualidade**: O Simulated Annealing oferece soluções de alta qualidade em tempo previsível. O parâmetro de temperatura dinâmica ($T_0 = 250$ ou $450$ para VIPs) permite ajustar automaticamente a exploração conforme a urgência.

5. **Alternativas Consideradas**:
   - *Algoritmo Húngaro*: Ótimo mas $O(n^3)$ e não lida bem com restrições complexas (autonomia, preferências).
   - *Programação Linear Inteira*: Garantia de optimalidade mas demasiado lento para decisões em tempo real.

== Otimização da Atribuição de Pedidos

A função `assign_pending_requests` é o componente central do sistema de decisão. O processo implementa várias otimizações para garantir eficiência em tempo real.

=== Pipeline de Atribuição

1. **Recolha de Candidatos**: Identifica veículos disponíveis e redirecionáveis (já a caminho de um cliente, mas que podem mudar de destino).

2. **Construção da Matriz de Custos** ($N times M$): Cada célula $C[i,j]$ representa o custo de atribuir o veículo $i$ ao pedido $j$, calculado via `calculate_detailed_cost`.

3. **Aplicação de Filtros (Pruning)**: Atribuições impossíveis recebem custo $infinity$:
   - Capacidade insuficiente para passageiros
   - Autonomia insuficiente para completar a viagem
   - Impossibilidade de chegar a um posto após a entrega

4. **Resolução via Meta-Heurística**: O Simulated Annealing encontra a configuração que minimiza a energia total.

5. **Execução e Reatribuição**: Aplica as decisões, libertando veículos de tarefas anteriores se necessário.

=== Otimizações Implementadas

#figure(
  table(
    columns: (auto, 2fr),
    align: (left, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if calc.odd(row) { luma(250) } else { white },
    [*Otimização*], [*Descrição*],
    [Estimativa Heurística], [Na construção da matriz de custos, usamos distância de Haversine em vez de A\* completo. Reduz o tempo de $O(E log V)$ para $O(1)$ por par veículo-pedido. O A\* real é usado apenas na rota final.],
    [Cache de Trânsito], [O `TrafficManager` mantém cache espacial de penalizações de trânsito, limpa a cada tick. Evita recalcular ruído de Perlin para posições próximas.],
    [Cache de Hotspots], [Cada hotspot pré-calcula os nós próximos (`node_cache`) na inicialização. Acelera a seleção de origens/destinos.],
    [Redirecionamento Dinâmico], [Veículos em estado `ON_WAY_TO_CLIENT` são incluídos na reavaliação. Permite trocar atribuições se surgir um pedido mais urgente.],
    [Temperatura Adaptativa], [A temperatura inicial do SA aumenta de 250 para 450 quando há pedidos VIP (prioridade ≥ 4) ou fila de espera saturada.],
    [Bónus de Estabilidade], [Manter a mesma atribuição dá um bónus de −5.0 no custo, evitando oscilações constantes (_jitter_) entre soluções equivalentes.],
  ),
  caption: [Otimizações Implementadas no Sistema de Atribuição],
)

A função de custo utilizada para preencher a matriz é detalhada na @tab:custo-atribuicao.

= Metodologia de Testes e Resultados

Utilizámos um sistema de *benchmark* automatizado (`BenchmarkRunner`) que executa simulações paralelas para testar 9 combinações de algoritmos durante 28 dias simulados.

== Métricas de Avaliação
- **Financeiras**: Lucro Líquido, Receita Total.
- **Operacionais**: Taxa de Ocupação, Tempo Médio de Espera, Km Vazios, Pedidos Falhados.
- **Ambientais**: Emissões Totais de CO2.

== Análise dos Resultados

Os dados recolhidos mostram uma clara vantagem para os algoritmos informados e de otimização global.

// AVISO ADICIONAR RESULTADOS
  #image("DadosBrutos.PNG")

1.  **Eficiência do A\***: A combinação **A\* + Simulated Annealing** completou o maior número de pedidos (**11 921**), com o menor número de falhas (**2 168**). O A\* permite encontrar rotas mais rápidas, libertando os veículos mais cedo.
2.  **Qualidade de Serviço**: O tempo médio de espera baixou drasticamente de 15.87 min (BFS) para **11.72 min** (A\* + SA).
3.  **Sustentabilidade**: A otimização global permitiu reduzir as emissões de CO2 para o valor mínimo registado (**6 029 kg**), demonstrando que uma frota bem gerida é mais ecológica.

= Correspondência com as Tarefas do Enunciado

Esta secção mapeia explicitamente cada tarefa solicitada no enunciado à nossa implementação:

// ATUALIZAR DADOS
#figure(
  table(
    columns: (auto, 1fr),
    align: (center, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0  { luma(230) } else if calc.odd(row) { luma(250) } else { white },
    
    [*Tarefa*], [*Implementação*],
    
    [Formular o problema\ como procura], 
    [✓ Definido como Otimização Combinatória Dinâmica com estado $S_t = (A, B, V)$, operadores (Assign, Swap, Move, etc.), e função de energia multiobjetivo],
    
    [Representar cidade\ como grafo],
    [✓ Grafo real de Braga via OSMnx, nós=intersecções, arestas=estradas com distâncias Haversine],
    
    [Desenvolver estratégias\ informadas e não\ informadas],
    [✓ Implementados BFS (não informada), Greedy, A\* (informadas).],
    
    [Implementar sistema\ de simulação dinâmica],
    [✓ Simulador com chegadas de pedidos via Processo de Poisson, trânsito dinâmico (Perlin + Gaussianas), meteorologia, falhas de infraestrutura],
    
    [Avaliar eficiência\ com métricas],
    [✓ Benchmark com 9 combinações de algoritmos, métricas: Lucro, Taxa de Ocupação, Tempo de Espera, km Vazios, CO2],
    
    [Simular condições\ dinâmicas],
    [✓ Trânsito variável (picos de hora), meteorologia (Sol/Chuva/Tempestade), falhas de estações (0.01%/tick)],
  ),
  caption: [Correspondência Tarefa-Implementação],
)

// ATUALIZAR DADOS
== Funcionalidades Extra Implementadas
Além dos requisitos base, implementámos:

1. **Hotspots Geográficos**: Sistema de 18 zonas de alta densidade com ativação temporal e ponderação.

2. **Gestão Preventiva de Bateria**: Penalização quadrática para baixa autonomia.

3. **Sistema de Prioridade Escalonado**: Timeouts diferenciados por prioridade.

4. **Trânsito Dinâmico**: Curvas Gaussianas + Ruído de Perlin 3D.

5. **Benchmark Automatizado Paralelo**: Sistema de testes concorrentes (`ProcessPoolExecutor`) para comparar 9 configurações de algoritmos em 28 dias simulados.

6. **Reprodutibilidade**: Seeds fixas garantem que benchmarks são justos e replicáveis.

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