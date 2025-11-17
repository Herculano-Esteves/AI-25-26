from typing import List, TYPE_CHECKING, Tuple, Set, Optional
from models.request import Request
from models.vehicle import Vehicle, VehicleCondition, Motor
from search import find_a_star_route, _heuristic_distance
from models.node import Node
import random
import math
import numpy as np

if TYPE_CHECKING:
    from simulator import Simulator


class PlanningConfig:
    """
    Centraliza todos os pesos e penalizações para facilitar o tuning e a explicação no relatório.
    """

    # Pesos Base
    WEIGHT_TIME = 1.0  # Peso de 1 minuto de viagem
    WEIGHT_PRIORITY = 25.0  # Quanto vale cada nível de prioridade
    WEIGHT_AGE = 3.0  # Peso por minuto de espera

    # Penalizações "Hard"
    PENALTY_IMPOSSIBLE = float("inf")
    PENALTY_ENV_MISMATCH = 80.0  # Veículo a combustão em pedido "Green"
    PENALTY_UNUSED_SEAT = 5.0  # Por lugar vazio

    # Penalizações "Soft"
    # Topic 5: Risco de Bateria
    BATTERY_RISK_EXPONENT = 1.8  # Quão agressiva é a curva de risco (quadrática/exponencial)
    BATTERY_CRITICAL_LEVEL = 25.0  # Abaixo disto, o risco dispara
    WEIGHT_BATTERY_RISK = 15.0  # Multiplicador do fator de risco

    # Isolamento e Hotspots
    WEIGHT_ISOLATION = 0.8  # Custo por km de distância de um Hotspot após entrega

    # Recarga Futura
    WEIGHT_FUTURE_REFUEL = 1.5  # Custo por km até à estação mais próxima APÓS entrega

    # Custo de Oportunidade
    WEIGHT_LOST_OPPORTUNITY = 40.0  # EV a fazer pedido não-ecológico quando há ecológicos na fila

    # Backlog
    BACKLOG_BASE_PENALTY = 150.0  # Custo fixo por deixar alguém para trás


class StrategyManager:
    _hotspots: List[Node] = []

    @classmethod
    def identify_hotspots(self, simulator: "Simulator"):  # Usar depois localizações reais
        """
        Identifica nós estratégicos no mapa (Topic 3).
        Critério: Nós com mais conexões ou centrais.
        Simplificação: Escolhe 4 nós aleatórios mas consistentes se não houver dados de centralidade.
        """
        if self._hotspots:
            return self._hotspots

        nodes = list(simulator.map.nos)
        if not nodes:
            return []

        # Heurística simples para "Centro da Cidade" (média das coordenadas)
        avg_x = sum(n.position[0] for n in nodes) / len(nodes)
        avg_y = sum(n.position[1] for n in nodes) / len(nodes)
        center_dummy = Node((avg_x, avg_y))

        # Encontrar o nó real mais próximo do centro geométrico
        center_node = min(nodes, key=lambda n: _heuristic_distance(n, center_dummy))

        # Adicionar o centro e alguns nós periféricos distantes para cobrir área
        self._hotspots = [center_node]

        # Adicionar mais 3 hotspots aleatórios para simular zonas de interesse (Estação, Shopping, etc.)
        # Usamos seed para consistência
        random.seed(42)
        self._hotspots.extend(random.sample(nodes, min(len(nodes), 3)))
        random.seed()  # Reset seed

        print(f"[Strategy] {len(self._hotspots)} Hotspots identificados para planeamento.")
        return self._hotspots

    @staticmethod
    def get_dist_to_nearest_hotspot(node: Node, simulator: "Simulator") -> float:
        hotspots = StrategyManager.identify_hotspots(simulator)
        if not hotspots:
            return 0.0
        # Usa heurística (linha reta) para ser rápido. A* aqui seria muito lento.
        return min(_heuristic_distance(node, h) for h in hotspots)

    @staticmethod
    def get_dist_to_nearest_station(node: Node, motor: Motor, simulator: "Simulator") -> float:
        """Retorna distância estimada à estação compatível mais próxima."""
        stations = []
        if motor == Motor.ELECTRIC:
            stations = [n for n in simulator.map.nos if n.energy_chargers > 0]
        else:
            stations = [n for n in simulator.map.nos if n.gas_pumps > 0]

        if not stations:
            return float("inf")

        return min(_heuristic_distance(node, s) for s in stations)


