from typing import List, TYPE_CHECKING, Tuple, Set
from models.request import Request
from models.vehicle import Vehicle, VehicleCondition, Motor
from search import find_a_star_route
import random
import math
import numpy as np

if TYPE_CHECKING:
    from simulator import Simulator

# CONSTANTES DE PENALIZAÇÃO (TUNING)
ENVIRONMENTAL_PREFERENCE_PENALTY = 50.0
PER_UNUSED_PASSENGER_SEAT_PENALTY = 2.0
REQUEST_AGE_PRIORITY_WEIGHT = 2.0  # Aumentado para valorizar espera
REQUEST_PRIORITY_WEIGHT = 25.0  # Valoriza clientes VIP

# Crítica 2: Penalizações de Estado Futuro
BATTERY_LOW_THRESHOLD = 20.0  # Km mínimos aceitáveis após viagem
BATTERY_RISK_PENALTY = 500.0  # Penalidade severa por arriscar ficar sem bateria

# Crítica 1: Penalizações de Backlog Dinâmicas
BACKLOG_BASE_PENALTY = 100.0
BACKLOG_AGE_FACTOR = 5.0  # Multiplicador por minuto de espera

# Parâmetros do SA
SA_INITIAL_TEMP = 250.0
SA_ALPHA = 0.98
SA_MIN_TEMP = 0.1 # Evitar congelamento absoluto
SA_MAX_ITER = 2000  # Mais iterações para permitir reheating


class SAState:
    def __init__(self, assignment: List[int], backlog: Set[int]):
        # assignment[v_idx] = req_idx (ou -1 se vazio)
        self.assignment = assignment
        # backlog = conjunto de req_idxs não atribuídos
        self.backlog = backlog

    def copy(self):
        return SAState(self.assignment.copy(), self.backlog.copy())


def calculate_total_energy(
    state: SAState, cost_matrix: np.ndarray, requests: List[Request], current_time: float
) -> float:
    """
    Calcula a Energia Total (Custo).
    Reflete Crítica 1 (Idade no Backlog) e Crítica 2 (Custo Futuro via Matrix).
    """
    total_energy = 0.0

    # 1. Custo dos Atribuídos (Operacional + Risco Futuro)
    for v_idx, r_idx in enumerate(state.assignment):
        if r_idx != -1:
            cost = cost_matrix[v_idx, r_idx]
            if cost == float("inf"):
                return float("inf")
            total_energy += cost

    # 2. Custo do Backlog
    for r_idx in state.backlog:
        req = requests[r_idx]

        # Idade real do pedido
        age_minutes = max(0, current_time - req.creation_time)

        # Fórmula: Base + (Prioridade * Peso) + (Idade * Peso)
        # Pedidos antigos e prioritários tornam-se "radioativos" no backlog
        priority_cost = req.priority * REQUEST_PRIORITY_WEIGHT
        age_cost = age_minutes * BACKLOG_AGE_FACTOR

        total_energy += BACKLOG_BASE_PENALTY + priority_cost + age_cost

    return total_energy


def get_neighbor(
    state: SAState,
    num_vehicles: int,
    num_requests: int,
    cost_matrix: np.ndarray,
    requests: List[Request],
) -> SAState:
    """
    Gera vizinhos com operadores avançados (Crítica 3: REPLACE, Crítica 4: Proteção Backlog).
    Usa lógica de Retry (Crítica 3.2) para evitar falhas.
    """
    # Tentar gerar um vizinho válido até 3 vezes
    for _ in range(3):
        new_state = state.copy()

        # Probabilidades de Operadores
        # Ajustadas para favorecer trocas inteligentes
        p = random.random()

        busy_vehicles = [i for i, r in enumerate(new_state.assignment) if r != -1]
        free_vehicles = [i for i, r in enumerate(new_state.assignment) if r == -1]

        # SWAP (Troca entre dois veículos ocupados) 
        if p < 0.25:
            if len(busy_vehicles) >= 2:
                v1, v2 = random.sample(busy_vehicles, 2)
                # Swap
                new_state.assignment[v1], new_state.assignment[v2] = (
                    new_state.assignment[v2],
                    new_state.assignment[v1],
                )
                return new_state

        # MOVE (Move de ocupado para livre)
        elif p < 0.50:
            if busy_vehicles and free_vehicles:
                v_src = random.choice(busy_vehicles)
                v_dst = random.choice(free_vehicles)
                req_idx = new_state.assignment[v_src]

                if cost_matrix[v_dst, req_idx] != float("inf"):
                    new_state.assignment[v_dst] = req_idx
                    new_state.assignment[v_src] = -1
                    return new_state

        # Replace, Substitui o pedido atual de um carro por um do backlog (útil se o do backlog for VIP)
        elif p < 0.75:
            if busy_vehicles and new_state.backlog:
                v_target = random.choice(busy_vehicles)
                r_new = random.choice(list(new_state.backlog))
                r_old = new_state.assignment[v_target]

                if cost_matrix[v_target, r_new] != float("inf"):
                    # Troca
                    new_state.assignment[v_target] = r_new
                    new_state.backlog.remove(r_new)
                    new_state.backlog.add(r_old)
                    return new_state

            # Fallback para ADD se REPLACE não for possível (para não desperdiçar ciclo)
            if free_vehicles and new_state.backlog:
                v_dst = random.choice(free_vehicles)
                r_add = random.choice(list(new_state.backlog))
                if cost_matrix[v_dst, r_add] != float("inf"):
                    new_state.assignment[v_dst] = r_add
                    new_state.backlog.remove(r_add)
                    return new_state

        # REMOVE (Proteção VIP)
        else:
            if busy_vehicles:
                # Limite de backlog para não explodir
                if len(new_state.backlog) > num_vehicles * 3:
                    continue

                v_src = random.choice(busy_vehicles)
                req_idx = new_state.assignment[v_src]
                req = requests[req_idx]

                # Proteção VIP
                # Se for prioridade alta, 80% de chance de abortar a remoção
                if req.priority >= 4 and random.random() < 0.8:
                    continue

                new_state.assignment[v_src] = -1
                new_state.backlog.add(req_idx)
                return new_state

    # Se falhar 3x, retorna original
    return state


