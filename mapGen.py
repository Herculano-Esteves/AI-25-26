import networkx as nx
import random
from graph import GrafoCidade
from nodo import Node
from models import Veiculo, Pedido, Motorizacao
from typing import Tuple, List

def criar_mapa_gerado(
    largura=10, altura=10, prob_posto_gas=0.1, prob_estacao_ev=0.1
) -> Tuple[GrafoCidade, List[Veiculo], List[Pedido]]:
    mapa = GrafoCidade()
    nos_criados = {}

    # Create nodes
    for x in range(largura):
        for y in range(altura):
            gas_pumps = 0
            energy_chargers = 0

            if random.random() < prob_posto_gas:
                gas_pumps = random.randint(2, 6)

            if random.random() < prob_estacao_ev:
                energy_chargers = random.randint(2, 6)

            pos = (x, y)
            no = Node(pos, gas_pumps, energy_chargers, random.randint(200, 900))
            nos_criados[pos] = no
            mapa.adicionar_no(no)

    # Creates streets
    G_grid = nx.grid_2d_graph(largura, altura)

    for u_pos, v_pos in G_grid.edges():
        no_origem = nos_criados[u_pos]
        no_destino = nos_criados[v_pos]

        distancia = 1.0
        tempo = random.uniform(1.5, 3.0)

        mapa.adicionar_aresta(no_origem, no_destino, distancia, tempo, True)

    todos_os_nos = list(nos_criados.values())
    garantir_ponto_interesse(todos_os_nos, Motorizacao.ELETRICO)
    garantir_ponto_interesse(todos_os_nos, Motorizacao.COMBUSTAO)

    veiculos = []
    # Generates eletric vehicles
    for i in range(3):
        loc = random.choice(todos_os_nos)
        veiculos.append(
            Veiculo(
                f"V-EV{i+1}",
                Motorizacao.ELETRICO,
                loc,
                random.randint(3, 7),
                0.035,
                random.randint(350, 650),
                random.randint(50, 650),
            )
        )

    # Generates combustion vehicles
    for i in range(3):
        loc = random.choice(todos_os_nos)
        veiculos.append(
            Veiculo(
                f"V-GAS{i+1}",
                Motorizacao.COMBUSTAO,
                loc,
                random.randint(3, 7),
                0.098,
                random.randint(600, 900),
                random.randint(50, 900),
            )
        )

    # Generates random requests
    pedidos = []
    for i in range(5):
        pedidos.append(criar_pedido_aleatorio(todos_os_nos))

    print(
        f"Mapa gerado: {largura}x{altura} ({len(todos_os_nos)} nós). {len(veiculos)} veículos e {len(pedidos)} pedidos criados."
    )
    return mapa, veiculos, pedidos

def garantir_ponto_interesse(todos_os_nos, tipo_ponto):
    if tipo_ponto == Motorizacao.ELETRICO:
        if any(n.energy_chargers > 0 for n in todos_os_nos):
            return
        # Converte um nó aleatório
        no_a_converter = random.choice(todos_os_nos)
        no_a_converter.energy_chargers = random.randint(2, 4)

    elif tipo_ponto == Motorizacao.COMBUSTAO:
        if any(n.gas_pumps > 0 for n in todos_os_nos):
            return
        # Converte um nó aleatório
        no_a_converter = random.choice(todos_os_nos)
        no_a_converter.gas_pumps = random.randint(2, 4)

def criar_pedido_aleatorio(nos: List[Node]) -> Pedido:
    origem = random.choice(nos)
    destino = random.choice(nos)
    while origem == destino:
        destino = random.choice(nos)
    return Pedido(origem, destino, random.randint(1, 7))
