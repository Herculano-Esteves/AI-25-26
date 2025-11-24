from typing import List, TYPE_CHECKING, Tuple, Set, Optional
from models.request import Request
from models.vehicle import Vehicle, VehicleCondition, Motor
from search_algorithms import find_route, _heuristic_distance, haversine_km, calculate_time_minutes
from models.node import Node
import random
import math
import numpy as np

if TYPE_CHECKING:
    from simulator import Simulator


BASE_TIMEOUT_MINUTES = 30.0
TIMEOUT_REDUCTION_PER_PRIORITY = 5.0
CANCELLATION_PENALTY_EUR = 3.0  # Fee for client lost

from Simulation.simulation_config import PlanningConfig
from Simulation.assignment_algorithms import solve_assignment

# Configuração do Algoritmo de Procura (Routing)
# Opções: 'astar', 'bfs', 'greedy'
_selected_algorithm = "astar"

# Configuração do Algoritmo de Atribuição (Assignment)
# Opções: 'simulated annealing', 'greedy', 'hill climbing'
_selected_assignment_algorithm = "simulated annealing"

# Configuração do Algoritmo de Estimativa de Custo (Assignment Cost)
# Opções: 'heuristic', 'astar'
_selected_cost_estimation_algorithm = "heuristic"


def get_selected_algorithm() -> str:
    return _selected_algorithm


def set_selected_algorithm(algo: str):
    global _selected_algorithm
    _selected_algorithm = algo
    print(f"[Config] Algoritmo de rota alterado para: {algo}")


def get_selected_assignment_algorithm() -> str:
    return _selected_assignment_algorithm


def set_selected_assignment_algorithm(algo: str):
    global _selected_assignment_algorithm
    _selected_assignment_algorithm = algo
    print(f"[Config] Algoritmo de atribuição alterado para: {algo}")


def get_selected_cost_estimation_algorithm() -> str:
    return _selected_cost_estimation_algorithm


def set_selected_cost_estimation_algorithm(algo: str):
    global _selected_cost_estimation_algorithm
    _selected_cost_estimation_algorithm = algo
    print(f"[Config] Algoritmo de estimativa de custo alterado para: {algo}")


def estimate_route_info(
    start_node: Node, end_node: Node, average_speed_kmh: float = 50.0
) -> Tuple[List[Node], float, float]:
    """
    Estima o tempo e distância entre dois nós usando distância de Haversine
    e uma velocidade média conservadora.
    Retorna: (path_ficticio, tempo_minutos, distancia_km)
    """
    dist_km = haversine_km(
        start_node.position[0],
        start_node.position[1],
        end_node.position[0],
        end_node.position[1],
    )
    time_min = calculate_time_minutes(dist_km, average_speed_kmh)
    
    # Retornamos uma lista vazia como path, pois não calculamos a rota real
    return [], time_min, dist_km


class StrategyManager:
    @staticmethod
    def identify_hotspots(simulator: "Simulator") -> List[Node]:
        if not simulator.hotspot_manager:
            return []

        all_hotspot_nodes = set()
        for hotspot in simulator.hotspot_manager.hotspots:
            all_hotspot_nodes.update(hotspot.node_cache)

        return list(all_hotspot_nodes)

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
            stations = simulator.map.ev_stations
        else:
            stations = simulator.map.gas_stations

        if not stations:
            return float("inf")
        return min(_heuristic_distance(node, s) for s in stations)


def _calculate_base_time_cost(time_to_pickup: float) -> float:
    """Custo base associado ao tempo de viagem até ao cliente."""
    return time_to_pickup * PlanningConfig.WEIGHT_TIME


def _calculate_wait_time_bonus(request: Request, current_time: float) -> float:
    """Reduz o custo (bónus) para pedidos que estão à espera há muito tempo ou têm alta prioridade."""
    wait_time = current_time - request.creation_time
    age_bonus = wait_time * PlanningConfig.WEIGHT_AGE
    priority_bonus = (request.priority - 1) * PlanningConfig.WEIGHT_PRIORITY
    return -(age_bonus + priority_bonus)


def _calculate_environmental_penalty(vehicle: Vehicle, request: Request) -> float:
    """Penaliza veículos a combustão a fazerem pedidos ecológicos."""
    if request.environmental_preference and vehicle.motor == Motor.COMBUSTION:
        return request.path_distance * PlanningConfig.PENALTY_ENV_MISMATCH_PER_KM
    return 0.0


def _calculate_capacity_penalty(vehicle: Vehicle, request: Request) -> float:
    """Penaliza o uso de veículos grandes para poucos passageiros."""
    if vehicle.passenger_capacity > request.passenger_capacity:
        excess_capacity = vehicle.passenger_capacity - request.passenger_capacity
        return excess_capacity * PlanningConfig.PENALTY_UNUSED_SEAT
    return 0.0


def _calculate_battery_risk(remaining_km_after: float) -> float:
    """Calcula o risco associado a ficar com pouca bateria/combustível."""
    if remaining_km_after < 0:
        return float("inf")

    if remaining_km_after < PlanningConfig.BATTERY_CRITICAL_LEVEL:
        deficit = PlanningConfig.BATTERY_CRITICAL_LEVEL - remaining_km_after
        return (deficit**PlanningConfig.BATTERY_RISK_EXPONENT) * PlanningConfig.WEIGHT_BATTERY_RISK
    return 0.0


