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
    Centraliza todos os pesos e penalizações para facilitar o tuning.
    """

    # Pesos Base
    WEIGHT_TIME = 1.0  # Peso de 1 minuto de viagem
    WEIGHT_PRIORITY = 30.0  # Quanto vale cada nível de prioridade
    WEIGHT_AGE = 4.0  # Peso por minuto de espera

    # Penalizações "Hard"
    PENALTY_IMPOSSIBLE = float("inf")

    # Penalização dinâmica por Km
    PENALTY_ENV_MISMATCH_PER_KM = 15.0

    PENALTY_UNUSED_SEAT = 5.0  # Por lugar vazio

    # Penalizações
    BATTERY_RISK_EXPONENT = 2.0  # Quão agressiva é a curva de risco (quadrática/exponencial)
    BATTERY_CRITICAL_LEVEL = 30.0  # Abaixo disto, o risco dispara
    WEIGHT_BATTERY_RISK = 20.0  # Multiplicador do fator de risco

    WEIGHT_ISOLATION = 1  # Custo por km de distância de um Hotspot após entrega
    WEIGHT_FUTURE_REFUEL = 1.5  # Custo por km até à estação mais próxima APÓS entrega

    # Custo de Oportunidade
    WEIGHT_LOST_OPPORTUNITY = 40.0  # EV a fazer pedido não-ecológico quando há ecológicos na fila

    BACKLOG_BASE_PENALTY = 160.0  # Custo fixo por deixar alguém para trás


class StrategyManager:
    _hotspots: List[Node] = []

    @classmethod
    def identify_hotspots(cls, simulator: "Simulator"):
        """
        Identifica nós estratégicos (Centrais e de Interesse).
        Usar depois localizações reais
        """
        if cls._hotspots:
            return cls._hotspots

        nodes = list(simulator.map.nos)
        if not nodes:
            return []

        # Centro Geométrico
        avg_x = sum(n.position[0] for n in nodes) / len(nodes)
        avg_y = sum(n.position[1] for n in nodes) / len(nodes)
        center_dummy = Node((avg_x, avg_y))
        center_node = min(nodes, key=lambda n: _heuristic_distance(n, center_dummy))

        cls._hotspots = [center_node]

        # Adicionar pontos aleatórios fixos (ex: Estações, Aeroporto)
        rng = random.Random(42)
        cls._hotspots.extend(rng.sample(nodes, min(len(nodes), 4)))

        return cls._hotspots

    @staticmethod
    def get_dist_to_nearest_hotspot(node: Node, simulator: "Simulator") -> float:
        hotspots = StrategyManager.identify_hotspots(simulator)
        if not hotspots:
            return 0.0
        return min(_heuristic_distance(node, h) for h in hotspots)

    @staticmethod
    def get_dist_to_nearest_station(node: Node, motor: Motor, simulator: "Simulator") -> float:
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
        self.assignment = assignment
        self.backlog = backlog

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
    Calcula o custo total de uma atribuição.
    """
    _, time_to_pickup, dist_to_pickup = path_info

    # Custo Base
    cost = time_to_pickup * PlanningConfig.WEIGHT_TIME

    # Bónus de Atendimento
    wait_time = simulator.current_time - request.creation_time
    cost -= wait_time * PlanningConfig.WEIGHT_AGE
    cost -= (request.priority - 1) * PlanningConfig.WEIGHT_PRIORITY

    # Penalizações proporcionalmente à distância da viagem.
    # Viagens longas num motor a combustão para um cliente Eco custam mais.
    if request.environmental_preference and vehicle.motor == Motor.COMBUSTION:
        cost += request.path_distance * PlanningConfig.PENALTY_ENV_MISMATCH_PER_KM

    if vehicle.passenger_capacity > request.passenger_capacity:
        cost += (
            vehicle.passenger_capacity - request.passenger_capacity
        ) * PlanningConfig.PENALTY_UNUSED_SEAT

    # Estado Futuro e Risco
    total_trip_dist = dist_to_pickup + request.path_distance
    remaining_km_after = vehicle.remaining_km - total_trip_dist

    if remaining_km_after < 0:
        return float("inf")

    # Risco de Bateria (Exponencial)
    risk_factor = 0.0
    if remaining_km_after < PlanningConfig.BATTERY_CRITICAL_LEVEL:
        deficit = PlanningConfig.BATTERY_CRITICAL_LEVEL - remaining_km_after
        risk_factor = (
            deficit**PlanningConfig.BATTERY_RISK_EXPONENT
        ) * PlanningConfig.WEIGHT_BATTERY_RISK
    cost += risk_factor

    # Planeamento Pós-Entrega
    final_pos = request.end_node

    # Estimar distância para o posto mais próximo a partir do destino
    dist_station = StrategyManager.get_dist_to_nearest_station(final_pos, vehicle.motor, simulator)
    if dist_station > remaining_km_after:
        return float("inf")  # Stranded
    cost += dist_station * PlanningConfig.WEIGHT_FUTURE_REFUEL

    # Isolamento (Hotspots)
    dist_hotspot = StrategyManager.get_dist_to_nearest_hotspot(final_pos, simulator)
    cost += dist_hotspot * PlanningConfig.WEIGHT_ISOLATION

    # Custo de Oportunidade Inteligente
    # Só penaliza EV por não levar "Eco" se tiver bateria confortável (> 40% do critico)
    # Se estiver a morrer, aceita qualquer coisa sem penalidade de oportunidade.
    if vehicle.motor == Motor.ELECTRIC and not request.environmental_preference:
        if has_eco_in_backlog:
            # Penaçização em relação à percentagem de bateria (Sobrevivência vs Oportunidade)
            safe_range = vehicle.max_km * 0.6
            battery_factor = min(1.0, vehicle.remaining_km / safe_range)

            cost += PlanningConfig.WEIGHT_LOST_OPPORTUNITY * battery_factor

    return cost


