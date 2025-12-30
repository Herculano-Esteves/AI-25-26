from typing import List, Tuple, TYPE_CHECKING
from models.request import Request
from models.vehicle import Vehicle, VehicleCondition, Motor
from models.node import Node
from Simulation.search_algorithms import (
    find_route,
    _heuristic_distance,
    haversine_km,
    calculate_time_minutes,
)
from Simulation.simulation_config import PlanningConfig
from Simulation.assignment_algorithms import solve_assignment
import numpy as np

if TYPE_CHECKING:
    from simulator import Simulator

# Timeouts: Prio 1 = 30min, Prio 5 = 10min
BASE_TIMEOUT = 30.0
TIMEOUT_PER_PRIO = 5.0

# Algoritmos seleccionados
_routing_algo = "astar"
_assignment_algo = "simulated annealing"
_cost_algo = "heuristic"

def set_selected_algorithm(algo: str):
    global _routing_algo
    _routing_algo = algo
    print(f"[Config] Rota: {algo}")

def set_selected_assignment_algorithm(algo: str):
    global _assignment_algo
    _assignment_algo = algo
    print(f"[Config] Atribuição: {algo}")

def set_selected_cost_estimation_algorithm(algo: str):
    global _cost_algo
    _cost_algo = algo
    print(f"[Config] Estimativa: {algo}")

def estimate_route(start: Node, end: Node, speed: float = 50.0) -> Tuple[List[Node], float, float]:
    """Estima tempo/distância via haversine (sem calcular rota real)."""
    dist = haversine_km(start.position[0], start.position[1], end.position[0], end.position[1])
    time = calculate_time_minutes(dist, speed)
    return [], time, dist


def get_hotspot_nodes(sim: "Simulator") -> List[Node]:
    if not sim.hotspot_manager:
        return []
    nodes = set()
    for h in sim.hotspot_manager.hotspots:
        nodes.update(h.node_cache)
    return list(nodes)


def dist_to_nearest_hotspot(node: Node, sim: "Simulator") -> float:
    hotspots = get_hotspot_nodes(sim)
    return min(_heuristic_distance(node, h) for h in hotspots) if hotspots else 0.0


def dist_to_nearest_station(node: Node, motor: Motor, sim: "Simulator") -> float:
    stations = sim.map.ev_stations if motor == Motor.ELECTRIC else sim.map.gas_stations
    return min(_heuristic_distance(node, s) for s in stations) if stations else float("inf")


def calculate_cost(
    v: Vehicle, req: Request, path_info: Tuple, sim: "Simulator", has_eco: bool
) -> float:
    """Custo total de atribuir req a v."""
    _, time_pickup, dist_pickup = path_info

    cost = time_pickup * PlanningConfig.WEIGHT_TIME

    # Espera e prioridade
    wait = sim.current_time - req.creation_time
    cost -= wait * PlanningConfig.WEIGHT_AGE + (req.priority - 1) * PlanningConfig.WEIGHT_PRIORITY

    # Penalização eco
    if req.environmental_preference and v.motor == Motor.COMBUSTION:
        cost += req.path_distance * PlanningConfig.PENALTY_ENV_MISMATCH_PER_KM

    # Penalização capacidade
    if v.passenger_capacity > req.passenger_capacity:
        cost += (v.passenger_capacity - req.passenger_capacity) * PlanningConfig.PENALTY_UNUSED_SEAT

    # Autonomia
    remaining = v.remaining_km - dist_pickup - req.path_distance
    if remaining < 0:
        return float("inf")

    if remaining < PlanningConfig.BATTERY_CRITICAL_LEVEL:
        deficit = PlanningConfig.BATTERY_CRITICAL_LEVEL - remaining
        cost += (deficit**PlanningConfig.BATTERY_RISK_EXPONENT) * PlanningConfig.WEIGHT_BATTERY_RISK

    # Logística futura
    dist_station = dist_to_nearest_station(req.end_node, v.motor, sim)
    if dist_station > remaining:
        return float("inf")
    cost += dist_station * PlanningConfig.WEIGHT_FUTURE_REFUEL
    cost += dist_to_nearest_hotspot(req.end_node, sim) * PlanningConfig.WEIGHT_ISOLATION

    # Custo de oportunidade EV
    if v.motor == Motor.ELECTRIC and not req.environmental_preference and has_eco:
        factor = min(1.0, v.remaining_km / (v.max_km * 0.6))
        cost += PlanningConfig.WEIGHT_LOST_OPPORTUNITY * factor

    # Lucro projetado
    op_cost = (dist_pickup + req.path_distance) * v.price_per_km
    profit = req.price - op_cost
    cost -= profit * PlanningConfig.WEIGHT_PROFIT

    return cost


