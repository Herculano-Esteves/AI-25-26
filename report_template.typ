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

Para resolver isto, transformamos a cidade num Grafo (uma rede de nós e arestas) obtido através do _OSMnx_ e utilizamos algoritmos de Inteligência Artificial para encontrar as melhores soluções de rota e atribuição.

= Formulação do Problema

Para responder ao desafio de gestão de frota da TaxiGreen, o problema foi modelado como um problema de Otimização Combinatória resolvido através de pesquisa local.

Ao contrário de um problema de navegação simples, o desafio aqui não é encontrar apenas um caminho, mas sim encontrar a configuração de alocação ótima entre veículos e pedidos num determinado instante, considerando restrições de capacidade e autonomia.

A formulação segue a estrutura clássica de um problema de procura:
- *Estado*: Representação do sistema num dado instante
- *Operadores*: Ações que modificam o estado
- *Função de Custo*: Critério de otimização

== Representação do Estado

O sistema possui um estado $S_t$ num instante $t$, definido como um tuplo $S_t = (A, B, V)$:

- *A (Atribuições)*: Mapeamento $V -> R union {emptyset}$, cada veículo está livre ou atribuído a um pedido
- *B (Fila de Espera)*: Conjunto de pedidos pendentes ainda não atribuídos nem recolhidos por nenhum veículo
- *V (Estado Projetado)*: Para cada veículo, a posição, autonomia e tempo estimados após completar a tarefa atual

Esta representação permite avaliar não só o custo imediato, mas também a viabilidade futura (ex: evitar atribuições que deixariam um veículo sem autonomia).

*Tipo de problema*: O problema da TaxiGreen classifica-se como um problema de Otimização Combinatória em Ambiente Dinâmico.
- *Combinatório*: A escolha de atribuições veículo-pedido é discreta.
- *Dinâmico*: O ambiente muda (novos pedidos, trânsito) independentemente das ações do agente.
- *Parcialmente Observável*: O futuro (novos pedidos) é desconhecido, apenas estimado probabilisticamente.

=== Estado Inicial ($S_0$)

No arranque da simulação:
- *Atribuições*: $forall v in V: A[v] = emptyset$, todos os veículos livres
- *Fila*: $B = emptyset$, sem pedidos pendentes
- *Posições*: Veículos colocados em posições aleatórias (seed `42`)
- *Autonomia*: Combustão 600-900 km; Elétricos 200-420 km
- *Tempo*: $t_0 = $ 00:00 do primeiro dia

Formalmente: $S_0 = ({v_i -> emptyset}_(i=1)^(n), emptyset, {"pos", "autonomia", "tempo": t_0})$

=== Estado Objetivo ($S^*$)

Este é um *problema de otimização contínua e dinâmica* — não existe um estado final discreto. O objetivo é a *minimização contínua* da função de energia:

$ S^* = arg min_S E(S) quad forall t $

Características:
1. *Sem Fim*: O sistema processa pedidos indefinidamente
2. *Ótimo Local vs. Global*: Decisões locais podem não ser globalmente ótimas
3. *Restrições de Validade*: Autonomia $>= 0$, capacidade respeitada, fila minimizada
4. *Critério Prático*: Falhas < 15%, espera < 15 min, lucro positivo

== Operadores e Dinâmica de Execução

As ações que modificam o estado dividem-se em operadores de vizinhança (controlados pelo algoritmo) e transições automáticas (eventos do ambiente).

=== Operadores de Vizinhança

Cinco operadores para gerar estados vizinhos $S'$:

#figure(
  table(
    columns: (auto, 2fr),
    align: (left, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Operador*], [*Descrição*],
    [Assign(v, r)], [Atribui pedido $r$ da fila ao veículo livre $v$],
    [Unassign(v)], [Remove atribuição, devolvendo pedido à fila],
    [Swap(v₁, v₂)], [Troca pedidos entre dois veículos],
    [Move(v_src, v_dst)], [Move pedido de veículo ocupado para livre],
    [Replace(v, r_new)], [Substitui pedido atual por outro da fila],
  ),
  caption: [Operadores de Vizinhança],
)

=== Transições Automáticas do Ambiente

#figure(
  table(
    columns: (auto, 2fr),
    align: (left, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Evento*], [*Efeito*],
    [Timeout(r)], [Remove pedido expirado da fila],
    [CompleteTrip(v)], [Liberta veículo após entrega],
    [StartRecharge(v)], [Envia veículo para estação (indisponível)],
    [CompleteRecharge(v)], [Restaura autonomia e disponibilidade],
    [NewRequest(r)], [Adiciona pedido à fila, força reavaliação],
  ),
  caption: [Transições Automáticas do Ambiente],
)

#pagebreak()
=== Reavaliação Contínua

O sistema opera com planeamento contínuo, reiniciando a procura quando:
- Chega um novo pedido
- Um veículo fica disponível (termina viagem ou recarga)
- Ocorre timeout de pedido

Isto permite reatribuir pedidos dinamicamente se surgir uma configuração de menor custo.

== Função de Custo

O Teste Objetivo é a *minimização* da Função de Energia $E(S)$:

$ E(S) = sum_(v in "Frota") C(v, A[v]) + sum_(r in "Fila") C_"espera"(r) + P_"viabilidade" $

=== Custo de Atribuição Individual

O custo de atribuir veículo $v$ a pedido $r$ é:
$ C(v, r) = C_"tempo" + C_"espera" + C_"ambiente" + C_"capacidade" + C_"bateria" + C_"logística" + C_"oportunidade" + C_"lucro" $

