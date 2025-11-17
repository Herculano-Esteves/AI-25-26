import math
import random
import numpy as np
from typing import List, TYPE_CHECKING
from models.request import Request
from models.vehicle import Vehicle, VehicleCondition, Motor
from search import find_a_star_route
from mapGen import generate_random_request


if TYPE_CHECKING:
    from simulator import Simulator

ENVIRONMENTAL_PREFERENCE_PENALTY = 30.0
PER_UNUSED_PASSENGER_SEAT_PENALTY = 5.0
REQUEST_AGE_PRIORITY_WEIGHT = 0.5
REQUEST_PRIORITY_WEIGHT = 10.0


def calculate_total_cost(assignment, cost_matrix):
    """Calcula o custo total de uma configuração de atribuição."""
    total_cost = 0.0
    rows, cols = cost_matrix.shape

    for vehicle_idx, request_idx in enumerate(assignment):
        if request_idx != -1:  # Se o veículo tem um pedido atribuído
            cost = cost_matrix[vehicle_idx, request_idx]
            # Se a atribuição for inválida (infinito), penalizamos pesadamente
            if cost == float("inf"):
                total_cost += 1e9
            else:
                total_cost += cost
    return total_cost


def get_neighbor(current_assignment):
    """Gera um vizinho trocando dois elementos no vetor de atribuição."""
    neighbor = current_assignment.copy()
    n = len(neighbor)
    
    # Se tivermos menos de 2 veículos, não dá para trocar posições.
    if n < 2:
        return neighbor

    # Escolhe dois índices aleatórios para trocar
    i, j = random.sample(range(n), 2)
    
    # Realiza a troca (Swap)
    neighbor[i], neighbor[j] = neighbor[j], neighbor[i]
    
    return neighbor


def simulated_annealing_assignment(cost_matrix, max_iter=500, initial_temp=100.0, alpha=0.95):
    """
    Resolve o problema de atribuição linear usando Simulated Annealing.
    Retorna uma lista de tuplas (row_ind, col_ind).
    """
    num_vehicles, num_requests = cost_matrix.shape

    # 1. Estado Inicial
    # Criamos uma lista com o tamanho dos veículos.
    # Preenchemos com os índices dos pedidos disponíveis.
    # Se houver mais veículos que pedidos, preenchemos o resto com -1 (vazio).
    # Se houver mais pedidos que veículos, o SA atual vai ignorar os excedentes.

    current_assignment = [-1] * num_vehicles

    # Lista de pedidos a distribuir (0 a num_requests-1)
    # Nota: Se num_requests > num_vehicles, pegamos apenas os primeiros (limitação simples)
    # ou expandimos o array para permitir permutações completas.
    # Para simplificar: assumimos que permutamos os slots disponíveis nos veículos.
    available_request_indices = list(range(num_requests))

    # Se houver mais pedidos que veículos, infelizmente alguns ficam de fora nesta iteração
    # O Simulated Annealing vai tentar encontrar a melhor combinação dos que cabem.
    requests_to_fit = available_request_indices[:num_vehicles]

    for i, req_idx in enumerate(requests_to_fit):
        current_assignment[i] = req_idx

    # Randomizar estado inicial
    random.shuffle(current_assignment)

    current_cost = calculate_total_cost(current_assignment, cost_matrix)

    best_assignment = current_assignment.copy()
    best_cost = current_cost

    temperature = initial_temp

    # 2. Loop de Otimização
    for i in range(max_iter):
        neighbor = get_neighbor(current_assignment)
        neighbor_cost = calculate_total_cost(neighbor, cost_matrix)

        delta = neighbor_cost - current_cost

        # Critério de Aceitação
        acceptance_prob = 0.0
        if delta < 0:
            acceptance_prob = 1.0
        else:
            # Evitar overflow se T for muito baixo
            if temperature > 1e-5:
                acceptance_prob = math.exp(-delta / temperature)
            else:
                acceptance_prob = 0.0

        if random.random() < acceptance_prob:
            current_assignment = neighbor
            current_cost = neighbor_cost

            if current_cost < best_cost:
                best_assignment = current_assignment.copy()
                best_cost = current_cost

        # Resfriamento
        temperature *= alpha

    # 3. Formatar saída para corresponder ao formato esperado (row_ind, col_ind)
    row_ind = []
    col_ind = []

    for v_idx, r_idx in enumerate(best_assignment):
        if r_idx != -1:
            # Verificar se o custo não é infinito (atribuição impossível)
            if cost_matrix[v_idx, r_idx] != float("inf"):
                row_ind.append(v_idx)
                col_ind.append(r_idx)

    return row_ind, col_ind



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

    # Build the full Cost Matrix
    num_vehicles = len(available_vehicles)
    num_requests = len(pending_requests)
    cost_matrix = np.full((num_vehicles, num_requests), float("inf"))

    for i in range(num_vehicles):
        vehicle = available_vehicles[i]
        for j in range(num_requests):
            request = pending_requests[j]

            if vehicle.passenger_capacity < request.passenger_capacity:
                continue

            path_info = find_a_star_route(simulator.map, vehicle.position_node, request.start_node)
            if path_info:
                _, time, dist_to_client = path_info

                dist_to_refuel = float("inf")
                if vehicle.motor == Motor.ELECTRIC:
                    dist_to_refuel = request.nearest_ev_station_distance
                else:
                    dist_to_refuel = request.nearest_gas_station_distance

                if dist_to_refuel == float("inf"):
                    continue

                total_distance_needed = dist_to_client + request.path_distance + dist_to_refuel

                if vehicle.remaining_km < total_distance_needed:
                    continue

                wait_time_minutes = simulator.current_time - request.creation_time
                age_bonus = wait_time_minutes * REQUEST_AGE_PRIORITY_WEIGHT
                priority_bonus = (request.priority - 1) * REQUEST_PRIORITY_WEIGHT

                # Custo base é o tempo
                cost = time - age_bonus - priority_bonus

                if request.environmental_preference and vehicle.motor == Motor.COMBUSTION:
                    cost += ENVIRONMENTAL_PREFERENCE_PENALTY

                if request.passenger_capacity < vehicle.passenger_capacity:
                    cost += PER_UNUSED_PASSENGER_SEAT_PENALTY * (
                        vehicle.passenger_capacity - request.passenger_capacity
                    )

                cost_matrix[i, j] = cost

