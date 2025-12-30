import random
import math
from typing import List, Optional, TYPE_CHECKING
from models.request import Request
from Simulation.search_algorithms import find_route

if TYPE_CHECKING:
    from graph import CityGraph
    from models.node import Node
    from Simulation.hotspots import HotspotManager


class RequestGenerator:
    """Gera pedidos deterministicamente baseado em hotspots e hora do dia."""

    BASE_FARE = 2.50
    PRICE_PER_KM = 0.80

    def __init__(self, city_map: "CityGraph", hotspot_manager: "HotspotManager", seed: int = 42):
        self.city_map = city_map
        self.hotspot_manager = hotspot_manager
        self.rng = random.Random(seed)
        self.next_request_time = -1.0
        self.base_demand = 0.2
        self.peak_multiplier = 0.6

    def reset(self):
        self.next_request_time = -1.0
        self.rng = random.Random(42)

    def update(self, current_time: float, requests_list: List[Request]) -> bool:
        """Verifica se deve criar pedido. Retorna True se criou."""
        if self.next_request_time < 0:
            self.next_request_time = current_time + 0.1
            return False

        created = False
        while current_time >= self.next_request_time:
            req = self._create_request(self.next_request_time)
            if req:
                requests_list.append(req)
                created = True
                hour = (self.next_request_time / 60.0) % 24
                print(f"[Pedido] #{req.id} às {hour:.1f}h (Prio {req.priority}) - €{req.price:.2f}")
            self._schedule_next(self.next_request_time)

        return created

    def _schedule_next(self, last_time: float):
        """Calcula próximo pedido com distribuição exponencial."""
        hour = (last_time / 60.0) % 24
        rate = self._get_demand_rate(hour)
        u = 1.0 - self.rng.random()
        interval = -math.log(u) / rate
        self.next_request_time = last_time + interval

    def _get_demand_rate(self, hour: float) -> float:
        """Taxa de pedidos por minuto baseada na hora."""
        if 7.5 <= hour < 9.5:
            intensity = 0.7
        elif 12 <= hour < 14:
            intensity = 0.3
        elif 17 <= hour < 19.5:
            intensity = 0.9
        elif 19.5 <= hour < 21:
            intensity = 0.2
        elif hour < 6.5 or hour > 22:
            intensity = 0.1
        else:
            intensity = 0.1
        return self.base_demand + intensity * self.peak_multiplier

    def _get_hotspot_node(self) -> Optional["Node"]:
        """Escolhe nó de hotspot activo (ponderado por peso)."""
        active = [h for h in self.hotspot_manager.hotspots if h.is_active]
        all_nodes = list(self.city_map.nos)

        if not active:
            return self.rng.choice(all_nodes) if all_nodes else None

        weights = [h.weight for h in active]
        hotspot = self.rng.choices(active, weights=weights, k=1)[0]
        return self.rng.choice(hotspot.node_cache) if hotspot.node_cache else None

    def _create_request(self, creation_time: float) -> Optional[Request]:
        """Cria pedido com origem/destino baseados em hotspots."""
        all_nodes = list(self.city_map.nos)
        if not all_nodes:
            return None

        r = self.rng.random()

        # 40% hotspot→random, 30% random→hotspot, 20% hotspot→hotspot, 10% random
        if r < 0.4:
            start = self._get_hotspot_node()
            end = self.rng.choice(all_nodes)
        elif r < 0.7:
            start = self.rng.choice(all_nodes)
            end = self._get_hotspot_node()
        elif r < 0.9:
            start = self._get_hotspot_node()
            end = self._get_hotspot_node()
        else:
            start = self.rng.choice(all_nodes)
            end = self.rng.choice(all_nodes)

        # Fallback
        start = start or self.rng.choice(all_nodes)
        end = end or self.rng.choice(all_nodes)

        # Evitar origem == destino
        for _ in range(10):
            if start != end:
                break
            end = self.rng.choice(all_nodes)

        path_info = find_route("astar", self.city_map, start, end)
        if not path_info:
            return None

        path, time, dist = path_info

        pax = self.rng.randint(1, 4)
        if self.rng.random() < 0.1:
            pax = self.rng.randint(5, 7)

        priority = self._get_priority(creation_time)
        eco = self.rng.random() < 0.3

        # Preço: grupos grandes pagam mais
        multiplier = 1.3 if pax > 4 else 1.0
        price = (self.BASE_FARE + dist * self.PRICE_PER_KM) * multiplier

        return Request(
            start_node=start,
            end_node=end,
            passenger_capacity=pax,
            creation_time=creation_time,
            price=price,
            priority=priority,
            environmental_preference=eco,
            path=path,
            path_distance=dist,
            path_time=time,
        )

    def _get_priority(self, time_minutes: float) -> int:
        """VIPs mais frequentes em horas de ponta."""
        hour = (time_minutes / 60.0) % 24
        vip_chance = 0.20 if (7.5 < hour < 9.5) or (17.5 < hour < 19.5) else 0.05
        return 5 if self.rng.random() < vip_chance else self.rng.randint(1, 4)
