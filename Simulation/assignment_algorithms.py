import random
import math
import numpy as np
from typing import List, Set, Optional, Tuple, TYPE_CHECKING
from models.request import Request
from Simulation.simulation_config import PlanningConfig

if TYPE_CHECKING:
    from Simulation.simulator import Simulator


class SAState:
    """
    Simples classe para guardar o estado da solução (atribuição e backlog).
    """
    def __init__(self, assignment: List[int], backlog: Set[int]):
        self.assignment = assignment
        self.backlog = backlog

    def copy(self):
        return SAState(self.assignment.copy(), self.backlog.copy())


def _calculate_backlog_penalty(request: Request, current_time: float) -> float:
    """
    Calcula quanto nos custa deixar este pedido pendurado no backlog.
    Leva em conta a prioridade e há quanto tempo ele está à espera.
    """
    age = max(0, current_time - request.creation_time)

    # A prioridade pesa bastante (ao quadrado)
    priority_cost = (request.priority**2) * PlanningConfig.WEIGHT_PRIORITY
    
    # O tempo de espera também chateia, por isso penalizamos
    age_cost = age * PlanningConfig.WEIGHT_AGE * 2.0

    return PlanningConfig.BACKLOG_BASE_PENALTY + priority_cost + age_cost


def calculate_total_system_energy(
    state: SAState,
    cost_matrix: np.ndarray,
    requests: List[Request],
    current_time: float,
) -> float:
    """
    Função de custo (energia total). Queremos minimizar isto.
    Soma o custo das viagens dos veículos + penalizações do backlog.
    """
    total_energy = 0.0

    # Custo das atribuições atuais (quem vai buscar quem)
    for vehicle_idx, request_idx in enumerate(state.assignment):
        if request_idx != -1:
            cost = cost_matrix[vehicle_idx, request_idx]
            # Se for impossível (infinito), aborta logo
            if cost == float("inf"):
                return float("inf")
            total_energy += cost

    # Penalização por quem ficou de fora (backlog)
    for request_idx in state.backlog:
        req = requests[request_idx]
        total_energy += _calculate_backlog_penalty(req, current_time)

    return total_energy


def get_neighbor(
    state: SAState, num_vehicles: int, cost_matrix: np.ndarray, requests: List[Request]
) -> SAState:
    """
    Gera um vizinho próximo da solução atual.
    Tenta fazer pequenas mudanças: trocar, mover, substituir, etc.
    """
    for _ in range(3):  # Tentar 3x gerar válido
        new_state = state.copy()
        
        # Vamos decidir o que fazer com base num número aleatório
        prob = random.random()

        # Identificar quem está ocupado e quem está livre
        busy_vehicles = [i for i, r in enumerate(new_state.assignment) if r != -1]
        free_vehicles = [i for i, r in enumerate(new_state.assignment) if r == -1]

        # OP 1: SWAP (25%)
        if prob < 0.25 and len(busy_vehicles) >= 2:
            v1, v2 = random.sample(busy_vehicles, 2)
            # Troca simples
            new_state.assignment[v1], new_state.assignment[v2] = (
                new_state.assignment[v2],
                new_state.assignment[v1],
            )
            return new_state

        # OP 2: MOVE (Passar um pedido de um veículo para outro livre) (25%)
        elif prob < 0.50 and busy_vehicles and free_vehicles:
            src_vehicle = random.choice(busy_vehicles)
            dst_vehicle = random.choice(free_vehicles)
            
            request_idx = new_state.assignment[src_vehicle]
            
            # Só movemos se o destino conseguir fazer o pedido
            if cost_matrix[dst_vehicle, request_idx] != float("inf"):
                new_state.assignment[dst_vehicle] = request_idx
                new_state.assignment[src_vehicle] = -1
                return new_state

        # OP 3: REPLACE (Trocar um pedido atribuído por um do backlog) (30%)
        elif prob < 0.80 and busy_vehicles and new_state.backlog:
            vehicle_idx = random.choice(busy_vehicles)
            new_req_idx = random.choice(list(new_state.backlog))
            old_req_idx = new_state.assignment[vehicle_idx]
            
            if cost_matrix[vehicle_idx, new_req_idx] != float("inf"):
                new_state.assignment[vehicle_idx] = new_req_idx
                new_state.backlog.remove(new_req_idx)
                new_state.backlog.add(old_req_idx)
                return new_state

        # OP 4: ADD (Atribuir um pedido do backlog a um veículo livre) (15%)
        elif free_vehicles and new_state.backlog:
            vehicle_idx = random.choice(free_vehicles)
            req_idx = random.choice(list(new_state.backlog))
            
            if cost_matrix[vehicle_idx, req_idx] != float("inf"):
                new_state.assignment[vehicle_idx] = req_idx
                new_state.backlog.remove(req_idx)
                return new_state

        # OP 5: REMOVE (Remover um pedido e mandar para o backlog) (5%)
        elif busy_vehicles:
            # Só removemos se o backlog não estiver gigante
            if len(new_state.backlog) < num_vehicles * 3:
                vehicle_idx = random.choice(busy_vehicles)
                req_idx = new_state.assignment[vehicle_idx]
                
                # Proteção para pedidos VIP: é difícil removê-los (só 10% de chance)
                is_vip = requests[req_idx].priority >= 4
                if not is_vip or random.random() < 0.1:
                    new_state.assignment[vehicle_idx] = -1
                    new_state.backlog.add(req_idx)
                    return new_state

    # Se não conseguimos gerar nada válido, devolvemos o original
    return state


