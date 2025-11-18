from typing import Tuple, Set, Dict, List, Optional
from models.node import Node

# (Distance Km, Time minutes, Max Speed km/h)
TipoAresta = Tuple[float, float, float]


class CityGraph:

    def __init__(self):
        self.nos: Set[Node] = set()
        self.adj: Dict[Node, Dict[Node, TipoAresta]] = {}
        self.position_to_node: Dict[Tuple[float, float], Node] = {}

        self.gas_stations: List[Node] = []
        self.ev_stations: List[Node] = []

    def add_node(self, no: Node):
        # If it already exists it will replace
        if no not in self.nos:
            self.nos.add(no)
            self.adj[no] = {}
            self.position_to_node[no.position] = no

            # Add to station list
            if no.gas_pumps > 0:
                self.gas_stations.append(no)
            if no.energy_chargers > 0:
                self.ev_stations.append(no)

    def node_exists(self, no: Node) -> bool:
        return no in self.nos

    def get_node_by_position(self, position: Tuple[float, float]) -> Optional[Node]:
        return self.position_to_node.get(position)

    def add_connection(
        self,
        start_node: Node,
        end_node: Node,
        distance_km: float,
        time: float,  # Minutes
        max_speed: float,
        bidirecional: bool = True,
    ):
        self.add_node(start_node)
        self.add_node(end_node)

        self.adj[start_node][end_node] = (distance_km, time, max_speed)

        if bidirecional:
            self.adj[end_node][start_node] = (distance_km, time, max_speed)

    def get_node_neighbours(self, no: Node) -> List[Node]:
        if no not in self.adj:
            return []
        return list(self.adj[no].keys())

    def connection_weight(self, start_node: Node, end_node: Node) -> Optional[TipoAresta]:
        if start_node in self.adj and end_node in self.adj[start_node]:
            return self.adj[start_node][end_node]
        return None

    def __str__(self) -> str:
        output = "Grafo da Cidade:\n"
        output += f"Total de Nós: {len(self.nos)}\n"
        output += "--- Arestas\n"

        if not self.adj:
            return output + "(Grafo vazio)"

        for no, vizinhos in self.adj.items():
            output += f"  {no}:\n"
            if not vizinhos:
                output += "    -> (Nenhum vizinho)\n"
            for vizinho, peso in vizinhos.items():
                dist, tempo, max_speed = peso
                output += f"    -> {vizinho} | (Dist: {dist} km, Tempo: {tempo} min, Velocidade maxima: {max_speed} km/h)\n"
        return output