def check_timeouts(sim: "Simulator"):
    """Remove pedidos que excederam tempo de espera."""
    for i in range(len(sim.requests) - 1, -1, -1):
        req = sim.requests[i]
        age = sim.current_time - req.creation_time
        limit = BASE_TIMEOUT - (req.priority - 1) * TIMEOUT_PER_PRIO

        if age > limit:
            print(f"[Timeout] Pedido {req.id} cancelado ({age:.0f}m > {limit:.0f}m)")
            sim.requests.pop(i)
            sim.stats.step_requests_cancelled_timeout += 1
            sim.stats.total_requests_failed += 1


def assign_pending_requests(sim: "Simulator"):
    """Atribui pedidos pendentes a veículos disponíveis."""
    sim.assignment_needed = False

    pending = list(sim.requests)

    # Veículos livres ou a caminho do cliente (podem ser redireccionados)
    available = [
        v
        for v in sim.vehicles
        if v.condition == VehicleCondition.AVAILABLE
        and v.remaining_km >= sim.LOW_AUTONOMY_THRESHOLD
    ]

    redirectable = [
        v
        for v in sim.vehicles
        if v.condition == VehicleCondition.ON_WAY_TO_CLIENT
        and v.remaining_km >= sim.LOW_AUTONOMY_THRESHOLD
    ]
    available.extend(redirectable)

    for v in redirectable:
        if v.request and v.request not in pending:
            pending.append(v.request)

    if not pending or not available:
        return

    has_eco = any(r.environmental_preference for r in pending)

    # Matriz de custos
    cost_matrix = np.full((len(available), len(pending)), float("inf"))

    for i, v in enumerate(available):
        for j, req in enumerate(pending):
            if v.passenger_capacity < req.passenger_capacity:
                continue

            if _cost_algo == "heuristic":
                path_info = estimate_route(v.position_node, req.start_node)
            else:
                path_info = find_route(
                    _routing_algo,
                    sim.map,
                    v.position_node,
                    req.start_node,
                    current_time=sim.current_time,
                    traffic_manager=sim.traffic_manager,
                )

            if not path_info:
                continue

            cost = calculate_cost(v, req, path_info, sim, has_eco)
            if v.request == req:
                cost -= 5.0  # Bónus por manter mesma atribuição
            cost_matrix[i, j] = cost

    if np.all(cost_matrix == float("inf")):
        return

    # Temperatura inicial mais alta se há VIPs
    temp = (
        450.0 if max(r.priority for r in pending) >= 4 or len(pending) > len(available) else 250.0
    )

    assignment = solve_assignment(_assignment_algo, sim, cost_matrix, pending, temp)

    # Libertar veículos que vão mudar de pedido
    for v_idx, r_idx in enumerate(assignment):
        v = available[v_idx]
        new_req = pending[r_idx] if r_idx != -1 else None

        if v.request and v.request != new_req:
            old = v.request
            print(f"[Reatribuição] {v.id}: {old.id} → {new_req.id if new_req else 'livre'}")
            if old in sim.requests_to_pickup:
                sim.requests_to_pickup.remove(old)
            if old not in sim.requests:
                sim.requests.append(old)
            v.request = None
            v.condition = VehicleCondition.AVAILABLE
            v.current_route = []

    # Aplicar novas atribuições
    for v_idx, r_idx in enumerate(assignment):
        if r_idx != -1:
            v, req = available[v_idx], pending[r_idx]
            if v.request != req:
                _assign(sim, req, v)

    # Garantir que pedidos não atribuídos voltam à fila
    for req in pending:
        active = req in sim.requests_to_pickup or req in sim.requests_to_dropoff
        if not active and req not in sim.requests:
            sim.requests.append(req)


def _assign(sim: "Simulator", req: Request, v: Vehicle):
    """Atribui pedido a veículo e calcula rota."""
    if req in sim.requests:
        sim.requests.remove(req)
    if req not in sim.requests_to_pickup:
        sim.requests_to_pickup.append(req)

    v.request = req
    v.condition = VehicleCondition.ON_WAY_TO_CLIENT

    path_info = find_route(
        _routing_algo,
        sim.map,
        v.position_node,
        req.start_node,
        current_time=sim.current_time,
        traffic_manager=sim.traffic_manager,
    )

    if path_info:
        v.current_route = path_info[0]
        v.current_segment_index = 0
        v.current_segment_progress_time = 0.0
    else:
        print(f"[Erro] Rota {v.id}→{req.id} não encontrada")
        v.request = None
        v.condition = VehicleCondition.AVAILABLE
        if req in sim.requests_to_pickup:
            sim.requests_to_pickup.remove(req)
        sim.requests.append(req)