#figure(
  table(
    columns: (auto, 2fr, auto),
    align: (left, left, center),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if calc.odd(row) { luma(250) } else { white },
    [*Componente*], [*Descrição*], [*Peso*],
    [$C_"tempo"$], [Tempo de viagem até ao cliente (via A\*)], [1.0],
    [$C_"espera"$], [Bónus negativo por tempo de espera e prioridade], [4.0 / 30.0],
    [$C_"ambiente"$], [Penalização se combustão atende pedido ecológico], [15.0/km],
    [$C_"capacidade"$], [Penalização por lugares não utilizados], [0.5/lugar],
    [$C_"bateria"$], [Risco se autonomia < 30km], [20.0],
    [$C_"logística"$], [Distância a postos e hotspots após entrega], [0.5 / 1.0],
    [$C_"oportunidade"$], [EVs em pedidos não-eco com pedidos eco na fila], [50.0],
    [$C_"lucro"$], [Ajuste baseado no lucro projetado], [10.0],
  ),
  caption: [Componentes da Função de Custo de Atribuição],
) <tab:custo-atribuicao>

=== Penalização da Fila de Espera

$ C_"espera"(r) = 160 + ("Prio"^2 times 30) + ("Age" times 8) $

O termo quadrático garante que VIPs (prio 5) custam 25× mais que normais (prio 1).

=== Restrições de Viabilidade

Um estado é inválido ($P_"viabilidade" = infinity$) se:
- Autonomia final < 0 para qualquer veículo
- Capacidade de passageiros insuficiente
- Impossibilidade de chegar a posto após entrega



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

- Curvas Gaussianas: Para modelar picos de hora de ponta:
  - Manhã (08:30): intensidade 0.6, largura 1.5
  - Almoço (13:00): intensidade 0.2, largura 1.2
  - Tarde (18:00): intensidade 0.8, largura 1.8 (pico máximo)
  - Noite (21:00): intensidade 0.1, largura 1.5
  - Base: 0.1

- Fórmula de Ganho Linear: $"gain" = "rush_intensity" times 5.0$
  - Esta formulação aumenta o trânsito proporcionalmente à intensidade de pico
  - Durante picos, intensidade 0.8 → ganho ≈ 4.0

- Ruído de Perlin (3D): Para introduzir variabilidade espacial e temporal orgânica, evitando padrões repetitivos. O ruído é aplicado nas coordenadas $(x,y,t)$ onde $x$ e $y$ são coordenadas geográficas e $t$ é o tempo simulado.

#figure(
  image("Transito.PNG", width: 100%),
  caption: [Visualização das camadas de trânsito (Perlin Noise)],
)

=== Sistema Meteorológico
O clima é simulado através de Ruído de Perlin 1D sobre o tempo, garantindo transições suaves:
- Sol (noise < 0.45): penalização 1.0× (sem impacto)
- Nublado (noise 0.45-0.65): penalização 1.0× (sem impacto)
- Chuva (noise 0.65-0.85): penalização 1.3×
- Tempestade (noise > 0.85): penalização 1.6×

O valor de *noise* é normalizado para [0, 1] a partir do output do Perlin.

=== Hotspots (Zonas de Alta Densidade)
A distribuição de pedidos não é uniforme. Implementamos um sistema de 18 Hotspots que modela zonas de alta procura na cidade de Braga:

Principais Hotspots (por categoria)::
- *Educação*: Universidade do Minho, Escola Sá de Miranda, Colégio D. Diogo de Sousa
- *Transportes*: Estação CP
- *Comercial*: Braga Parque, Nova Arcada, Minho Center
- *Saúde*: Hospital de Braga
- *Lazer*: Centro Histórico, Bares da Sé, Altice Fórum, Estádio Municipal
- *Tecnologia*: INL - Nanotecnologia
- *Industrial*: Parque Industrial

Este sistema garante que os pedidos se concentram em zonas realistas (universidades de manhã, bares à noite, hospital 24h, etc.).

#figure(
  image("HotSpots.PNG", width: 60%),
  caption: [Distribuição dos Hotspots na cidade de Braga],
)

=== Falhas de Infraestrutura
As estações de carregamento (EV) e de abastecimento (combustão) podem falhar:
- Probabilidade de Falha: 0.01% por tick de simulação
- Tempo de Recuperação: 120 minutos (2 horas)
- Impacto: Veículos precisam de desviar para estações alternativas, aumentando custos operacionais

#figure(
  image("BombaForaDeServico.PNG", width: 20%),
  caption: [Visualização de uma estação de serviço inoperacional],
)

#pagebreak()
== Agentes (Veículos)
A frota é heterogénea, composta por veículos com atributos distintos. A configuração padrão inclui:

#figure(
  image("Frota.PNG", width: 100%),
  caption: [Gestão da Frota: Monitorização de estatísticas individuais],
)

A frota é heterogénea, composta por veículos com atributos distintos. A tabela detalhada com as especificações técnicas de cada tipo de veículo (Combustão vs. Elétrico) encontra-se no Anexo B.

Os veículos elétricos destacam-se pelo baixo custo operacional (€0.04/km) mas requerem gestão cuidadosa de autonomia.

=== Gestão de Bateria/Combustível
O sistema implementa uma lógica de gestão preventiva:
- Limiar Crítico para Recarga: Quando a autonomia restante \< 50 km, o veículo é automaticamente enviado para uma estação se não tiver nenhum pedido capaz de realizar.
- Penalização na Função de Custo: Quando a autonomia \< 30 km, a função de custo aplica uma penalização quadrática: 
  $P_"bateria" = W_"bateria" times ((30 - "autonomia") / 30)^2$
- Tempo de Recarga:
  - *Veículos a combustão*: Reabastecimento fixo de 5 minutos.
  - *Veículos elétricos*: Recarga proporcional à taxa da estação.

== Características dos Pedidos

Cada pedido de transporte é modelado como um agente com atributos que influenciam a atribuição e o custo.

=== Taxa de Chegada (Processo de Poisson)

A taxa de chegada $lambda(t)$ varia ao longo do dia: $lambda(t) = 0.2 + ("intensidade" times 0.6)$

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

*Nota*: Valores proporcionais à frota simulada (10 veículos). Padrões temporais baseados em dados do setor TVDE#footnote[IMT (2025). Plataforma IMT/Bolt/Uber.].

=== Atributos dos Pedidos <sec:atributos-pedidos>