class SAState:
    def __init__(self, assignment: List[int], backlog: Set[int]):
        self.assignment = assignment  # assignment[v_idx] = req_idx (ou -1)
        self.backlog = backlog  # set de req_idxs

    def copy(self):
        return SAState(self.assignment.copy(), self.backlog.copy())


def calculate_detailed_cost(
    vehicle: Vehicle,
    request: Request,
    path_info: Tuple[list, float, float],
    simulator: "Simulator",
    has_eco_in_backlog: bool,
) -> float:
    """
    Calcula o custo TOTAL de uma atribuição (Viagem + Futuro + Risco).
    Aqui reside a inteligência da Fase 3.
    """
    _, time_to_pickup, dist_to_pickup = path_info

    # Custo Base (Tempo)
    cost = time_to_pickup * PlanningConfig.WEIGHT_TIME

    # Bónus (Idade e Prioridade) - Reduzem o custo para tornar atrativo
    wait_time = simulator.current_time - request.creation_time
    cost -= wait_time * PlanningConfig.WEIGHT_AGE
    cost -= (request.priority - 1) * PlanningConfig.WEIGHT_PRIORITY

    # Penalizações "Hard"
    if request.environmental_preference and vehicle.motor == Motor.COMBUSTION:
        cost += PlanningConfig.PENALTY_ENV_MISMATCH

    unused_seats = vehicle.passenger_capacity - request.passenger_capacity
    if unused_seats > 0:
        cost += unused_seats * PlanningConfig.PENALTY_UNUSED_SEAT

    # Análise de Estado Futuro (Lookahead Simplificado)
    # O veículo vai viajar: Pickup -> Destino
    total_trip_dist = dist_to_pickup + request.path_distance
    remaining_km_after = vehicle.remaining_km - total_trip_dist

    # Restrição física absoluta
    if remaining_km_after < 0:
        return float("inf")

    # Curva exponencial: quanto mais perto de 0, mais caro fica
    risk_factor = 0.0
    if remaining_km_after < vehicle.max_km:  # Só se gastou algo
        if remaining_km_after < PlanningConfig.BATTERY_CRITICAL_LEVEL:
            # Penalidade cresce drasticamente
            deficit = PlanningConfig.BATTERY_CRITICAL_LEVEL - remaining_km_after
            risk_factor = (
                deficit**PlanningConfig.BATTERY_RISK_EXPONENT
            ) * PlanningConfig.WEIGHT_BATTERY_RISK

    cost += risk_factor

    final_pos_node = request.end_node

    # Estimar distância para o posto mais próximo a partir do DESTINO
    dist_to_station = StrategyManager.get_dist_to_nearest_station(
        final_pos_node, vehicle.motor, simulator
    )

    # Se a distância ao posto for maior que a autonomia que sobra... catástrofe.
    if dist_to_station > remaining_km_after:
        return float("inf")  # Veículo ficaria stranded após a entrega

    cost += dist_to_station * PlanningConfig.WEIGHT_FUTURE_REFUEL

    # Evitar mandar carros para o meio do nada se não necessário
    dist_to_hotspot = StrategyManager.get_dist_to_nearest_hotspot(final_pos_node, simulator)
    cost += dist_to_hotspot * PlanningConfig.WEIGHT_ISOLATION

    # Se sou um EV e estou a levar um pedido normal, mas há pedidos ECO na fila
    if vehicle.motor == Motor.ELECTRIC and not request.environmental_preference:
        if has_eco_in_backlog:
            cost += PlanningConfig.WEIGHT_LOST_OPPORTUNITY

    return cost


def calculate_total_system_energy(
    state: SAState, cost_matrix: np.ndarray, requests: List[Request], current_time: float
) -> float:
    """
    Função de avaliação global (Energia).
    Soma custos de atribuição + Penalizações pesadas de Backlog.
    """
    total_energy = 0.0

    #  Custo das Atribuições
    for v_idx, r_idx in enumerate(state.assignment):
        if r_idx != -1:
            c = cost_matrix[v_idx, r_idx]
            if c == float("inf"):
                return float("inf")
            total_energy += c

    # Custo do Backlog (Feedback dinâmico via Age)
    for r_idx in state.backlog:
        req = requests[r_idx]
        age = max(0, current_time - req.creation_time)

        # VIPs no backlog custam muito mais (quadrático)
        prio_cost = (req.priority**2) * PlanningConfig.WEIGHT_PRIORITY
        age_cost = (
            age * PlanningConfig.WEIGHT_AGE * 1.5
        )  # Age pesa mais no backlog que na atribuição

        total_energy += PlanningConfig.BACKLOG_BASE_PENALTY + prio_cost + age_cost

    return total_energy


