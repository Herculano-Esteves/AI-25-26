from typing import List, Tuple
from models.node import Node
from graph import CityGraph
from Simulation.search_algorithms import haversine_km, _heuristic_distance


class Hotspot:
    """Zona de alta procura com horários de actividade."""

    def __init__(self, name: str, coords: Tuple[float, float], hours: List[Tuple[int, int]],
                 weight: float = 1.0, radius_km: float = 0.5):
        self.name = name
        self.coordinates = coords  # (lon, lat)
        self.active_hours = hours  # [(start, end), ...]
        self.weight = weight
        self.radius_km = radius_km
        self.is_active = False
        self.node_cache: List[Node] = []

    def check_active(self, hour: int) -> bool:
        """Verifica se está activo à hora indicada."""
        self.is_active = any(start <= hour < end for start, end in self.active_hours)
        return self.is_active


class HotspotManager:
    """Gere hotspots de Braga e associa-os a nós do grafo."""

    def __init__(self, city_map: CityGraph):
        self.city_map = city_map
        self.hotspots: List[Hotspot] = []
        self._init_hotspots()
        self._map_to_nodes()

    def _init_hotspots(self):
        """Hotspots de Braga com coordenadas, horários e pesos."""
        data = [
            
            # Universidades e escolas
            ("Universidade do Minho", (-8.398417, 41.559389), [(7, 10), (12, 14), (16, 19)], 2.0, 0.5),
            ("INL - Nanotecnologia", (-8.399337, 41.554724), [(7, 10), (16, 19)], 1.4, 0.4),
            ("Escola Sá de Miranda", (-8.413700, 41.552900), [(7, 9), (12, 14), (16, 18)], 1.1, 0.3),
            ("Colégio D. Diogo de Sousa", (-8.4162467, 41.5574328), [(7, 9), (12, 14), (16, 18)], 1.0, 0.35),
            ("Escola André Soares", (-8.416732, 41.547369), [(7, 9), (12, 14), (16, 18)], 1.0, 0.3),
            ("Escola Alberto Sampaio", (-8.413744, 41.542797), [(7, 9), (12, 14), (16, 18)], 1.0, 0.35),
            ("Escola Lamaçães", (-8.402400, 41.546947), [(7, 9), (12, 14), (16, 18)], 0.9, 0.3),
            
            # Comércio e lazer
            ("Braga Parque", (-8.406206, 41.558494), [(11, 15), (17, 22)], 2.2, 0.5),
            ("Nova Arcada", (-8.502800, 41.569800), [(11, 15), (17, 21)], 1.8, 0.8),
            ("Minho Center", (-8.40022, 41.54089), [(12, 15), (17, 21)], 1.3, 0.4),
            ("Avenida da Liberdade", (-8.413000, 41.553500), [(8, 20)], 1.2, 0.5),
            
            # Centro e vida nocturna
            ("Centro Histórico", (-8.423580, 41.551470), [(11, 15), (18, 2)], 2.0, 0.6),
            ("Bares da Sé", (-8.425326, 41.550683), [(20, 4)], 2.3, 0.4),
            
            # Eventos e transportes
            ("Altice Fórum Braga", (-8.422736, 41.540989), [(18, 23)], 3.0, 0.6),
            ("Estádio Municipal", (-8.433000, 41.566200), [(18, 23)], 3.5, 0.7),
            ("Estação CP", (-8.434821, 41.547321), [(6, 9), (16, 20), (21, 23)], 1.6, 0.5),
            
            # Saúde e indústria
            ("Hospital de Braga", (-8.400000, 41.566667), [(0, 24)], 1.9, 0.6),
            ("Parque Industrial", (-8.450500, 41.521000), [(6, 9), (16, 19)], 1.6, 0.8),
        ]

        for name, coords, hours, weight, radius in data:
            self.hotspots.append(Hotspot(name, coords, hours, weight, radius))

    def _map_to_nodes(self):
        """Associa nós do grafo a cada hotspot (por distância real em km)."""
        all_nodes = list(self.city_map.nos)
        print("[Hotspots] A mapear zonas aos nós...")

        for h in self.hotspots:
            nearby = []
            for node in all_nodes:
                dist = haversine_km(node.position[0], node.position[1],
                                   h.coordinates[0], h.coordinates[1])
                if dist <= h.radius_km:
                    nearby.append(node)

            # Fallback: se mapa esparso, usa os 3 mais próximos
            if not nearby:
                dummy = Node(h.coordinates)
                nearby = sorted(all_nodes, key=lambda n: _heuristic_distance(n, dummy))[:3]

            h.node_cache = nearby
            print(f"  {h.name}: {len(nearby)} nós")

    def update(self, hour: int):
        """Actualiza estado de todos os hotspots."""
        for h in self.hotspots:
            h.check_active(hour)

    def get_active_hotspots(self) -> List[Hotspot]:
        return [h for h in self.hotspots if h.is_active]