Cada pedido de transporte tem parâmetros diferentes sendo estes "aleatórios" na sua criação:

#figure(
  table(
    columns: (auto, 2fr),
    align: (left, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Atributo*], [*Descrição*],
    [Prioridade (1-5)], [VIP (5) tem 20% probabilidade em picos, 5% fora; 1-4 uniformes],
    [Preço], [$P = (2.50 + 0.80 times D) times M$, $M=1.3$ se >4 passageiros, caso contratio $M = 1$],
    [Preferência Ecológica], [30% preferem veículos elétricos],
    [Passageiros], [1-4 (90%), 5-7 (10%)],
    [Timeout], [$T_"max" = 30 - 5 times ("Prio" - 1)$ minutos],
  ),
  caption: [Detalhes dos Atributos dos Pedidos de Transporte],
)

= Algoritmos Desenvolvidos

== Subproblema de Procura de Caminho

Considere-se o grafo da cidade de Braga, um nó de origem $o$ (posição atual do veículo) e um nó de destino $d$ (local de recolha do cliente). Este subproblema pode ser formulado do seguinte modo:

*Tipo de problema*: Procura de caminho num grafo com custos não-negativos.

*Estado inicial*: $E_0 = (o)$, posição atual do veículo.

*Operador de mudança de estado*: Seja $n'$ um nó adjacente a $n$. O custo de viajar entre $n$ e $n'$ é dado por:
$ c_(n arrow n') = d(n, n') / v times (1 + m(n, n')) $
onde $d$ calcula a distância (Haversine), $v$ é a velocidade permitida na via, e $m$ é o fator de trânsito.

*Estado final*: $E_f = (d)$, chegada ao destino.

*Custo da solução*: Soma dos tempos de viagem em cada aresta percorrida.

#figure(
  image("AlgoritmoDeAtribuicao.PNG", width: 40%),
  caption: [Seleção do algoritmo de procura de caminho],
)

=== Algoritmos Implementados

Para resolver este subproblema, implementamos três algoritmos:

#figure(
  table(
    columns: (auto, 2fr, auto),
    align: (left, left, center),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Algoritmo*], [*Descrição*], [*Tipo*],
    [BFS], [Explora camada por camada. Garante menor número de "saltos".], [Não Informada],
    [Greedy], [Escolhe sempre o nó com menor heurística $h(n)$.], [Informada],
    [A\*], [Minimiza $f(n) = g(n) + h(n)$. Garante caminho ótimo se $h$ admissível.], [Informada],
  ),
  caption: [Algoritmos de Procura de Caminho Implementados],
)

Heurística utilizada: Tempo de viagem em linha reta à velocidade máxima (120 km/h):
$ h(n) = "Haversine"(n, d) / 2 "km/min" $

Esta heurística é admissível porque nunca sobrestima o custo real — nenhum veículo pode viajar mais rápido que 120 km/h.

=== Comparação dos Algoritmos de Procura

Para comparar o desempenho e a qualidade das soluções, os algoritmos foram testados em 100 rotas aleatórias no grafo de Braga. Os resultados agregados são:

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row == 3 { luma(235) } else { white },
    [*Algoritmo*], [*Σ Tempo (ms)*], [*Σ Custo (min)*], [*Σ Nós Solução*], [*Σ Nós Visitados*],
    [BFS], [609.9], [1482.5], [4632], [454619],
    [Greedy], [37.8], [1637.1], [7612], [16179],
    [A\*], [1631.8], [1078.6], [6478], [327066],
  ),
  caption: [Somas das Métricas de Procura (100 rotas de teste)],
) <tab:search-comparison>

Análise dos Resultados:
- O *A\** encontra o caminho ótimo (menor custo: 1079 min, −27% vs. BFS) mas é o mais lento (1632ms) e visita muitos nós, demonstrando a exploração exaustiva necessária para garantir optimalidade.
- O *BFS* é mais rápido que o A\* mas produz soluções subótimas (+37% custo) porque minimiza arestas, não tempo.
- O *Greedy* é o mais rápido (38ms) com poucos nós visitados, mas produz as piores soluções (+52% custo vs. A\*) porque ignora o custo já percorrido.

== Algoritmos de Atribuição (Assignment)

O problema de atribuir $N$ veículos a $M$ pedidos é combinatório. Implementamos três estratégias:

#figure(
  table(
    columns: (auto, 2fr, 1.5fr),
    align: (left, left, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Algoritmo*], [*Descrição*], [*Limitação*],
    [Greedy], [Faz a combinação mais barata imediata.], [Ótimo local, não global],
    [Hill Climbing], [Tenta trocas a partir de solução inicial. Aceita se melhorar.], [Fica preso em mínimos locais],
    [Simulated Annealing], [Aceita soluções piores com probabilidade $e^(-Delta E / T)$ para escapar mínimos locais.], [Mais lento, requer afinação],
  ),
  caption: [Algoritmos de Atribuição Implementados],
)

=== Simulated Annealing — Parâmetros

O Simulated Annealing foi escolhido como algoritmo principal devido à natureza combinatória do problema:

- *Temperatura Inicial* ($T_0$): 250.0 (aumenta para 450.0 quando há pedidos VIP)
- *Fator de Arrefecimento* ($alpha$): 0.95
- *Critério de Aceitação*: $P("aceitar") = e^(-Delta E / T)$
- *Operadores de Vizinhança*: Assign, Unassign, Swap, Move, Replace

=== Justificação das Escolhas de Design

A escolha do Simulated Annealing como algoritmo principal de atribuição resultou de uma análise cuidadosa das características do problema:

1. Espaço de Estados Discreto e Combinatório: O problema de atribuir $N$ veículos a $M$ pedidos gera um espaço de $(M+1)^N$ estados possíveis (cada veículo pode estar livre ou atribuído a qualquer um dos $M$ pedidos).
   
   Exemplo de cálculo para um caso (10 veículos, 20 pedidos pendentes):
   $ |S| = (20 + 1)^10 = 21^10  approx 1.66 times 10^13 $

      Se um computador avaliasse 1 milhão de estados por segundo, demoraria mais de 500 anos a explorar todas as combinações. Isto torna a procura exaustiva completamente impraticável, justificando o uso de Simulated Annealing.