def simulated_annealing_solver(
    simulator: "Simulator", cost_matrix: np.ndarray, requests: List[Request]
):
    """
    Solver principal com Reheating e Zero Delta Acceptance.
    """
    num_vehicles = cost_matrix.shape[0]
    num_requests = cost_matrix.shape[1]
    current_time = simulator.current_time

    # 1. Estado Inicial (Construtivo Simples)
    initial_assignment = [-1] * num_vehicles
    initial_backlog = set(range(num_requests))

    # Tentar preencher o máximo possível inicialmente
    req_list_indices = list(range(num_requests))
    # Ordenar por prioridade para tentar encaixar os VIPs primeiro no estado inicial
    req_list_indices.sort(key=lambda r: requests[r].priority, reverse=True)

    for r_idx in req_list_indices:
        # Procura primeiro carro livre capaz
        for v_idx in range(num_vehicles):
            if initial_assignment[v_idx] == -1 and cost_matrix[v_idx, r_idx] != float("inf"):
                initial_assignment[v_idx] = r_idx
                initial_backlog.remove(r_idx)
                break

    current_state = SAState(initial_assignment, initial_backlog)
    current_energy = calculate_total_energy(current_state, cost_matrix, requests, current_time)

    best_state = current_state.copy()
    best_energy = current_energy

    temp = SA_INITIAL_TEMP

    # Contadores para Reheating
    iter_since_improvement = 0
    REHEAT_THRESHOLD = 300  # Se não melhorar em 300 iterações, aquece

    # 2. Loop SA
    for i in range(SA_MAX_ITER):
        neighbor = get_neighbor(current_state, num_vehicles, num_requests, cost_matrix, requests)
        neighbor_energy = calculate_total_energy(neighbor, cost_matrix, requests, current_time)

        if neighbor_energy == float("inf"):
            continue

        delta = neighbor_energy - current_energy

        # Aceitar delta 0
        accept = False
        if delta <= 0:
            accept = True
        else:
            if temp > SA_MIN_TEMP:
                try:
                    prob = math.exp(-delta / temp)
                    if random.random() < prob:
                        accept = True
                except OverflowError:
                    accept = False

        if accept:
            current_state = neighbor
            current_energy = neighbor_energy

            if current_energy < best_energy:
                best_state = current_state.copy()
                best_energy = current_energy
                iter_since_improvement = 0
            else:
                iter_since_improvement += 1
        else:
            iter_since_improvement += 1

        # Reheating Automático
        if iter_since_improvement > REHEAT_THRESHOLD:
            temp = min(temp * 2.0, SA_INITIAL_TEMP)  # Aquece
            iter_since_improvement = 0
            # Voltar ao best state para tentar outro caminho
            current_state = best_state.copy()
            current_energy = best_energy

        # Arrefecimento com limite mínimo
        temp = max(temp * SA_ALPHA, SA_MIN_TEMP)

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

    num_vehicles = len(available_vehicles)
    num_requests = len(pending_requests)

    # Inicialização da matriz de custos
    cost_matrix = np.full((num_vehicles, num_requests), float("inf"))

    for i in range(num_vehicles):
        vehicle = available_vehicles[i]
        for j in range(num_requests):
            request = pending_requests[j]

            # 1. Capacidade
            if vehicle.passenger_capacity < request.passenger_capacity:
                continue

            # 2. A* pathfinding
            path_info = find_a_star_route(simulator.map, vehicle.position_node, request.start_node)
            if not path_info:
                continue

            _, time_to_pickup, dist_to_pickup = path_info

            # 3. Autonomia & Custo Futuro
            dist_to_refuel = float("inf")
            if vehicle.motor == Motor.ELECTRIC:
                dist_to_refuel = request.nearest_ev_station_distance
            else:
                dist_to_refuel = request.nearest_gas_station_distance

            if dist_to_refuel == float("inf"):
                continue  # Sem estação alcançável no destino, risco total

            total_distance_needed = dist_to_pickup + request.path_distance + dist_to_refuel

            # Check hard constraint
            if vehicle.remaining_km < total_distance_needed:
                continue

            # Check Soft Constraint (Future Battery Risk)
            # Se a viagem deixar o carro com < 20km, aplica penalidade severa
            remaining_after_trip = vehicle.remaining_km - (dist_to_pickup + request.path_distance)
            future_risk_cost = 0.0

            if vehicle.motor == Motor.ELECTRIC and remaining_after_trip < BATTERY_LOW_THRESHOLD:
                future_risk_cost = BATTERY_RISK_PENALTY

            # Custo Base
            wait_time_minutes = simulator.current_time - request.creation_time
            age_bonus = wait_time_minutes * REQUEST_AGE_PRIORITY_WEIGHT
            priority_bonus = (request.priority - 1) * REQUEST_PRIORITY_WEIGHT

            cost = time_to_pickup
            cost -= age_bonus
            cost -= priority_bonus
            cost += future_risk_cost  # Adiciona penalidade de risco futuro

            if request.environmental_preference and vehicle.motor == Motor.COMBUSTION:
                cost += ENVIRONMENTAL_PREFERENCE_PENALTY

            if request.passenger_capacity < vehicle.passenger_capacity:
                cost += PER_UNUSED_PASSENGER_SEAT_PENALTY * (
                    vehicle.passenger_capacity - request.passenger_capacity
                )

            cost_matrix[i, j] = cost

    if np.all(cost_matrix == float("inf")):
        return

    # Executa SA com current_time para cálculo correto de backlog
    final_assignment_indices = simulated_annealing_solver(simulator, cost_matrix, pending_requests)

    assignments_to_make = []
    for v_idx, r_idx in enumerate(final_assignment_indices):
        if r_idx != -1:
            vehicle = available_vehicles[v_idx]
            request = pending_requests[r_idx]
            assignments_to_make.append((vehicle, request))

    for vehicle, request in assignments_to_make:
        if request in simulator.requests and vehicle.condition == VehicleCondition.AVAILABLE:
            assign_request_to_vehicle(simulator, request, vehicle)


