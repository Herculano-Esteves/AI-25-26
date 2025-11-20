import random
import math
import numpy as np
from typing import List, Optional, TYPE_CHECKING
from models.request import Request
from search import find_a_star_route, _heuristic_distance

if TYPE_CHECKING:
    from graph import CityGraph
    from models.node import Node

class RequestGenerator:
    def __init__(self, city_map: "CityGraph", seed: int = 42):
        self.city_map = city_map
        
        # Gerador de números aleatórios ISOLADO para garantir determinismo.
        self.rng = random.Random(seed)
        
        # Inicia negativo para forçar o primeiro agendamento
        self.next_request_time: float = -1.0
        
        # Configuração da Procura
        self.base_demand = 0.01
        self.peak_multiplier = 0.1

        # Preços
        self.BASE_FARE = 2.50
        self.PRICE_PER_KM = 0.80

    def update(self, current_time: float, requests_list: List[Request]):
        """
        Verifica se está na hora de criar um novo pedido.
        Se sim, cria-o e agenda o próximo.
        """
        # Inicialização do primeiro agendamento
        if self.next_request_time < 0:
            # Agendar o primeiro pedido para AGORA ou muito em breve
            # (Evita o "vazio" inicial que pode confundir o utilizador)
            self.next_request_time = current_time + 0.1
            return

        # Loop para garantir que geramos todos os pedidos em atraso (se houver lag)
        while current_time >= self.next_request_time:
            
            # 1. Criar o Pedido Agora
            new_req = self._create_deterministic_request(self.next_request_time)
            
            # Só adicionamos se for válido (tiver caminho)
            if new_req:
                requests_list.append(new_req)
                hour = (self.next_request_time / 60.0) % 24
                print(f"[Generator] Novo Pedido {new_req.id} às {hour:.2f}h (Prio {new_req.priority}) - €{new_req.price:.2f}")
            
            # 2. Agendar o Próximo (Processo de Poisson)
            self._schedule_next_request(self.next_request_time)

    def _schedule_next_request(self, last_time: float):
        """
        Calcula o intervalo até ao próximo pedido usando distribuição exponencial.
        Intervalo = -ln(U) / lambda
        """
        hour_of_day = (last_time / 60.0) % 24
        demand_rate = self._get_current_demand_rate(hour_of_day)

        # random() dá [0.0, 1.0). Log de 0 é erro, por isso 1 - random
        u = 1.0 - self.rng.random()
        
        # Evitar divisão por zero se a procura for muito baixa
        if demand_rate <= 0.001: demand_rate = 0.001
            
        interval_minutes = -math.log(u) / demand_rate
        
        self.next_request_time = last_time + interval_minutes

    def _get_current_demand_rate(self, hour: float) -> float:
        """
        Define a 'temperatura' da cidade.
        Retorna pedidos por minuto.
        """
        def gaussian(h, peak, width, height):
            return height * math.exp(-((h - peak) ** 2) / (2 * width ** 2))

        morning = gaussian(hour, 8.0, 1.5, 1.0)
        lunch = gaussian(hour, 12.5, 1.0, 0.6)
        evening = gaussian(hour, 18.0, 2.0, 1.2)
        night = gaussian(hour, 21.0, 1.5, 0.5)

        total_intensity = morning + lunch + evening + night
        final_rate = self.base_demand + (total_intensity * self.peak_multiplier)
        
        return final_rate

    def _create_deterministic_request(self, creation_time: float) -> Optional[Request]:
        """
        Gera um pedido completo com PATH REAL calculado.
        Retorna None se não encontrar caminho.
        """
        all_nodes = list(self.city_map.nos)
        if not all_nodes: return None
        
        # Escolha de nós
        start_node = self.rng.choice(all_nodes)
        end_node = self.rng.choice(all_nodes)
        tries = 0
        while start_node == end_node and tries < 10:
            end_node = self.rng.choice(all_nodes)
            tries += 1

        # Sem isto, o veiculo chega ao cliente e não sabe para onde ir (path=None)
        # Não passamos traffic_manager aqui para o path ser o "ideal" base para calcular preço
        path_info = find_a_star_route(self.city_map, start_node, end_node)
        
        if not path_info:
            # Se não há caminho (ilhas isoladas no grafo), abortar este pedido
            return None
            
        real_path, real_time, real_dist = path_info

        # Atributos
        pax = self.rng.randint(1, 4)
        if self.rng.random() < 0.1: pax = self.rng.randint(5, 7) 

        priority = self._determine_priority_by_hour(creation_time)
        eco_pref = self.rng.random() < 0.3 

        # Preço Real baseado na distância real
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
            path_time=real_time
        )

    def _determine_priority_by_hour(self, time_minutes: float) -> int:
        hour = (time_minutes / 60.0) % 24
        vip_chance = 0.05
        if (7.5 < hour < 9.5) or (17.5 < hour < 19.5):
            vip_chance = 0.20
            
        if self.rng.random() < vip_chance:
            return 5
            
        return self.rng.randint(1, 3)