2.  A função de custo do nosso problema possui múltiplos mínimos locais devido às interações entre restrições (autonomia, capacidade, preferências ecológicas). Algoritmos puramente greedy ou hill climbing ficam facilmente presos nos mínimos locais.

3. Natureza Dinâmica do Problema: Como novos pedidos chegam continuamente e o estado dos veículos muda (bateria, posição), o algoritmo é re-executado frequentemente. O SA adapta-se bem a este contexto porque cada execução parte de uma solução inicial diferente (estado atual), beneficiando da exploração aleatória inicial.

4. Compromisso Tempo-Qualidade: O Simulated Annealing oferece soluções de alta qualidade em tempo previsível. O parâmetro de temperatura dinâmica ($T_0 = 250$ ou $450$ para VIPs) permite ajustar automaticamente a exploração conforme a urgência.

5. Alternativas Consideradas:
   - *Algoritmo Húngaro*: Ótimo mas $O(n^3)$ e não lida bem com restrições complexas (autonomia, preferências).
   - *Programação Linear Inteira*: Garantia de optimalidade mas demasiado lento para decisões em tempo real.

== Otimização da Atribuição de Pedidos

A função `assign_pending_requests` é o componente central do sistema de decisão. O processo implementa várias otimizações para garantir eficiência em tempo real.

=== Pipeline de Atribuição

1. Recolha de Candidatos: Identifica veículos disponíveis e redirecionáveis (já a caminho de um cliente, mas que podem mudar de destino).

2. Construção da Matriz de Custos ($N times M$): Cada célula $C[i,j]$ representa o custo de atribuir o veículo $i$ ao pedido $j$, calculado via `calculate_detailed_cost`.

3. Aplicação de Filtros (Pruning): Atribuições impossíveis recebem custo $infinity$:
   - Capacidade insuficiente para passageiros
   - Autonomia insuficiente para completar a viagem
   - Impossibilidade de chegar a um posto após a entrega

4. Resolução via Meta-Heurística: O Simulated Annealing encontra a configuração que minimiza a energia total.

5. Execução e Reatribuição: Aplica as decisões, libertando veículos de tarefas anteriores se necessário.

=== Otimizações Implementadas

#figure(
  table(
    columns: (auto, 2fr),
    align: (left, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if calc.odd(row) { luma(250) } else { white },
    [*Otimização*], [*Descrição*],
    [Estimativa Heurística], [Na construção da matriz de custos, usamos distância de Haversine em vez de A\* completo. Reduz o tempo de $O(A log V)$ (A = Arestas, V = Vertices) para $O(1)$ por par veículo-pedido. O A\* real é usado apenas na rota final.],
    [Cache de Trânsito], [O `TrafficManager` mantém cache espacial de penalizações de trânsito, limpa a cada tick. Evita recalcular ruído de Perlin para posições próximas.],
    [Cache de Hotspots], [Cada hotspot pré-calcula os nós próximos (`node_cache`) na inicialização. Acelera a seleção de origens/destinos.],
    [Redirecionamento Dinâmico], [Veículos em estado `ON_WAY_TO_CLIENT` são incluídos na reavaliação. Permite trocar atribuições se surgir um pedido mais urgente.],
    [Temperatura Adaptativa], [A temperatura inicial do SA aumenta de 250 para 450 quando há pedidos VIP (prioridade ≥ 4) ou fila de espera saturada.],
    [Bónus de Estabilidade], [Manter a mesma atribuição dá um bónus de −5.0 no custo, evitando oscilações constantes (_jitter_) entre soluções equivalentes.],
  ),
  caption: [Otimizações Implementadas no Sistema de Atribuição],
)

A função de custo utilizada para preencher a matriz é detalhada na @tab:custo-atribuicao.

#figure(
  image("AlgoritmoDeRota.PNG", width: 40%),
  caption: [Seleção do algoritmo de otimização de atribuições],
)

= Reprodutibilidade e Determinismo

A simulação produz resultados idênticos em cada execução, graças ao uso de seeds fixas em todos os processos estocásticos.

== Componentes com Seed Fixa

#figure(
  table(
    columns: (auto, auto, 1.5fr),
    align: (center, center, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Componente*], [*Seed*], [*O que controla*],
    [Gerador de Pedidos], [`12345`], [Intervalos, origens/destinos, prioridades, preferências],
    [Criação da Frota], [`42`], [Posições iniciais dos 10 veículos],
    [Trânsito (Perlin)], [`42`], [Padrões espaciais de congestionamento],
    [Meteorologia (Perlin)], [`42`], [Transições de clima (Sol/Chuva/Tempestade)],
    [Falhas de Estações], [`42`], [Quando e quais estações falham (0.01%/tick)],
  ),
  caption: [Seeds Fixas para Reprodutibilidade],
)

== Processos Estocásticos

*Geração de Pedidos (Processo de Poisson Não-Homogéneo)*:
- A taxa de chegada $lambda(t)$ varia ao longo do dia para simular picos de procura.
- O intervalo até ao próximo pedido é dado por: $Delta t = -ln(U) / lambda(t)$, onde $U in (0, 1]$.
- Isto cria intervalos menores entre pedidos quando $lambda(t)$ é alto (horas de ponta).

*Seleção de Hotspots*:
- Origens e destinos são selecionados com base nos pesos dos hotspots ativos.

*Trânsito e Meteorologia*:
- Ruído de Perlin 3D para variação espacial/temporal do tráfego.
- Ruído de Perlin 1D para transições suaves de clima.

*Falhas de Infraestrutura*:
- Cada estação tem 0.01% de probabilidade de falhar por tick de simulação.


== Exceção