def get_neighbor(
    state: SAState, num_vehicles: int, cost_matrix: np.ndarray, requests: List[Request]
) -> SAState:
    """
    Gerador de vizinhos com operadores inteligentes.
    Tenta 3x para garantir que não devolve o mesmo estado falhado.
    """
    best_neighbor = state  # Fallback

    # Tentativas de gerar algo válido
    for _ in range(3):
        new_state = state.copy()
        p = random.random()

        busy = [i for i, r in enumerate(new_state.assignment) if r != -1]
        free = [i for i, r in enumerate(new_state.assignment) if r == -1]

        #  SWAP (25%) - Troca entre carros
        if p < 0.25 and len(busy) >= 2:
            v1, v2 = random.sample(busy, 2)
            new_state.assignment[v1], new_state.assignment[v2] = (
                new_state.assignment[v2],
                new_state.assignment[v1],
            )
            return new_state

        # MOVE (25%) - Ocupado para Livre
        elif p < 0.50 and busy and free:
            v_src = random.choice(busy)
            v_dst = random.choice(free)
            r = new_state.assignment[v_src]
            if cost_matrix[v_dst, r] != float("inf"):
                new_state.assignment[v_dst] = r
                new_state.assignment[v_src] = -1
                return new_state

        # REPLACE (30%) - Backlog substitui Ocupado
        elif p < 0.80 and busy and new_state.backlog:
            v = random.choice(busy)
            r_new = random.choice(list(new_state.backlog))
            r_old = new_state.assignment[v]

            if cost_matrix[v, r_new] != float("inf"):
                new_state.assignment[v] = r_new
                new_state.backlog.remove(r_new)
                new_state.backlog.add(r_old)
                return new_state

        # ADD (15%) - Backlog para Livre
        elif free and new_state.backlog:
            v = random.choice(free)
            r = random.choice(list(new_state.backlog))
            if cost_matrix[v, r] != float("inf"):
                new_state.assignment[v] = r
                new_state.backlog.remove(r)
                return new_state

        # REMOVE (5%) - Proteção contra mínimos locais
        # (Difícil remover VIPs)
        elif busy:
            v = random.choice(busy)
            r = new_state.assignment[v]
            if requests[r].priority < 4 or random.random() < 0.1:  # Só 10% chance se for VIP
                new_state.assignment[v] = -1
                new_state.backlog.add(r)
                return new_state

    return state


def simulated_annealing_solver(
    simulator: "Simulator",
    cost_matrix: np.ndarray,
    requests: List[Request],
    initial_temp: float = 200.0,
):
    num_vehicles = cost_matrix.shape[0]
    num_requests = cost_matrix.shape[1]

    # Estado Inicial Guloso (Preencher o máximo possível)
    assign = [-1] * num_vehicles
    backlog = set(range(num_requests))

    # Ordenar pedidos por prioridade para tentar encaixá-los primeiro
    sorted_req_indices = sorted(
        range(num_requests), key=lambda i: requests[i].priority, reverse=True
    )

    for r_idx in sorted_req_indices:
        # Tentar encontrar um veículo livre
        for v_idx in range(num_vehicles):
            if assign[v_idx] == -1 and cost_matrix[v_idx, r_idx] != float("inf"):
                assign[v_idx] = r_idx
                backlog.remove(r_idx)
                break

    current_state = SAState(assign, backlog)
    current_energy = calculate_total_system_energy(
        current_state, cost_matrix, requests, simulator.current_time
    )

    best_state = current_state.copy()
    best_energy = current_energy

    temp = initial_temp
    alpha = 0.97

    # Reheating Logic
    stagnation_counter = 0

    for i in range(1000):  # Iterações fixas
        neighbor = get_neighbor(current_state, num_vehicles, cost_matrix, requests)
        neighbor_energy = calculate_total_system_energy(
            neighbor, cost_matrix, requests, simulator.current_time
        )

        if neighbor_energy == float("inf"):
            continue

        delta = neighbor_energy - current_energy

        accept = False
        if delta <= 0:
            accept = True
        else:
            if temp > 0.01:
                try:
                    if random.random() < math.exp(-delta / temp):
                        accept = True
                except:
                    pass

        if accept:
            current_state = neighbor
            current_energy = neighbor_energy
            if current_energy < best_energy:
                best_state = current_state.copy()
                best_energy = current_energy
                stagnation_counter = 0
            else:
                stagnation_counter += 1
        else:
            stagnation_counter += 1

        # Reheat se estagnado
        if stagnation_counter > 150:
            temp = min(temp * 1.5, initial_temp)
            stagnation_counter = 0
            current_state = best_state.copy()  # Reset para o melhor conhecido

        temp = max(temp * alpha, 0.01)

    return best_state.assignment