def _calculate_future_logistics_cost(
    vehicle: Vehicle,
    request: Request,
    remaining_km_after: float,
    simulator: "Simulator",
) -> float:
    """
    Calcula custos associados ao estado do veículo APÓS a entrega.
    Inclui:
    1. Viabilidade de chegar a um posto de abastecimento.
    2. Distância a um posto (custo de reabastecimento futuro).
    3. Distância a um Hotspot (custo de isolamento).
    """
    final_pos = request.end_node

    # Reabastecimento
    dist_station = StrategyManager.get_dist_to_nearest_station(final_pos, vehicle.motor, simulator)
    if dist_station > remaining_km_after:
        return float("inf")  # Stranded

    refuel_cost = dist_station * PlanningConfig.WEIGHT_FUTURE_REFUEL

    # Isolamento (Hotspots)
    dist_hotspot = StrategyManager.get_dist_to_nearest_hotspot(final_pos, simulator)
    isolation_cost = dist_hotspot * PlanningConfig.WEIGHT_ISOLATION

    return refuel_cost + isolation_cost


def _calculate_opportunity_cost(
    vehicle: Vehicle, request: Request, has_eco_in_backlog: bool
) -> float:
    """
    Penaliza EVs por fazerem pedidos não-ecológicos quando há pedidos ecológicos à espera.
    A penalização é menor se o EV estiver com pouca bateria (precisa de trabalhar onde der).
    """
    if vehicle.motor == Motor.ELECTRIC and not request.environmental_preference:
        if has_eco_in_backlog:
            safe_range = vehicle.max_km * 0.6
            battery_factor = min(1.0, vehicle.remaining_km / safe_range)
            return PlanningConfig.WEIGHT_LOST_OPPORTUNITY * battery_factor
    return 0.0


def _calculate_profit_adjustment(
    vehicle: Vehicle, request: Request, dist_to_pickup: float
) -> float:
    """
    Ajusta o custo com base no lucro projetado.
    Maior lucro = Menor custo (valor negativo retornado).
    """
    operational_cost = (dist_to_pickup + request.path_distance) * vehicle.price_per_km
    projected_profit = request.price - operational_cost

    # Subtraímos o lucro (multiplicado pelo peso) ao custo total
    return -(projected_profit * PlanningConfig.WEIGHT_PROFIT)


def calculate_detailed_cost(
    vehicle: Vehicle,
    request: Request,
    path_info: Tuple[list, float, float],
    simulator: "Simulator",
    has_eco_in_backlog: bool,
) -> float:
    """
    Calcula o custo total de uma atribuição, agregando vários componentes de custo.
    """
    _, time_to_pickup, dist_to_pickup = path_info

    # Custos Base e Bónus
    cost = _calculate_base_time_cost(time_to_pickup)
    cost += _calculate_wait_time_bonus(request, simulator.current_time)

    # Penalizações de Compatibilidade
    cost += _calculate_environmental_penalty(vehicle, request)
    cost += _calculate_capacity_penalty(vehicle, request)

    # Verificação de Autonomia e Risco
    total_trip_dist = dist_to_pickup + request.path_distance
    remaining_km_after = vehicle.remaining_km - total_trip_dist

    battery_risk = _calculate_battery_risk(remaining_km_after)
    if battery_risk == float("inf"):
        return float("inf")
    cost += battery_risk

    # Logística Futura (Pós-Entrega)
    future_cost = _calculate_future_logistics_cost(vehicle, request, remaining_km_after, simulator)
    if future_cost == float("inf"):
        return float("inf")
    cost += future_cost

    # Custo de Oportunidade
    cost += _calculate_opportunity_cost(vehicle, request, has_eco_in_backlog)

    # Otimização de Lucro
    cost += _calculate_profit_adjustment(vehicle, request, dist_to_pickup)

    return cost


def check_timeouts(simulator: "Simulator"):
    """
    Verifica se algum pedido na fila excedeu o tempo máximo de espera.
    Prio 1: 30 min
    Prio 5: 10 min
    """
    for i in range(len(simulator.requests) - 1, -1, -1):
        req = simulator.requests[i]
        age = simulator.current_time - req.creation_time

        # Fórmula: Prio 1 -> 30m, Prio 5 -> 10m
        # (req.priority - 1) * 5 => P1=0, P5=20
        # Limit: 30 - 0 = 30, 30 - 20 = 10
        limit = BASE_TIMEOUT_MINUTES - ((req.priority - 1) * TIMEOUT_REDUCTION_PER_PRIORITY)

        if age > limit:
            print(
                f"[Timeout] Pedido {req.id} (Prio {req.priority}) cancelado! Esperou {age:.1f} min > {limit} min."
            )

            simulator.requests.pop(i)

            simulator.stats.step_requests_cancelled_timeout += 1
            simulator.stats.step_operational_cost += CANCELLATION_PENALTY_EUR
            simulator.stats.total_requests_failed += 1