O *Simulated Annealing* usa `random.random()` global — intencional para explorar diferentes caminhos no espaço de soluções, enquanto o workload permanece idêntico.

= Metodologia de Testes e Resultados

== Configuração Experimental

Para avaliar a eficiência dos algoritmos utilizámos um sistema de benchmark automatizado que executa simulações paralelas via `ProcessPoolExecutor`. Cada configuração foi testada durante 28 dias simulados (672 horas) com condições iguais, garantidas pelo uso de seeds fixas.

#figure(
  table(
    columns: (auto, auto),
    align: (left, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Parâmetro*], [*Valor*],
    [Duração Simulada], [672 horas],
    [Frota], [10 veículos (5 EV + 5 combustão)],
    [Total de Pedidos], [≈14 090],
    [Combinações Testadas], [9 (3 routing × 3 assignment)],
    [Tempo Real de Execução], [3 759s (BFS) a 9 114s (A\* + SA)],
  ),
  caption: [Configuração do Ambiente de Benchmark],
)

== Métricas de Avaliação

As métricas recolhidas dividem-se em três categorias, alinhadas com os objetivos do enunciado:

#figure(
  table(
    columns: (auto, 2fr, auto),
    align: (left, left, center),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if calc.odd(row) { luma(250) } else { white },
    [*Categoria*], [*Métrica*], [*Unidade*],
    [Financeira], [Receita Total / Custo Total / Lucro Líquido], [€],
    [Operacional], [Pedidos Completos / Falhados (Taxa de Sucesso)], [contagem / %],
    [Operacional], [Tempo Médio de Espera (resposta ao pedido)], [minutos],
    [Operacional], [Tempo Médio de Viagem], [minutos],
    [Operacional], [Km Totais / Vazios / Ocupados], [km],
    [Operacional], [Taxa de Ocupação (geral, EV, combustão)], [%],
    [Ambiental], [Emissões Totais de CO2], [kg],
    [Ambiental], [Rácio de Km por EVs], [%],
  ),
  caption: [Métricas Recolhidas por Cada Simulação],
)

== Resultados Globais

A tabela seguinte resume os resultados das 9 combinações testadas, ordenadas por algoritmo de routing:

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto, auto, auto),
    align: (left, left, right, right, right, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row >= 7 { luma(235) } else { white },
    [*Routing*], [*Assignment*], [*Lucro (€)*], [*Completos*], [*Taxa (%)*], [*Espera (min)*], [*Km Vazios*], [*CO2 (kg)*],
    [BFS], [Greedy], [76 272], [11 183], [79.4], [15.87], [70 960], [6 600],
    [BFS], [Hill Climbing], [76 305], [11 586], [82.2], [14.01], [69 145], [6 313],
    [BFS], [Sim. Annealing], [76 070], [11 569], [82.1], [14.07], [69 453], [6 314],
    [Greedy], [Greedy], [76 688], [11 197], [79.5], [16.55], [67 254], [6 420],
    [Greedy], [Hill Climbing], [76 415], [11 531], [81.8], [14.68], [64 997], [6 132],
    [Greedy], [Sim. Annealing], [75 566], [11 421], [81.1], [14.50], [64 851], [6 086],
    [A\*], [Greedy], [*79 629*], [11 613], [82.4], [13.22], [66 524], [6 392],
    [A\*], [Hill Climbing], [79 331], [*11 921*], [*84.6*], [11.82], [64 540], [6 121],
    [A\*], [Sim. Annealing], [79 349], [*11 921*], [*84.6*], [*11.72*], [*63 937*], [*6 029*],
  ),
  caption: [Resultados das 9 Combinações de Algoritmos],
) <tab:benchmark-results>

*Legenda*: A coluna Taxa (%) indica a percentagem de pedidos atendidos com sucesso. Os valores destacados (*negrito*) representam os melhores resultados em cada métrica.

== Análise Detalhada

=== Impacto do Algoritmo de Routing

O algoritmo de routing (procura de caminho) tem impacto significativo no desempenho global:

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row == 3 { luma(235) } else { white },
    [*Routing*], [*Receita Média (€)*], [*Custo Médio (€)*], [*Lucro Médio (€)*],
    [BFS], [88 223], [11 997], [76 216],
    [Greedy], [87 644], [11 421], [76 223],
    [A\*], [*90 336*], [*11 094*], [*79 436*],
  ),
  caption: [Métricas Financeiras por Algoritmo de Routing],
)

O A\* supera as alternativas: gera +€2 100/mês de receita face ao BFS enquanto reduz custos operacionais em €900/mês, resultando num lucro 4.2% superior.

=== Impacto do Algoritmo de Atribuição

Para isolar o efeito dos algoritmos de atribuição, fixamos o routing em A\*:

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, right, right, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row == 3 { luma(235) } else { white },
    [*Assignment*], [*Completos*], [*Espera (min)*], [*Km Vazios*], [*CO2 (kg)*], [*Lucro (€)*],
    [Greedy], [11 613], [13.22], [66 524], [6 392], [*79 629*],
    [Hill Climbing], [*11 921*], [11.82], [64 540], [6 121], [79 331],
    [Simulated Annealing], [*11 921*], [*11.72*], [*63 937*], [*6 029*], [79 349],
  ),
  caption: [Comparação dos Algoritmos de Atribuição],
) <tab:assignment-comparison>

*Observações*:
- O Greedy maximiza o lucro (+€280) mas sacrifica a qualidade de serviço: 308 pedidos a menos e 1.5 min de espera adicional
- O Hill Climbing e Simulated Annealing obtêm resultados quase idênticos, sugerindo que a função de custo tem poucos mínimos locais
- O SA tem ligeira vantagem em CO2 (−92 kg) e tempo de espera (−0.1 min)

=== Tempo Médio de Resposta ao Pedido

O tempo de espera mede o intervalo desde a criação do pedido até à chegada do veículo:

#figure(
  image("MetricasDeTempo.PNG", width: 100%),
  caption: [Gráfico de métricas temporais: Espera vs. Viagem],
)