def assign_pending_requests(simulator: "Simulator"):
    pending_requests = simulator.requests
    if not pending_requests:
        return

    available_vehicles = [
        v
        for v in simulator.vehicles
        if v.condition == VehicleCondition.AVAILABLE
        and v.remaining_km >= simulator.LOW_AUTONOMY_THRESHOLD
    ]

    if not available_vehicles:
        return

    # Inicializar Hotspots se necessário
    StrategyManager.identify_hotspots(simulator)

    num_vehicles = len(available_vehicles)
    num_requests = len(pending_requests)

    # Verificar se há pedidos eco no backlog (para penalização de oportunidade)
    has_eco = any(r.environmental_preference for r in pending_requests)

    # Construção da Matriz de Custos Inteligente
    cost_matrix = np.full((num_vehicles, num_requests), float("inf"))

    for i in range(num_vehicles):
        v = available_vehicles[i]
        for j in range(num_requests):
            req = pending_requests[j]

            # Filtros Absolutos (Hard Constraints)
            if v.passenger_capacity < req.passenger_capacity:
                continue

            # Pathfinding (A*)
            path_info = find_a_star_route(simulator.map, v.position_node, req.start_node)
            if not path_info:
                continue

            # Cálculo de Custo Estratégico
            cost = calculate_detailed_cost(v, req, path_info, simulator, has_eco)
            cost_matrix[i, j] = cost

    # Se tudo for impossível, sair
    if np.all(cost_matrix == float("inf")):
        return

    # Configuração Dinâmica do SA
    # Se houver VIPs (>3) ou backlog grande, aumentamos a temperatura inicial (Reheat)
    initial_temp = 200.0
    max_prio = max(r.priority for r in pending_requests)
    if max_prio >= 4 or len(pending_requests) > num_vehicles * 2:
        print(f"[Planner] Modo Alta Intensidade Ativado (VIP/Backlog)")
        initial_temp = 400.0

    # Executar SA
    final_assignment = simulated_annealing_solver(
        simulator, cost_matrix, pending_requests, initial_temp
    )

    # Aplicar Resultados
    assignments_to_make = []
    for v_idx, r_idx in enumerate(final_assignment):
        if r_idx != -1:
            vehicle = available_vehicles[v_idx]
            req = pending_requests[r_idx]
            assignments_to_make.append((vehicle, req))

    for v, r in assignments_to_make:
        if r in simulator.requests and v.condition == VehicleCondition.AVAILABLE:
            assign_request_to_vehicle(simulator, r, v)


def assign_request_to_vehicle(simulator: "Simulator", request: Request, v: Vehicle):
    if request in simulator.requests:
        simulator.requests.remove(request)

    simulator.requests_to_pickup.append(request)
    v.request = request
    v.condition = VehicleCondition.ON_WAY_TO_CLIENT

    # Log mais rico para debug
    dist_str = f"{v.remaining_km:.0f}km"
    print(f"[Atribuição] {v.id} -> {request.id} (Prio {request.priority}). Bat: {dist_str}")

    path_info = find_a_star_route(simulator.map, v.position_node, request.start_node)
    if path_info:
        path, _, _ = path_info
        v.current_route = path
        v.current_segment_index = 0
        v.current_segment_progress_time = 0.0
    else:
        # Fallback de erro
        v.request = None
        v.condition = VehicleCondition.AVAILABLE
        if request in simulator.requests_to_pickup:
            simulator.requests_to_pickup.remove(request)
        simulator.requests.append(request)


def generate_new_requests_if_needed(simulator: "Simulator"):
    # Lógica original de geração
    from mapGen import generate_random_request

    total = (
        len(simulator.requests)
        + len(simulator.requests_to_pickup)
        + len(simulator.requests_to_dropoff)
    )

    # Mantém um nível mínimo de pressão no sistema
    target_requests = max(5, int(len(simulator.vehicles) * 0.8))

    if total < simulator.NUM_INITIAL_REQUESTS or len(simulator.requests) < target_requests:
        num = simulator.NUM_REQUESTS_TO_GENERATE
        for _ in range(num):
            simulator.requests.append(
                generate_random_request(
                    simulator.map, list(simulator.map.nos), simulator.current_time
                )
            )
