from typing import List, Tuple, Optional
from models.node import Node
from graph import CityGraph
from search import haversine_km, _heuristic_distance
import random


class Hotspot:
    def __init__(
        self,
        name: str,
        coordinates: Tuple[float, float],
        active_hours: List[Tuple[int, int]],
        weight: float = 1.0,
        radius_km: float = 0.5,
    ):
        """
        :param coordinates: (Longitude, Latitude) - X, Y
        :param active_hours: Lista de tuplos [(start_hour, end_hour), ...]
        :param weight: Probabilidade relativa deste hotspot ser escolhido
        :param radius_km: Radius of influence in Kilometers
        """
        self.name = name
        self.coordinates = coordinates  # (lon, lat)
        self.active_hours = active_hours
        self.weight = weight
        self.radius_km = radius_km
        self.is_active = False
        self.node_cache: List[Node] = []

    def check_active(self, current_hour: int) -> bool:
        """Checks if the hotspot is on."""
        self.is_active = False
        for start, end in self.active_hours:
            if start <= current_hour < end:
                self.is_active = True
                break
        return self.is_active


class HotspotManager:
    def __init__(self, city_map: CityGraph):
        self.city_map = city_map
        self.hotspots: List[Hotspot] = []
        self._initialize_braga_hotspots()
        self._map_hotspots_to_nodes()

    def _initialize_braga_hotspots(self):

        hotspots_list = [
            Hotspot(
                "Universidade do Minho",
                (-8.398417, 41.559389),
                [(7, 10), (12, 14), (16, 19)],
                weight=2.0,
                radius_km=0.5,
            ),
            Hotspot(
                "Braga Parque",
                (-8.406206, 41.558494),
                [(11, 15), (17, 22)],
                weight=2.2,
                radius_km=0.5,
            ),
            Hotspot(
                "Altice Fórum Braga",
                (-8.422736, 41.540989),
                [(18, 23)],
                weight=3.0,
                radius_km=0.6,
            ),
            Hotspot(
                "Hospital de Braga",
                (-8.400000, 41.566667),
                [(0, 24)],
                weight=1.9,
                radius_km=0.6,
            ),
            Hotspot(
                "Estação CP",
                (-8.434821, 41.547321),
                [(6, 9), (16, 20), (21, 23)],
                weight=1.6,
                radius_km=0.5,
            ),
            Hotspot(
                "Centro Histórico",
                (-8.423580, 41.551470),
                [(11, 15), (18, 2)],
                weight=2.0,
                radius_km=0.6,
            ),
            Hotspot(
                "Bares da Sé",
                (-8.425326, 41.550683),
                [(20, 4)],
                weight=2.3,
                radius_km=0.4,
            ),
            Hotspot(
                "Minho Center",
                (-8.40022, 41.54089),
                [(12, 15), (17, 21)],
                weight=1.3,
                radius_km=0.4,
            ),
            Hotspot(
                "Nova Arcada",
                (-8.502800, 41.569800),
                [(11, 15), (17, 21)],
                weight=1.8,
                radius_km=0.8,
            ),
            Hotspot(
                "INL - Nanotecnologia",
                (-8.399337, 41.554724),
                [(7, 10), (16, 19)],
                weight=1.4,
                radius_km=0.4,
            ),
            Hotspot(
                "Parque Industrial",
                (-8.450500, 41.521000),
                [(6, 9), (16, 19)],
                weight=1.6,
                radius_km=0.8,
            ),
            Hotspot(
                "Estádio Municipal",
                (-8.433000, 41.566200),
                [(18, 23)],
                weight=3.5,
                radius_km=0.7,
            ),
            Hotspot(
                "Avenida da Liberdade",
                (-8.413000, 41.553500),
                [(8, 20)],
                weight=1.2,
                radius_km=0.5,
            ),
            Hotspot(
                "Escola Sá de Miranda",
                (-8.413700, 41.552900),
                [(7, 9), (12, 14), (16, 18)],
                weight=1.1,
                radius_km=0.3,
            ),
            Hotspot(
                "Colégio D. Diogo de Sousa",
                (-8.4162467, 41.5574328),
                [(7, 9), (12, 14), (16, 18)],
                weight=1.0,
                radius_km=0.35,
            ),
            Hotspot(
                "Escola André Soares",
                (-8.416732, 41.547369),
                [(7, 9), (12, 14), (16, 18)],
                weight=1.0,
                radius_km=0.3,
            ),
            Hotspot(
                "Escola Sec. Alberto Sampaio",
                (-8.413744, 41.542797),
                [(7, 9), (12, 14), (16, 18)],
                weight=1.0,
                radius_km=0.35,
            ),
            Hotspot(
                "Escola Lamaçães",
                (-8.402400, 41.546947),
                [(7, 9), (12, 14), (16, 18)],
                weight=0.9,
                radius_km=0.3,
            ),
        ]

        self.hotspots.extend(hotspots_list)

    def _map_hotspots_to_nodes(self):
        """
        Associa nós do grafo real aos hotspots num raio fisico (km).
        """
        all_nodes = list(self.city_map.nos)

        print("[Hotspots] A mapear zonas de calor aos nós do grafo (Distância Real)...")

        for hotspot in self.hotspots:
            nearby_nodes = []

            for node in all_nodes:
                # haversine_km expects
                dist_km = haversine_km(
                    node.position[0],
                    node.position[1],
                    hotspot.coordinates[0],
                    hotspot.coordinates[1],
                )

                if dist_km <= hotspot.radius_km:
                    nearby_nodes.append(node)

            # Fallback: If no nodes found in radius (sparse map), pick closest 3 regardless of radius
            if not nearby_nodes:
                dummy_center = Node(hotspot.coordinates)
                nearby_nodes = sorted(
                    all_nodes, key=lambda n: _heuristic_distance(n, dummy_center)
                )[:3]

            hotspot.node_cache = nearby_nodes
            print(
                f"  -> {hotspot.name} (R={hotspot.radius_km}km): {len(nearby_nodes)} nós associados."
            )

    def update(self, current_hour: int):
        """Atualiza o estado ativo/inativo baseada na hora."""
        for h in self.hotspots:
            h.check_active(current_hour)

    def get_active_hotspots(self) -> List[Hotspot]:
        return [h for h in self.hotspots if h.is_active]

    def get_random_node_from_active_hotspots(self) -> Optional[Node]:
        """
        Retorna um nó aleatório de um hotspot ativo (ponderado pelo weight).
        Retorna None se nenhum estiver ativo.
        """
        active = self.get_active_hotspots()
        if not active:
            return None

        # Escolha ponderada (ex: Centro tem mais peso que estação)
        weights = [h.weight for h in active]
        chosen_hotspot = random.choices(active, weights=weights, k=1)[0]

        if chosen_hotspot.node_cache:
            return random.choice(chosen_hotspot.node_cache)
        return None