def calculate_total_system_energy(
    state: SAState, cost_matrix: np.ndarray, requests: List[Request], current_time: float
) -> float:
    total_energy = 0.0

    # Atribuições
    for v_idx, r_idx in enumerate(state.assignment):
        if r_idx != -1:
            c = cost_matrix[v_idx, r_idx]
            if c == float("inf"):
                return float("inf")
            total_energy += c

    # Backlog (Penalização)
    for r_idx in state.backlog:
        req = requests[r_idx]
        age = max(0, current_time - req.creation_time)

        prio_cost = (req.priority**2) * PlanningConfig.WEIGHT_PRIORITY
        age_cost = age * PlanningConfig.WEIGHT_AGE * 2.0  # Age pesa no backlog

        total_energy += PlanningConfig.BACKLOG_BASE_PENALTY + prio_cost + age_cost

    return total_energy


def get_neighbor(
    state: SAState, num_vehicles: int, cost_matrix: np.ndarray, requests: List[Request]
) -> SAState:
    """
    Operadores com proteção de estabilidade.
    """
    for _ in range(3):  # Tentar 3x gerar válido
        new_state = state.copy()
        p = random.random()

        busy = [i for i, r in enumerate(new_state.assignment) if r != -1]
        free = [i for i, r in enumerate(new_state.assignment) if r == -1]

        # OP 1: SWAP (25%)
        if p < 0.25 and len(busy) >= 2:
            v1, v2 = random.sample(busy, 2)
            new_state.assignment[v1], new_state.assignment[v2] = (
                new_state.assignment[v2],
                new_state.assignment[v1],
            )
            return new_state

        # OP 2: MOVE (25%)
        elif p < 0.50 and busy and free:
            v_src = random.choice(busy)
            v_dst = random.choice(free)
            r = new_state.assignment[v_src]
            if cost_matrix[v_dst, r] != float("inf"):
                new_state.assignment[v_dst] = r
                new_state.assignment[v_src] = -1
                return new_state

        # OP 3: REPLACE (30%)
        elif p < 0.80 and busy and new_state.backlog:
            v = random.choice(busy)
            r_new = random.choice(list(new_state.backlog))
            r_old = new_state.assignment[v]
            if cost_matrix[v, r_new] != float("inf"):
                new_state.assignment[v] = r_new
                new_state.backlog.remove(r_new)
                new_state.backlog.add(r_old)
                return new_state

        # OP 4: ADD (15%)
        elif free and new_state.backlog:
            v = random.choice(free)
            r = random.choice(list(new_state.backlog))
            if cost_matrix[v, r] != float("inf"):
                new_state.assignment[v] = r
                new_state.backlog.remove(r)
                return new_state

        # OP 5: REMOVE (5%) - Protegido
        elif busy:
            # Só remove se backlog estiver controlado
            if len(new_state.backlog) < num_vehicles * 3:
                v = random.choice(busy)
                r = new_state.assignment[v]
                # Proteção VIP
                if requests[r].priority < 4 or random.random() < 0.1:
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

    # Inicialização Estocástia
    # Preenchimento com ruído para evitar mínimos locais logo no início.
    assign = [-1] * num_vehicles
    backlog = set(range(num_requests))

    # Lista de candidatos ordenados
    sorted_req_indices = sorted(
        range(num_requests), key=lambda i: requests[i].priority, reverse=True
    )

    for r_idx in sorted_req_indices:
        # Tenta atribuir ao primeiro veículo livre e viável
        candidates = []
        for v_idx in range(num_vehicles):
            if assign[v_idx] == -1 and cost_matrix[v_idx, r_idx] != float("inf"):
                candidates.append(v_idx)

        if candidates:
            # Escolhe o melhor candidato com 80% chance, ou aleatório 20%
            best_c = min(candidates, key=lambda v: cost_matrix[v, r_idx])
            if random.random() < 0.8:
                chosen_v = best_c
            else:
                chosen_v = random.choice(candidates)

            assign[chosen_v] = r_idx
            backlog.remove(r_idx)

    current_state = SAState(assign, backlog)
    current_energy = calculate_total_system_energy(
        current_state, cost_matrix, requests, simulator.current_time
    )

    best_state = current_state.copy()
    best_energy = current_energy

    temp = initial_temp
    alpha = 0.96  # Arrefecimento

    stagnation_counter = 0

    # Loop SA com Reheating
    MAX_ITER = 1200
    for i in range(MAX_ITER):
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
        if stagnation_counter > 200:
            temp = min(temp * 1.8, initial_temp)
            stagnation_counter = 0
            current_state = best_state.copy()  # Reset para o melhor conhecido

        temp = max(temp * alpha, 0.05)

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

    # Verificar se há pedidos eco no backlog para penalização de oportunidade
    has_eco = any(r.environmental_preference for r in pending_requests)

    # Construção da Matriz de Custos Inteligente
    cost_matrix = np.full((num_vehicles, num_requests), float("inf"))

    for i in range(num_vehicles):
        v = available_vehicles[i]
        for j in range(num_requests):
            req = pending_requests[j]

            # Filtros Absolutos
            if v.passenger_capacity < req.passenger_capacity:
                continue

            # Pathfinding (A*)
            path_info = find_a_star_route(simulator.map, v.position_node, req.start_node)
            if not path_info:
                continue

            # Cálculo de Custo Estratégico
            cost = calculate_detailed_cost(v, req, path_info, simulator, has_eco)
            cost_matrix[i, j] = cost

    if np.all(cost_matrix == float("inf")):
        return

    # Configuração Dinâmica, reheat inicial se houver VIPs
    initial_temp = 250.0
    max_prio = max(r.priority for r in pending_requests)
    if max_prio >= 4 or len(pending_requests) > num_vehicles:
        initial_temp = 450.0

    final_assignment = simulated_annealing_solver(
        simulator, cost_matrix, pending_requests, initial_temp
    )

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

    dist_str = f"{v.remaining_km:.0f}km"
    print(f"[SA] {v.id} -> {request.id} (Prio {request.priority}). Bat: {dist_str}")

    path_info = find_a_star_route(simulator.map, v.position_node, request.start_node)
    if path_info:
        path, _, _ = path_info
        v.current_route = path
        v.current_segment_index = 0
        v.current_segment_progress_time = 0.0
    else:
        v.request = None
        v.condition = VehicleCondition.AVAILABLE
        if request in simulator.requests_to_pickup:
            simulator.requests_to_pickup.remove(request)
        simulator.requests.append(request)


def generate_new_requests_if_needed(simulator: "Simulator"):
    from mapGen import generate_random_request

    total = (
        len(simulator.requests)
        + len(simulator.requests_to_pickup)
        + len(simulator.requests_to_dropoff)
    )
    target = max(5, int(len(simulator.vehicles) * 0.8))

    if total < simulator.NUM_INITIAL_REQUESTS or len(simulator.requests) < target:
        num = simulator.NUM_REQUESTS_TO_GENERATE
        for _ in range(num):
            simulator.requests.append(
                generate_random_request(
                    simulator.map, list(simulator.map.nos), simulator.current_time
                )
            )