def simulated_annealing_solver(
    simulator: "Simulator",
    cost_matrix: np.ndarray,
    requests: List[Request],
    initial_temp: float = 200.0,
) -> List[int]:
    """
    O nosso "cavalo de batalha". Usa Simulated Annealing para encontrar uma boa distribuição
    de pedidos pelos veículos.
    """
    num_vehicles = cost_matrix.shape[0]
    num_requests = cost_matrix.shape[1]

    # Solução Inicial (Greedy Estocástico)
    # Começamos com tudo vazio e tentamos preencher de forma inteligente
    assignment = [-1] * num_vehicles
    backlog = set(range(num_requests))

    # Ordenamos pedidos por prioridade para tentar atender os VIPs primeiro
    sorted_requests = sorted(
        range(num_requests), key=lambda i: requests[i].priority, reverse=True
    )

    for req_idx in sorted_requests:
        # Quem pode levar este pedido?
        candidates = []
        for v_idx in range(num_vehicles):
            # Se o veículo está livre e consegue chegar lá
            if assignment[v_idx] == -1 and cost_matrix[v_idx, req_idx] != float("inf"):
                candidates.append(v_idx)

        if candidates:
            # Escolhemos o melhor candidato (menor custo) na maioria das vezes (80%)
            # Mas às vezes (20%) escolhemos um aleatório para dar variedade
            best_candidate = min(candidates, key=lambda v: cost_matrix[v, req_idx])
            
            if random.random() < 0.8:
                chosen_vehicle = best_candidate
            else:
                chosen_vehicle = random.choice(candidates)

            assignment[chosen_vehicle] = req_idx
            backlog.remove(req_idx)

    # Configuração inicial do SA
    current_state = SAState(assignment, backlog)
    current_energy = calculate_total_system_energy(
        current_state, cost_matrix, requests, simulator.current_time
    )

    best_state = current_state.copy()
    best_energy = current_energy

    # Parâmetros do recozimento
    temperature = initial_temp
    cooling_rate = 0.96
    max_iterations = 1200
    stagnation_limit = 200
    stagnation_counter = 0

    # Loop Principal
    for _ in range(max_iterations):
        # Gerar vizinho
        neighbor = get_neighbor(current_state, num_vehicles, cost_matrix, requests)
        neighbor_energy = calculate_total_system_energy(
            neighbor, cost_matrix, requests, simulator.current_time
        )

        # Se for inválido, ignora
        if neighbor_energy == float("inf"):
            continue

        delta = neighbor_energy - current_energy

        # Aceitamos se for melhor OU se a temperatura permitir (critério de Metropolis)
        should_accept = False
        if delta <= 0:
            should_accept = True
        else:
            # Probabilidade de aceitar piora diminui com a temperatura
            if temperature > 0.01:
                probability = math.exp(-delta / temperature)
                if random.random() < probability:
                    should_accept = True

        if should_accept:
            current_state = neighbor
            current_energy = neighbor_energy
            
            # Atualiza o melhor global se encontrarmos
            if current_energy < best_energy:
                best_state = current_state.copy()
                best_energy = current_energy
                stagnation_counter = 0
            else:
                stagnation_counter += 1
        else:
            stagnation_counter += 1

        # Reaquecimento se ficarmos presos muito tempo
        if stagnation_counter > stagnation_limit:
            temperature = min(temperature * 1.8, initial_temp)
            stagnation_counter = 0
            # Voltamos ao melhor conhecido para não nos perdermos
            current_state = best_state.copy()

        # Arrefecimento
        temperature = max(temperature * cooling_rate, 0.05)

    return best_state.assignment


