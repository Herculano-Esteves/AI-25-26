import random
import math
import numpy as np
from typing import List, Set, TYPE_CHECKING
from models.request import Request
from Simulation.simulation_config import PlanningConfig

if TYPE_CHECKING:
    from Simulation.simulator import Simulator


class SAState:
    """Estado da solução: atribuição veículo→pedido e backlog."""

    def __init__(self, assignment: List[int], backlog: Set[int]):
        self.assignment = assignment
        self.backlog = backlog

    def copy(self):
        return SAState(self.assignment.copy(), self.backlog.copy())


def _backlog_penalty(request: Request, current_time: float) -> float:
    """Custo de deixar um pedido no backlog (prioridade + tempo de espera)."""
    age = max(0, current_time - request.creation_time)
    priority_cost = (request.priority**2) * PlanningConfig.WEIGHT_PRIORITY
    age_cost = age * PlanningConfig.WEIGHT_AGE * 2.0
    return PlanningConfig.BACKLOG_BASE_PENALTY + priority_cost + age_cost


def calculate_total_energy(
    state: SAState, cost_matrix: np.ndarray, requests: List[Request], current_time: float
) -> float:
    """Função de custo total: soma dos custos de viagem + penalizações do backlog."""
    total = 0.0

    for v_idx, r_idx in enumerate(state.assignment):
        if r_idx != -1:
            cost = cost_matrix[v_idx, r_idx]
            if cost == float("inf"):
                return float("inf")
            total += cost

    for r_idx in state.backlog:
        total += _backlog_penalty(requests[r_idx], current_time)

    return total


def get_neighbor(
    state: SAState, num_vehicles: int, cost_matrix: np.ndarray, requests: List[Request]
) -> SAState:
    """Gera vizinho: swap, move, replace, add ou remove."""
    for _ in range(3):
        new = state.copy()
        prob = random.random()

        busy = [i for i, r in enumerate(new.assignment) if r != -1]
        free = [i for i, r in enumerate(new.assignment) if r == -1]

        # SWAP (25%)
        if prob < 0.25 and len(busy) >= 2:
            v1, v2 = random.sample(busy, 2)
            new.assignment[v1], new.assignment[v2] = new.assignment[v2], new.assignment[v1]
            return new

        # MOVE para veículo livre (25%)
        elif prob < 0.50 and busy and free:
            src, dst = random.choice(busy), random.choice(free)
            r_idx = new.assignment[src]
            if cost_matrix[dst, r_idx] != float("inf"):
                new.assignment[dst] = r_idx
                new.assignment[src] = -1
                return new

        # REPLACE com pedido do backlog (30%)
        elif prob < 0.80 and busy and new.backlog:
            v_idx = random.choice(busy)
            new_r = random.choice(list(new.backlog))
            old_r = new.assignment[v_idx]
            if cost_matrix[v_idx, new_r] != float("inf"):
                new.assignment[v_idx] = new_r
                new.backlog.remove(new_r)
                new.backlog.add(old_r)
                return new

        # ADD do backlog (15%)
        elif free and new.backlog:
            v_idx = random.choice(free)
            r_idx = random.choice(list(new.backlog))
            if cost_matrix[v_idx, r_idx] != float("inf"):
                new.assignment[v_idx] = r_idx
                new.backlog.remove(r_idx)
                return new

        # REMOVE para backlog (5%)
        elif busy and len(new.backlog) < num_vehicles * 3:
            v_idx = random.choice(busy)
            r_idx = new.assignment[v_idx]
            # Pedidos VIP são mais difíceis de remover
            is_vip = requests[r_idx].priority >= 4
            if not is_vip or random.random() < 0.1:
                new.assignment[v_idx] = -1
                new.backlog.add(r_idx)
                return new

    return state


