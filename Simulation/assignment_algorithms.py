import random
import math
import numpy as np
from typing import List, Set, Optional, Tuple, TYPE_CHECKING
from models.request import Request
from Simulation.simulation_config import PlanningConfig

if TYPE_CHECKING:
    from Simulation.simulator import Simulator


class SAState:
    def __init__(self, assignment: List[int], backlog: Set[int]):
        self.assignment = assignment
        self.backlog = backlog

    def copy(self):
        return SAState(self.assignment.copy(), self.backlog.copy())


def _calculate_backlog_penalty(request: Request, current_time: float) -> float:
    """Calcula a penalização por deixar um pedido no backlog."""
    age = max(0, current_time - request.creation_time)

    prio_cost = (request.priority**2) * PlanningConfig.WEIGHT_PRIORITY
    age_cost = age * PlanningConfig.WEIGHT_AGE * 2.0  # Age pesa no backlog

    return PlanningConfig.BACKLOG_BASE_PENALTY + prio_cost + age_cost


def calculate_total_system_energy(
    state: SAState,
    cost_matrix: np.ndarray,
    requests: List[Request],
    current_time: float,
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
        total_energy += _calculate_backlog_penalty(req, current_time)

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
) -> List[int]:
    num_vehicles = cost_matrix.shape[0]
    num_requests = cost_matrix.shape[1]

    # Inicialização Estocástia
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

        if stagnation_counter > 200:
            temp = min(temp * 1.8, initial_temp)
            stagnation_counter = 0
            current_state = best_state.copy()

        temp = max(temp * alpha, 0.05)

    return best_state.assignment


def greedy_solver(
    simulator: "Simulator",
    cost_matrix: np.ndarray,
    requests: List[Request],
) -> List[int]:
    """
    Atribui pedidos aos veículos de forma sôfrega (Greedy).
    Para cada veículo (ordem aleatória ou fixa), escolhe o melhor pedido disponível.
    """
    num_vehicles = cost_matrix.shape[0]
    num_requests = cost_matrix.shape[1]

    assignment = [-1] * num_vehicles
    assigned_requests = set()

    # Ordenar veículos pode influenciar, vamos fazer por ordem de índice para simplicidade
    # Ou podíamos ordenar atribuições possíveis por custo global.

    # Abordagem: Listar todas as arestas (v, r) válidas, ordenar por custo e preencher.
    possible_assignments = []
    for v in range(num_vehicles):
        for r in range(num_requests):
            cost = cost_matrix[v, r]
            if cost != float("inf"):
                possible_assignments.append((cost, v, r))

    # Ordena por menor custo
    possible_assignments.sort(key=lambda x: x[0])

    for cost, v, r in possible_assignments:
        if assignment[v] == -1 and r not in assigned_requests:
            assignment[v] = r
            assigned_requests.add(r)

    return assignment


def hill_climbing_solver(
    simulator: "Simulator",
    cost_matrix: np.ndarray,
    requests: List[Request],
) -> List[int]:
    """
    Hill Climbing (Stochastic).
    Semelhante ao SA, mas só aceita melhorias estritas.
    """
    num_vehicles = cost_matrix.shape[0]
    num_requests = cost_matrix.shape[1]

    # Inicialização (Mesma lógica do SA para ter um bom ponto de partida)
    assign = [-1] * num_vehicles
    backlog = set(range(num_requests))

    # Greedy Initialization
    possible_assignments = []
    for v in range(num_vehicles):
        for r in range(num_requests):
            if cost_matrix[v, r] != float("inf"):
                possible_assignments.append((cost_matrix[v, r], v, r))
    possible_assignments.sort(key=lambda x: x[0])

    assigned_reqs = set()
    for _, v, r in possible_assignments:
        if assign[v] == -1 and r not in assigned_reqs:
            assign[v] = r
            assigned_reqs.add(r)
            backlog.remove(r)

    current_state = SAState(assign, backlog)
    current_energy = calculate_total_system_energy(
        current_state, cost_matrix, requests, simulator.current_time
    )

    MAX_ITER = 500

    for _ in range(MAX_ITER):
        neighbor = get_neighbor(current_state, num_vehicles, cost_matrix, requests)
        neighbor_energy = calculate_total_system_energy(
            neighbor, cost_matrix, requests, simulator.current_time
        )

        if neighbor_energy < current_energy:
            current_state = neighbor
            current_energy = neighbor_energy

    return current_state.assignment


def solve_assignment(
    algorithm: str,
    simulator: "Simulator",
    cost_matrix: np.ndarray,
    requests: List[Request],
    initial_temp: float = 200.0,
) -> List[int]:
    algo = algorithm.lower()

    if algo == "greedy":
        return greedy_solver(simulator, cost_matrix, requests)
    elif algo == "hill climbing":
        return hill_climbing_solver(simulator, cost_matrix, requests)
    else:
        # Default to SA
        return simulated_annealing_solver(simulator, cost_matrix, requests, initial_temp)