def greedy_solver(
    simulator: "Simulator",
    cost_matrix: np.ndarray,
    requests: List[Request],
) -> List[int]:
    """
    Abordagem sôfrega (Greedy).
    Simplesmente olha para todas as combinações possíveis e vai escolhendo
    as mais baratas até não dar mais. Rápido, mas nem sempre ótimo.
    """
    num_vehicles = cost_matrix.shape[0]
    num_requests = cost_matrix.shape[1]

    assignment = [-1] * num_vehicles
    assigned_requests = set()

    # Listar todas as possibilidades válidas (custo, veiculo, pedido)
    possible_moves = []
    for v in range(num_vehicles):
        for r in range(num_requests):
            cost = cost_matrix[v, r]
            if cost != float("inf"):
                possible_moves.append((cost, v, r))

    # Ordenar do mais barato para o mais caro
    possible_moves.sort(key=lambda x: x[0])

    # Preencher
    for _, v, r in possible_moves:
        # Se o veículo está livre E o pedido ainda não foi pego
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
    Hill Climbing Estocástico.
    É como o Simulated Annealing, mas sem a parte de aceitar soluções piores.
    Só sobe o morro (ou desce, no caso de minimizar custo).
    """
    num_vehicles = cost_matrix.shape[0]
    num_requests = cost_matrix.shape[1]

    # Inicialização Greedy (para começar bem)
    assignment = [-1] * num_vehicles
    backlog = set(range(num_requests))
    assigned_requests = set()

    # Mesma lógica do greedy_solver para o estado inicial
    possible_moves = []
    for v in range(num_vehicles):
        for r in range(num_requests):
            if cost_matrix[v, r] != float("inf"):
                possible_moves.append((cost_matrix[v, r], v, r))
    
    possible_moves.sort(key=lambda x: x[0])

    for _, v, r in possible_moves:
        if assignment[v] == -1 and r not in assigned_requests:
            assignment[v] = r
            assigned_requests.add(r)
            backlog.remove(r)

    current_state = SAState(assignment, backlog)
    current_energy = calculate_total_system_energy(
        current_state, cost_matrix, requests, simulator.current_time
    )

    # Tenta melhorar 500 vezes
    for _ in range(500):
        neighbor = get_neighbor(current_state, num_vehicles, cost_matrix, requests)
        neighbor_energy = calculate_total_system_energy(
            neighbor, cost_matrix, requests, simulator.current_time
        )

        # Só aceita se for estritamente melhor
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
    """
    Função principal que despacha para o algoritmo escolhido.
    """
    algo_name = algorithm.lower()

    if algo_name == "greedy":
        return greedy_solver(simulator, cost_matrix, requests)
    elif algo_name == "hill climbing":
        return hill_climbing_solver(simulator, cost_matrix, requests)
    else:
        # Por defeito usamos o Simulated Annealing que é o mais robusto
        return simulated_annealing_solver(simulator, cost_matrix, requests, initial_temp)