def assign_pending_requests(simulator: "Simulator"):
    simulator.assignment_needed = False

    # Gather all requests that need assignment
    pending_requests = list(simulator.requests)

    # Gather available vehicles AND vehicles on the way to pickup
    available_vehicles = []

    # Vehicles that are completely free
    free_vehicles = [
        v
        for v in simulator.vehicles
        if v.condition == VehicleCondition.AVAILABLE
        and v.remaining_km >= simulator.LOW_AUTONOMY_THRESHOLD
    ]
    available_vehicles.extend(free_vehicles)

    # Vehicles that are busy but can be redirected
    redirectable_vehicles = [
        v
        for v in simulator.vehicles
        if v.condition == VehicleCondition.ON_WAY_TO_CLIENT
        and v.remaining_km >= simulator.LOW_AUTONOMY_THRESHOLD
    ]
    available_vehicles.extend(redirectable_vehicles)

    # Add the requests from redirectable vehicles to the pool
    for v in redirectable_vehicles:
        if v.request:
            if v.request not in pending_requests:
                pending_requests.append(v.request)

    if not pending_requests or not available_vehicles:
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

            # Pathfinding (A*) or Heuristic
            path_info = None
            
            if get_selected_cost_estimation_algorithm() == "heuristic":
                path_info = estimate_route_info(v.position_node, req.start_node)
            else:
                # Fallback to full A*
                path_info = find_route(
                    get_selected_algorithm(),
                    simulator.map,
                    v.position_node,
                    req.start_node,
                    current_time=simulator.current_time,
                    traffic_manager=simulator.traffic_manager,
                )

            if not path_info:
                continue

            # Cálculo de Custo Estratégico
            cost = calculate_detailed_cost(v, req, path_info, simulator, has_eco)

            # Small bonus for keeping the same assignment to avoid jitter
            if v.request == req:
                cost -= 5.0

            cost_matrix[i, j] = cost

    if np.all(cost_matrix == float("inf")):
        return

    # Configuração Dinâmica, reheat inicial se houver VIPs
    initial_temp = 250.0
    max_prio = max(r.priority for r in pending_requests)
    if max_prio >= 4 or len(pending_requests) > num_vehicles:
        initial_temp = 450.0

    final_assignment = solve_assignment(
        get_selected_assignment_algorithm(), simulator, cost_matrix, pending_requests, initial_temp
    )

    # Identify vehicles that are changing tasks (or becoming free) and reset them
    for v_idx, r_idx in enumerate(final_assignment):
        vehicle = available_vehicles[v_idx]

        # Determine the new request for this vehicle (or None)
        new_req = None
        if r_idx != -1:
            new_req = pending_requests[r_idx]

        # Check if vehicle needs to drop its current request
        if vehicle.request:
            # If it's a different request (or no request), we must unassign the old one
            if vehicle.request != new_req:
                old_req = vehicle.request
                print(
                    f"[Reassignment] {vehicle.id} dropping {old_req.id} (New: {new_req.id if new_req else 'None'})"
                )

                # Remove from pickup list safely
                if old_req in simulator.requests_to_pickup:
                    simulator.requests_to_pickup.remove(old_req)

                # Add back to pending list if not already there
                if old_req not in simulator.requests:
                    simulator.requests.append(old_req)

                # Reset vehicle state
                vehicle.request = None
                vehicle.condition = VehicleCondition.AVAILABLE
                vehicle.current_route = []

    # Apply new assignments
    for v_idx, r_idx in enumerate(final_assignment):
        vehicle = available_vehicles[v_idx]

        if r_idx != -1:
            new_req = pending_requests[r_idx]

            if vehicle.request == new_req:
                continue

            assign_request_to_vehicle(simulator, new_req, vehicle)

    # Check
    for req in pending_requests:
        # If req is not in pickup/dropoff/completed
        is_active = req in simulator.requests_to_pickup or req in simulator.requests_to_dropoff

        if not is_active and req not in simulator.requests:
            simulator.requests.append(req)


def assign_request_to_vehicle(simulator: "Simulator", request: Request, v: Vehicle):
    # Remove from pending list if present
    if request in simulator.requests:
        simulator.requests.remove(request)

    # Add to pickup list if not present
    if request not in simulator.requests_to_pickup:
        simulator.requests_to_pickup.append(request)

    v.request = request
    v.condition = VehicleCondition.ON_WAY_TO_CLIENT

    dist_str = f"{v.remaining_km:.0f}km"

    path_info = find_route(
        get_selected_algorithm(),
        simulator.map,
        v.position_node,
        request.start_node,
        current_time=simulator.current_time,
        traffic_manager=simulator.traffic_manager,
    )

    if path_info:
        path, _, _ = path_info
        v.current_route = path
        v.current_segment_index = 0
        v.current_segment_progress_time = 0.0
    else:
        print(f"[SA] Erro: Caminho real não encontrado para atribuição {v.id}->{request.id}")
        v.request = None
        v.condition = VehicleCondition.AVAILABLE
        if request in simulator.requests_to_pickup:
            simulator.requests_to_pickup.remove(request)
        simulator.requests.append(request)