- Pior cenário: Greedy + Greedy → 16.55 min (atribuições imediatas sem otimização)
- Melhor cenário: A\* + SA → 11.72 min (−29%)

=== Taxa de Pedidos Não Atendidos

Um pedido falha quando expira por timeout antes de ser atendido:

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row == 4 { luma(235) } else { white },
    [*Combinação*], [*Completos*], [*Falhados*], [*Taxa Sucesso*],
    [BFS + Greedy], [11 183], [2 907], [79.4%],
    [Greedy + Greedy], [11 197], [2 893], [79.5%],
    [A\* + Greedy], [11 613], [2 477], [82.4%],
    [A\* + SA], [*11 921*], [*2 168*], [*84.6%*],
  ),
  caption: [Taxa de Sucesso (Pedidos Atendidos)],
)

A combinação A\* + SA atende 738 pedidos adicionais (+6.6%) face ao pior cenário.

=== Emissões de CO2

#figure(
  image("ImpactoAmbiental.PNG", width: 80%),
  caption: [Análise do Impacto Ambiental (Emissões CO2)],
)

A combinação A\* + SA emitiu apenas 6 029 kg de CO2 (−571 kg / −8.6% em relação a BFS + Greedy), graças a:
- Maior utilização de EVs (49.3% dos km vs. 47.0%)
- Menos km percorridos em vazio

=== Taxa de Ocupação da Frota

A ocupação mede a proporção de km em que os veículos transportam passageiros:

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row == 4 { luma(235) } else { white },
    [*Combinação*], [*Geral*], [*EV*], [*Combustão*],
    [BFS + Greedy], [50.4%], [49.5%], [51.3%],
    [Greedy + SA], [51.9%], [51.2%], [52.5%],
    [A\* + Greedy], [52.9%], [52.1%], [53.6%],
    [A\* + SA], [*53.3%*], [*52.1%*], [*54.4%*],
  ),
  caption: [Taxa de Ocupação da Frota],
)

Veículos a combustão têm ocupação ligeiramente superior (+2%) devido à maior autonomia.

=== Km Percorridos Sem Passageiros

Os km vazios (deslocações para recolha e desvios a estações) impactam custos e emissões:

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (left, left, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row == 10 { luma(235) } else { white },
    [*Routing*], [*Assignment*], [*Km Total*], [*Km Vazios*], [*Rácio*],
    [BFS], [Greedy], [143 205], [70 960], [49.6%],
    [BFS], [Hill Climbing], [139 900], [69 145], [49.4%],
    [BFS], [Sim. Annealing], [140 017], [69 453], [49.6%],
    [Greedy], [Greedy], [139 610], [67 254], [48.2%],
    [Greedy], [Hill Climbing], [135 637], [64 997], [47.9%],
    [Greedy], [Sim. Annealing], [134 718], [64 851], [48.1%],
    [A\*], [Greedy], [141 138], [66 524], [47.1%],
    [A\*], [Hill Climbing], [137 493], [64 540], [46.9%],
    [A\*], [SA], [136 790], [*63 937*], [*46.7%*],
  ),
  caption: [Km Percorridos Sem Passageiros],
)

O A\* + SA reduziu os km vazios em 7 023 km (−10%) face ao BFS + Greedy.

== Síntese dos Resultados

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, left, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else { white },
    [*Objetivo*], [*Melhor Combinação*], [*Valor*],
    [Maior Lucro], [A\* + Greedy], [€79 629],
    [Menor Tempo de Espera], [A\* + Simulated Annealing], [11.72 min],
    [Menor CO2], [A\* + Simulated Annealing], [6 029 kg],
    [Maior Taxa de Sucesso], [A\* + Simulated Annealing], [84.6%],
    [Menor Km Vazios], [A\* + Simulated Annealing], [63 937 km],
  ),
  caption: [Resumo: Melhor Combinação por Objetivo],
) <tab:winners>

A análise indica que A\* + Simulated Annealing é a estratégia ideal para a TaxiGreen, oferecendo o melhor equilíbrio entre:
1. Qualidade de serviço (−29% tempo de espera)
2. Sustentabilidade ambiental (−8.6% CO2)
3. Eficiência operacional (−10% km vazios)
4. Viabilidade financeira (99.6% do lucro máximo)

Esta solução demonstra que é possível ser sustentável sem comprometer a rentabilidade.

#pagebreak()
= Correspondência com as Tarefas Pedidas

Esta secção mapeia cada tarefa solicitada no enunciado à nossa implementação:

// ATUALIZAR DADOS
#figure(
  table(
    columns: (auto, 1fr),
    align: (center, left),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0  { luma(230) } else if calc.odd(row) { luma(250) } else { white },
    
    [*Tarefa*], [*Implementação*],
    
    [Formular o problema\ como procura], 
    [✓ Definido como Otimização Combinatória Dinâmica com estado $S_t = (A, B, V)$, operadores (Assign, Swap, Move, etc.), e função de energia],
    
    [Representar cidade\ como grafo],
    [✓ Grafo real de Braga via OSMnx, nós=intersecções, arestas=estradas com distâncias Haversine],
    
    [Desenvolver estratégias\ informadas e não\ informadas],
    [✓ Implementados BFS (não informada), Greedy, A\* (informadas).],
    
    [Implementar sistema\ de simulação dinâmica],
    [✓ Simulador com chegadas de pedidos via Processo de Poisson, trânsito dinâmico (Perlin + Gaussianas), meteorologia, falhas de infraestrutura],
    
    [Avaliar eficiência\ com métricas],
    [✓ Benchmark com 9 combinações de algoritmos, métricas: Lucro, Taxa de Ocupação, Tempo de Espera, km Vazios, CO2],
    
    [Simular condições\ dinâmicas],
    [✓ Trânsito variável (picos de hora), meteorologia (Sol/Nevoeiro/Chuva/Tempestade), falhas de estações],
  ),
  caption: [Correspondência Tarefa-Implementação],
)