def simulated_annealing_solver(
    simulator: "Simulator",
    cost_matrix: np.ndarray,
    requests: List[Request],
    initial_temp: float = 200.0,
) -> List[int]:
    """Simulated Annealing para atribuição de pedidos a veículos."""
    n_vehicles = cost_matrix.shape[0]
    n_requests = cost_matrix.shape[1]

    # Solução inicial
    assignment = [-1] * n_vehicles
    backlog = set(range(n_requests))

    sorted_reqs = sorted(range(n_requests), key=lambda i: requests[i].priority, reverse=True)
    for r_idx in sorted_reqs:
        candidates = [
            v
            for v in range(n_vehicles)
            if assignment[v] == -1 and cost_matrix[v, r_idx] != float("inf")
        ]
        if candidates:
            best = min(candidates, key=lambda v: cost_matrix[v, r_idx])
            chosen = best if random.random() < 0.8 else random.choice(candidates)
            assignment[chosen] = r_idx
            backlog.remove(r_idx)

    current = SAState(assignment, backlog)
    current_energy = calculate_total_energy(current, cost_matrix, requests, simulator.current_time)
    best, best_energy = current.copy(), current_energy

    temp = initial_temp
    cooling = 0.96
    stagnation = 0
    max_iterations = 1200

    for _ in range(max_iterations):
        neighbor = get_neighbor(current, n_vehicles, cost_matrix, requests)
        neighbor_energy = calculate_total_energy(
            neighbor, cost_matrix, requests, simulator.current_time
        )

        if neighbor_energy == float("inf"):
            continue

        delta = neighbor_energy - current_energy

        # Critério de Metropolis
        accept = delta <= 0 or (temp > 0.01 and random.random() < math.exp(-delta / temp))

        if accept:
            current, current_energy = neighbor, neighbor_energy
            if current_energy < best_energy:
                best, best_energy = current.copy(), current_energy
                stagnation = 0
            else:
                stagnation += 1
        else:
            stagnation += 1

        # Reaquecimento se estagnar
        if stagnation > 200:
            temp = min(temp * 1.8, initial_temp)
            stagnation = 0
            current = best.copy()

        temp = max(temp * cooling, 0.05)

    return best.assignment


def greedy_solver(
    simulator: "Simulator", cost_matrix: np.ndarray, requests: List[Request]
) -> List[int]:
    """Greedy: escolhe sempre a atribuição mais barata disponível."""
    n_vehicles, n_requests = cost_matrix.shape

    assignment = [-1] * n_vehicles
    assigned = set()

    # Ordenar por custo crescente
    moves = [
        (cost_matrix[v, r], v, r)
        for v in range(n_vehicles)
        for r in range(n_requests)
        if cost_matrix[v, r] != float("inf")
    ]
    moves.sort()

    for _, v, r in moves:
        if assignment[v] == -1 and r not in assigned:
            assignment[v] = r
            assigned.add(r)

    return assignment


def hill_climbing_solver(
    simulator: "Simulator", cost_matrix: np.ndarray, requests: List[Request]
) -> List[int]:
    """Hill Climbing: como SA mas só aceita melhorias."""
    n_vehicles, n_requests = cost_matrix.shape

    # Inicialização greedy
    assignment = [-1] * n_vehicles
    backlog = set(range(n_requests))
    assigned = set()

    moves = [
        (cost_matrix[v, r], v, r)
        for v in range(n_vehicles)
        for r in range(n_requests)
        if cost_matrix[v, r] != float("inf")
    ]
    moves.sort()

    for _, v, r in moves:
        if assignment[v] == -1 and r not in assigned:
            assignment[v] = r
            assigned.add(r)
            backlog.discard(r)

    current = SAState(assignment, backlog)
    current_energy = calculate_total_energy(current, cost_matrix, requests, simulator.current_time)

    for _ in range(500):
        neighbor = get_neighbor(current, n_vehicles, cost_matrix, requests)
        neighbor_energy = calculate_total_energy(
            neighbor, cost_matrix, requests, simulator.current_time
        )
        if neighbor_energy < current_energy:
            current, current_energy = neighbor, neighbor_energy

    return current.assignment


def solve_assignment(
    algorithm: str,
    simulator: "Simulator",
    cost_matrix: np.ndarray,
    requests: List[Request],
    initial_temp: float = 250.0,
) -> List[int]:
    """Despacha para o algoritmo escolhido."""
    name = algorithm.lower()
    if name == "greedy":
        return greedy_solver(simulator, cost_matrix, requests)
    elif name == "hill climbing":
        return hill_climbing_solver(simulator, cost_matrix, requests)
    else:
        return simulated_annealing_solver(simulator, cost_matrix, requests, initial_temp)