# Verificar se a matriz tem alguma solução viável
    if np.all(cost_matrix == float("inf")):
        return
    
    # O Simulated Annealing precisa de pelo menos 2 para fazer trocas.
    # Se só há 1, fazemos uma escolha simples (Gulosa) do melhor pedido para ele.
    if num_vehicles == 1:
        # Pega a linha de custos do único veículo
        costs = cost_matrix[0] 
        # Encontra o índice do menor custo (argmin)
        best_req_idx = np.argmin(costs)
        
        # Se o custo for infinito, não faz nada
        if costs[best_req_idx] == float("inf"):
            return

        assignments_to_make = [(available_vehicles[0], pending_requests[best_req_idx])]
    
    else:
        vehicle_indices, request_indices = simulated_annealing_assignment(
            cost_matrix, 
            max_iter=500, 
            initial_temp=50.0, 
            alpha=0.90
        )

        assignments_to_make = []
        for v_id, r_id in zip(vehicle_indices, request_indices):
            cost = cost_matrix[v_id, r_id]
            if cost == float("inf"):
                continue

            vehicle = available_vehicles[v_id]
            request = pending_requests[r_id]
            assignments_to_make.append((vehicle, request))

    # Aplicar as atribuições
    for vehicle, request in assignments_to_make:
        if request in simulator.requests and vehicle.condition == VehicleCondition.AVAILABLE:
            assign_request_to_vehicle(simulator, request, vehicle)


def assign_request_to_vehicle(simulator: "Simulator", request: Request, v: Vehicle):
    simulator.requests.remove(request)
    simulator.requests_to_pickup.append(request)
    v.request = request
    v.condition = VehicleCondition.ON_WAY_TO_CLIENT

    print(
        f"[Assignment] {v.id} aceitou {request.id}."
        f"A caminho de {request.start_node.position}."
        f"Preferencia ambiental: {request.environmental_preference}"
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
        print(f"[ERROR] Não foi possivel encontrar caminho {v.id} para {request.id}.")
        v.request = None
        v.condition = VehicleCondition.AVAILABLE
        simulator.requests_to_pickup.remove(request)
        simulator.requests.append(request)


def generate_new_requests_if_needed(simulator: "Simulator"):
    total_active_requests = (
        len(simulator.requests)
        + len(simulator.requests_to_pickup)
        + len(simulator.requests_to_dropoff)
    )

    # Right now create requests by hand
    num_vehicles = len(simulator.vehicles)
    min_pending_requests = max(2, int(num_vehicles / 3))
    total_is_low = total_active_requests < simulator.NUM_INITIAL_REQUESTS
    pending_is_low = len(simulator.requests) < min_pending_requests

    if total_is_low or pending_is_low:
        num_to_gen = simulator.NUM_REQUESTS_TO_GENERATE
        print(
            f"[Simulation] Criados {num_to_gen} novos pedidos. " f"(Total: {total_active_requests})"
        )
        for _ in range(num_to_gen):
            simulator.requests.append(
                generate_random_request(
                    simulator.map, list(simulator.map.nos), simulator.current_time
                )
            )