// ATUALIZAR DADOS
== Funcionalidades Extra Implementadas
Além dos requisitos base, implementámos:

1. Hotspots Geográficos: Sistema de zonas de alta densidade com horários de funcionamento e peso na criação de pedidos.

2. Gestão Preventiva de Bateria: Penalização quadrática para baixa autonomia.

3. Sistema de Prioridade Escalonado: Timeouts diferentes por prioridade.

4. Trânsito e meteorologia Dinâmica: Curvas Gaussianas e Ruído de Perlin.

5. Benchmark Automatizado: Sistema de testes concorrentes (`ProcessPoolExecutor`) para comparar 9 configurações de algoritmos em 28 dias simulados.

6. Reprodutibilidade: Seeds fixas garantem que benchmarks são justos e replicáveis.

= Conclusão e Reflexão

O projeto atingiu o objetivo principal de desenvolver um sistema inteligente de gestão de frota para a TaxiGreen, capaz de operar num ambiente urbano dinâmico e complexo. A solução implementada equilibra eficazmente os custos operacionais, a satisfação do cliente (tempo de espera) e a sustentabilidade ambiental, respondendo aos desafios da mobilidade moderna.

Os resultados do benchmark demonstraram que a combinação de A\* (para navegação) e Simulated Annealing (para atribuição) superou as outras abordagens. O A\* garantiu rotas ótimas que reduziram os quilómetros percorridos em vazio, enquanto o Simulated Annealing permitiu uma gestão global da frota, evitando mínimos locais e priorizando veículos elétricos sempre que viável, resultando numa redução de 8.6% nas emissões de CO2.

== Resposta aos Desafios do Enunciado
O sistema lidou com sucesso com as restrições impostas:
- Gestão de Frota Mista: A lógica de custo penalizou o uso de veículos a combustão para pedidos "eco" e garantiu que os EVs fossem carregados preventivamente.
- Dinamismo: O planeamento contínuo permitiu reagir a novos pedidos, trânsito variável e falhas de infraestrutura em tempo real.
- Equilíbrio de Objetivos: A função de custo multiobjetivo permitiu afinar o peso do lucro vs. serviço ao cliente.

#pagebreak()
= Apresentação da Interface

A aplicação desenvolvida disponibiliza uma interface gráfica que permite visualizar e controlar a simulação em tempo real.

#figure(
  image("gui.PNG", width: 110%),
  caption: [Visualização do mapa com veículos e pedidos em tempo real e Painel lateral com métricas de desempenho (lucro, CO2, tempos de espera)],
)

A interface permite:
- *Zoom e Navegação*: Scroll para zoom, arrastar para mover o mapa
- *Visualização de Trânsito*: Arestas coloridas (verde→vermelho) indicam congestionamento
- *Hotspots*: Círculos verdes/vermelhos mostram zonas de alta procura ativas/inativas
- *Estados dos Veículos*: Ícones diferentes para EVs e veículos a combustão
- *Métricas*: Painel para observar valores da simulação
- *Configuração*: Painel para alterar algoritmos de routing/assignment em tempo real

= Referências

#set enum(numbering: "[1]")

+ Russell, S., & Norvig, P. (2021). _Artificial Intelligence: A Modern Approach_ (4th ed.). Pearson. <russell2021>

+ Boeing, G. (2017). "OSMnx: New Methods for Acquiring, Constructing, Analyzing, and Visualizing Complex Street Networks". _Computers, Environment and Urban Systems_, 65, 126-139.

+ Instituto da Mobilidade e dos Transportes (2025). _Estatísticas TVDE Portugal_. Plataforma IMT.

+ Associação Automóvel de Portugal (2024). _Emissões médias de CO2 em Portugal_. Revista ACP.

#heading(numbering: none)[Anexos]

== Anexo A: Galeria da Interface

Nesta secção apresentamos capturas de ecrã adicionais que ilustram a interface gráfica desenvolvida para monitorização e controlo da simulação.

=== Controlos e Ambiente

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  figure(image("Controlos.PNG"), caption: [Painel de Controlo da Simulação]),
  figure(image("Dia.PNG"), caption: [Ciclo Dia/Noite na Interface]),
  figure(
  image("Simulacao.PNG", width: 80%),
  caption: [Painel de Controlos dos algoritmos, velocidade de simulação e benchmark],
)

)

=== Gestão de Pedidos

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  figure(image("Pedidos.PNG", width: 120%), caption: [Lista de Pedidos Ativos]),
  figure(image("Destino.PNG"), caption: [Visualização de Destino no Mapa]),
)

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  figure(image("PedidoPorAceitar.PNG", width: 40%), caption: [Pedido Pendente (Azul)]),
  figure(image("PedidoAceite.PNG", width: 40%), caption: [Pedido Atribuído (Verde)]),
)

=== Infraestrutura e Veículos

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  figure(image("BombaCombustao.PNG"), caption: [Posto de Abastecimento]),
  figure(image("BombaEletrica.PNG"), caption: [Posto de Carregamento EV]),
)

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  figure(image("GazolinaEEletrico.PNG", width: 40%), caption: [Posto de Abastecimento e Carregamento EV]),
)

=== Visualização de Dados

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  figure(image("Otimizacao.PNG", width: 80%), caption: [Visualização do Processo de Otimização]),
  figure(image("Metricas.PNG", width: 90%), caption: [Painel de Métricas em Tempo Real]),
)

#grid(
  columns: (1fr, 1fr),
  gutter: 1em,
  figure(image("HotSpotAtivo.PNG", width: 90%), caption: [Hotspot Ativo (Alta Procura)]),
  figure(image("HotSpotInativo.PNG", width: 90%), caption: [Hotspot Inativo]),
)

== Anexo B: Especificações da Frota

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
  caption: [Comparação detalhada entre Tipos de Veículos],
)

== Anexo C: Dados Completos de Benchmark

