import random
import math
import numpy as np
from typing import List, Optional, TYPE_CHECKING
from models.request import Request
from search import find_a_star_route

if TYPE_CHECKING:
    from graph import CityGraph
    from models.node import Node


class RequestGenerator:
    def __init__(self, city_map: "CityGraph", seed: int = 42):
        self.city_map = city_map

        # Deterministic number generator
        self.rng = random.Random(seed)
        self.next_request_time: float = -1.0

        # Demand of requests
        self.base_demand = 0.05
        self.peak_multiplier = 0.2

        # Prices per Km
        self.BASE_FARE = 2.50
        self.PRICE_PER_KM = 0.80

    def update(self, current_time: float, requests_list: List[Request]):
        """
        Verifica se está na hora de criar um novo pedido.
        Se sim, cria-o e agenda o próximo.
        """

        if self.next_request_time < 0:
            # Creates the first request
            self.next_request_time = current_time + 0.1
            return

        while current_time >= self.next_request_time:

            new_req = self._create_deterministic_request(self.next_request_time)

            if new_req:
                requests_list.append(new_req)
                hour = (self.next_request_time / 60.0) % 24
                print(
                    f"[Generator] Novo Pedido {new_req.id} às {hour:.2f}h (Prio {new_req.priority}) - €{new_req.price:.2f}"
                )

            self._schedule_next_request(self.next_request_time)

    def _schedule_next_request(self, last_time: float):
        """
        Calcula o intervalo até ao próximo pedido usando distribuição exponencial.
        Intervalo = -ln(U) / lambda
        """
        hour_of_day = (last_time / 60.0) % 24
        demand_rate = self._get_current_demand_rate(hour_of_day)

        # Deterministic u value
        # random() dá [0.0, 1.0[. Log de 0 é erro, por isso 1 - random
        u = 1.0 - self.rng.random()

        interval_minutes = -math.log(u) / demand_rate

        self.next_request_time = last_time + interval_minutes

    def _get_current_demand_rate(self, hour: float) -> float:
        """
        Define a 'temperatura' da cidade.
        Retorna pedidos por minuto.
        """
        total_intensity = 0.1

        if 7.5 <= hour < 9.5:
            total_intensity = 0.7

        # Almoço (12h - 14h)
        elif 12 <= hour < 14:
            total_intensity = 0.3

        # Tarde (17h - 19h30) - Pico Máximo
        elif 17 <= hour < 19.5:
            total_intensity = 0.9

        # Pré-noite (19h30 - 21h)
        elif 19.5 <= hour < 21:
            total_intensity = 0.2

        # Madrugada / Noite
        elif hour < 6.5 or hour > 22:
            total_intensity = 0.1

        final_rate = self.base_demand + (total_intensity * self.peak_multiplier)

        return final_rate

    def _create_deterministic_request(self, creation_time: float) -> Optional[Request]:
        """
        Gera um pedido completo com PATH REAL calculado.
        Retorna None se não encontrar caminho.
        """
        all_nodes = list(self.city_map.nos)
        if not all_nodes:
            return None

        # Node choice
        start_node = self.rng.choice(all_nodes)
        end_node = self.rng.choice(all_nodes)

        while start_node == end_node:
            end_node = self.rng.choice(all_nodes)

        path_info = find_a_star_route(self.city_map, start_node, end_node)

        if not path_info:
            return None

        real_path, real_time, real_dist = path_info

        # Random (Deterministic) passenger capacity
        pax = self.rng.randint(1, 4)
        if self.rng.random() < 0.1:
            pax = self.rng.randint(5, 7)

        priority = self._determine_priority_by_hour(creation_time)
        eco_pref = self.rng.random() < 0.3

        # Price based on distance
        price = self.BASE_FARE + (real_dist * self.PRICE_PER_KM)

        return Request(
            start_node=start_node,
            end_node=end_node,
            passenger_capacity=pax,
            creation_time=creation_time,
            price=price,
            priority=priority,
            environmental_preference=eco_pref,
            # Preencher os dados reais
            path=real_path,
            path_distance=real_dist,
            path_time=real_time,
        )

    def _determine_priority_by_hour(self, time_minutes: float) -> int:
        hour = (time_minutes / 60.0) % 24
        vip_chance = 0.05
        if (7.5 < hour < 9.5) or (17.5 < hour < 19.5):
            vip_chance = 0.20

        if self.rng.random() < vip_chance:
            return 5

        return self.rng.randint(1, 4)