def assign_request_to_vehicle(simulator: "Simulator", request: Request, v: Vehicle):
    if request in simulator.requests:
        simulator.requests.remove(request)

    simulator.requests_to_pickup.append(request)
    v.request = request
    v.condition = VehicleCondition.ON_WAY_TO_CLIENT

    print(
        f"[Assignment SA] {v.id} aceitou {request.id} (Prio: {request.priority}). "
        f"Dist: {v.remaining_km:.1f}km."
    )

    path_info = find_a_star_route(simulator.map, v.position_node, request.start_node)
    path = None
    if path_info:
        path, time, distance = path_info

    if path:
        v.current_route = path
        v.current_segment_index = 0
        v.current_segment_progress_time = 0.0
    else:
        print(f"[ERROR] Caminho falhou pós-atribuição.")
        v.request = None
        v.condition = VehicleCondition.AVAILABLE
        if request in simulator.requests_to_pickup:
            simulator.requests_to_pickup.remove(request)
        simulator.requests.append(request)


def generate_new_requests_if_needed(simulator: "Simulator"):
    from mapGen import generate_random_request

    total_active_requests = (
        len(simulator.requests)
        + len(simulator.requests_to_pickup)
        + len(simulator.requests_to_dropoff)
    )

    num_vehicles = len(simulator.vehicles)
    min_pending_requests = max(2, int(num_vehicles / 3))

    total_is_low = total_active_requests < simulator.NUM_INITIAL_REQUESTS
    pending_is_low = len(simulator.requests) < min_pending_requests

    if total_is_low or pending_is_low:
        num_to_gen = simulator.NUM_REQUESTS_TO_GENERATE
        for _ in range(num_to_gen):
            simulator.requests.append(
                generate_random_request(
                    simulator.map, list(simulator.map.nos), simulator.current_time
                )
            )