Esta secção apresenta todos os dados recolhidos durante os testes de benchmark (28 dias simulados, 672 horas). Os valores foram extraídos diretamente dos ficheiros JSON gerados pelo sistema.

=== Métricas Financeiras

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, left, right, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row >= 7 { luma(235) } else { white },
    [*Routing*], [*Assignment*], [*Receita (€)*], [*Custo (€)*], [*Lucro (€)*], [*Tempo De \ Simulação*],
    [BFS], [Greedy], [88 538], [12 266], [76 272], [3 759],
    [BFS], [Hill Climbing], [88 159], [11 854], [76 305], [3 762],
    [BFS], [Sim. Annealing], [87 934], [11 864], [76 070], [3 859],
    [Greedy], [Greedy], [88 632], [11 944], [76 688], [1 248],
    [Greedy], [Hill Climbing], [87 922], [11 507], [76 415], [1 275],
    [Greedy], [Sim. Annealing], [86 986], [11 420], [75 566], [1 337],
    [A\*], [Greedy], [*91 565*], [11 936], [*79 629*], [9 153],
    [A\*], [Hill Climbing], [90 854], [11 523], [79 331], [9 022],
    [A\*], [Sim. Annealing], [90 753], [*11 404*], [79 349], [9 114],
  ),
  caption: [Benchmark — Métricas Financeiras Completas],
)

=== Métricas Operacionais

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto), // Reduzido para 6 colunas
    align: (left, left, right, right, center, right), 
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row >= 7 { luma(235) } else { white },
    [*Routing*], [*Assignment*], [*Finalizados*], [*Falhados*], [*Espera \ Média*], [*Tempo de \ Viagem*],
    
    [BFS], [Greedy], [11 183], [2 907], [15.87], [26.78],
    [BFS], [Hill Climbing], [11 586], [2 504], [14.01], [24.45],
    [BFS], [Sim. Annealing], [11 569], [2 521], [14.07], [24.51],
    [Greedy], [Greedy], [11 197], [2 893], [16.55], [27.46],
    [Greedy], [Hill Climbing], [11 531], [2 559], [14.68], [25.15],
    [Greedy], [Sim. Annealing], [11 421], [2 668], [14.50], [24.94],
    [A\*], [Greedy], [11 613], [2 477], [13.22], [24.14],
    [A\*], [Hill Climbing], [*11 921*], [2 169], [11.82], [22.32],
    [A\*], [Sim. Annealing], [*11 921*], [*2 168*], [*11.72*], [*22.21*],
  ),
  caption: [Benchmark — Métricas Operacionais Completas],
)

=== Métricas de Quilometragem

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, left, right, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row >= 7 { luma(235) } else { white },
    [*Routing*], [*Assignment*], [*Km Total*], [*Km Vazios*], [*Km Ocupados*], [*Ocupação (%)*],
    [BFS], [Greedy], [143 205], [70 960], [72 244], [50.4],
    [BFS], [Hill Climbing], [139 900], [69 145], [70 755], [50.6],
    [BFS], [Sim. Annealing], [140 017], [69 453], [70 564], [50.4],
    [Greedy], [Greedy], [139 610], [67 254], [72 356], [51.8],
    [Greedy], [Hill Climbing], [135 637], [64 997], [70 640], [52.1],
    [Greedy], [Sim. Annealing], [134 718], [64 851], [69 867], [51.9],
    [A\*], [Greedy], [141 138], [66 524], [*74 614*], [52.9],
    [A\*], [Hill Climbing], [137 493], [64 540], [72 952], [53.1],
    [A\*], [Sim. Annealing], [136 790], [*63 937*], [72 853], [*53.3*],
  ),
  caption: [Benchmark — Métricas de Quilometragem Completas],
)

=== Métricas Ambientais e de Frota

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, left, right, right, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row >= 7 { luma(235) } else { white },
    [*Routing*], [*Assignment*], [*CO2 (kg)*], [*EV Ratio (%)*], [*Ocupação EV (%)*], [*Ocupação Gas (%)*],
    [BFS], [Greedy], [6 600], [47.0], [49.5], [51.3],
    [BFS], [Hill Climbing], [6 313], [48.1], [49.5], [51.6],
    [BFS], [Sim. Annealing], [6 314], [48.2], [49.4], [51.3],
    [Greedy], [Greedy], [6 420], [47.1], [50.9], [52.7],
    [Greedy], [Hill Climbing], [6 132], [48.0], [51.1], [52.9],
    [Greedy], [Sim. Annealing], [6 086], [48.1], [51.2], [52.5],
    [A\*], [Greedy], [6 392], [47.9], [*52.1*], [53.6],
    [A\*], [Hill Climbing], [6 121], [48.8], [52.0], [54.1],
    [A\*], [Sim. Annealing], [*6 029*], [*49.3*], [*52.1*], [*54.4*],
  ),
  caption: [Benchmark — Métricas Ambientais e de Frota],
)

=== Tempo em Estações de Recarga

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, left, right, right),
    stroke: 0.5pt + gray,
    fill: (row, col) => if row == 0 { luma(230) } else if row >= 7 { luma(235) } else { white },
    [*Routing*], [*Assignment*], [*Tempo EV (min)*], [*Tempo Gas (min)*],
    [BFS], [Greedy], [41 361], [550],
    [BFS], [Hill Climbing], [39 198], [525],
    [BFS], [Sim. Annealing], [39 828], [525],
    [Greedy], [Greedy], [38 170], [535],
    [Greedy], [Hill Climbing], [*36 512*], [510],
    [Greedy], [Sim. Annealing], [37 486], [*505*],
    [A\*], [Greedy], [39 820], [535],
    [A\*], [Hill Climbing], [38 598], [515],
    [A\*], [Sim. Annealing], [37 604], [510],
  ),
  caption: [Benchmark — Tempo Total em Estações de Recarga/Abastecimento],
)

*Nota*: Os dados foram recolhidos com seeds fixas para garantir reprodutibilidade. Os ficheiros JSON originais encontram-se na pasta `benchmark_results/` do projeto.