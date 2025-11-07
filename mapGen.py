import networkx as nx
import random
from graph import CityGraph
from models import Node, Vehicle, Request, Motor
from typing import Tuple, List


def generate_map(
    width=10, height=10, gas_probability=0.1, ev_probability=0.1
) -> CityGraph:
    map = CityGraph()
    created_nodes = {}
    all_nodes = list()

    # Create nodes
    for x in range(width):
        for y in range(height):
            gas_pumps = 0
            energy_chargers = 0

            if random.random() < gas_probability:
                gas_pumps = random.randint(2, 6)

            if random.random() < ev_probability:
                energy_chargers = random.randint(2, 6)

            pos = (x, y)
            no = Node(pos, gas_pumps, energy_chargers, random.randint(200, 900))
            created_nodes[pos] = no
            map.add_node(no)

    # Creates streets
    G_grid = nx.grid_2d_graph(width, height)

    for u_pos, v_pos in G_grid.edges():
        no_origem = created_nodes[u_pos]
        no_destino = created_nodes[v_pos]

        distancia = 1.0
        tempo = random.uniform(1.5, 3.0)

        map.add_connection(no_origem, no_destino, distancia, tempo, True)

    all_nodes = list(created_nodes.values())
    gas_ev_station_grant_existance(all_nodes)

    print(f"Mapa gerado: {width}x{height} ({len(all_nodes)} nós).")
    return map


def _create_vehicle(
    id_prefix: str,
    motor: Motor,
    loc: Node,
    cost_per_km: float,
    range: int,
    max_range: int,
) -> Vehicle:
    return Vehicle(
        f"V-{id_prefix}",
        motor,
        loc,
        random.randint(3, 7),
        cost_per_km,
        random.randint(range, max_range),
        random.randint(50, range),
    )


def create_vehicle_fleet(
    all_nodes: List[Node], num_ev: int, num_gas: int
) -> List[Vehicle]:
    veiculos = []

    # Generates eletric vehicles
    for i in range(num_ev):
        loc = random.choice(all_nodes)
        veiculos.append(
            _create_vehicle(f"EV{i+1}", Motor.ELECTRIC, loc, 0.035, 50, 650)
        )

    # Generates combustion vehicles
    for i in range(num_gas):
        loc = random.choice(all_nodes)
        veiculos.append(
            _create_vehicle(f"GAS{i+1}", Motor.COMBUSTION, loc, 0.098, 50, 900)
        )

    print(f"Frota gerada: {len(veiculos)} veículos criados.")
    return veiculos


def generate_requests(all_nodes: List[Node], num_requests: int) -> List[Request]:
    requests = []
    for _ in range(num_requests):
        requests.append(generate_random_request(all_nodes))
    print(f"Pedidos gerados: {len(requests)} requests iniciais criados.")
    return requests


def gas_ev_station_grant_existance(all_nodes):
    if not any(n.energy_chargers > 0 for n in all_nodes):
        no_a_converter = random.choice(all_nodes)
        no_a_converter.energy_chargers = random.randint(2, 4)

    if not any(n.gas_pumps > 0 for n in all_nodes):
        no_a_converter = random.choice(all_nodes)
        no_a_converter.gas_pumps = random.randint(2, 4)


def generate_random_request(nos: List[Node]) -> Request:
    start_node = random.choice(nos)
    end_node = random.choice(nos)
    while start_node == end_node:
        end_node = random.choice(nos)
    return Request(
        start_node=start_node,
        end_node=end_node,
        passenger_capacity=random.randint(1, 7),
        environmental_preference=True if random.randint(1,4) == 1 else False,
    )
