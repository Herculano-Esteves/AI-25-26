from typing import List, TYPE_CHECKING
from models.request import Request
from models.vehicle import Vehicle, VehicleCondition, Motor
from search import find_a_star_route
from mapGen import generate_random_request

import numpy as np
from scipy.optimize import linear_sum_assignment


if TYPE_CHECKING:
    from simulator import Simulator

# Penalties in minutes:
ENVIRONMENTAL_PREFERENCE_PENALTY = (
    30.0  # Maybe make it infinite to make it impossible to use combustion
)
PER_UNUSED_PASSENGER_SEAT_PENALTY = 5.0
REQUEST_AGE_PRIORITY_WEIGHT = 0.5
REQUEST_PRIORITY_WEIGHT = 10.0  # Priority weight


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

            # Check capacity constraint
            if vehicle.passenger_capacity < request.passenger_capacity:
                cost_matrix[i, j] = float("inf")
                continue

            # Calculate cost (A* time)
            path_info = find_a_star_route(simulator.map, vehicle.position_node, request.start_node)
            if path_info:
                _, time, dist_to_client = path_info

                # Autonomy check
                dist_to_refuel = float("inf")  # Distance to refuel after dropoff
                if vehicle.motor == Motor.ELECTRIC:
                    dist_to_refuel = request.nearest_ev_station_distance
                else:
                    dist_to_refuel = request.nearest_gas_station_distance

                # No station is reachable
                if dist_to_refuel == float("inf"):
                    cost_matrix[i, j] = float("inf")
                    continue

                # Total distance
                total_distance_needed = dist_to_client + request.path_distance + dist_to_refuel

                if vehicle.remaining_km < total_distance_needed:
                    cost_matrix[i, j] = float("inf")
                    continue

                # How long this request has been waiting
                wait_time_minutes = simulator.current_time - request.creation_time
                age_bonus = wait_time_minutes * REQUEST_AGE_PRIORITY_WEIGHT

                priority_bonus = (request.priority - 1) * REQUEST_PRIORITY_WEIGHT
                time += -age_bonus - priority_bonus

                if request.environmental_preference and vehicle.motor == Motor.COMBUSTION:
                    time += ENVIRONMENTAL_PREFERENCE_PENALTY

                if request.passenger_capacity < vehicle.passenger_capacity:
                    time += PER_UNUSED_PASSENGER_SEAT_PENALTY * (
                        vehicle.passenger_capacity - request.passenger_capacity
                    )

                cost_matrix[i, j] = time
            # cost_matrix remains 'inf' if no path found

    # Find which requests are serviceable
    serviceable_request_indices = []
    serviceable_requests = []
    for j in range(num_requests):
        if not np.all(cost_matrix[:, j] == float("inf")):
            serviceable_request_indices.append(j)
            serviceable_requests.append(pending_requests[j])

    if not serviceable_requests:
        return

    # Filter the matrix to only include serviceable requests
    pruned_matrix_cols = cost_matrix[:, serviceable_request_indices]

    # Find which vehicles are serviceable
    serviceable_vehicle_indices = []
    serviceable_vehicles = []
    for i in range(num_vehicles):
        if not np.all(pruned_matrix_cols[i, :] == float("inf")):
            serviceable_vehicle_indices.append(i)
            serviceable_vehicles.append(available_vehicles[i])

    if not serviceable_vehicles:
        return

    # This selects only the valid rows and columns
    feasible_matrix = cost_matrix[np.ix_(serviceable_vehicle_indices, serviceable_request_indices)]

    if feasible_matrix.size == 0:
        return

    # Check if there is at least one finite number
    if not np.any(np.isfinite(feasible_matrix)):
        return

    # Replace inf for a huge number (biggest number * row * col)
    solver_matrix = np.copy(feasible_matrix)
    finite_max_array = solver_matrix[np.isfinite(solver_matrix)]

    if finite_max_array.size == 0:
        return

    finite_max = np.max(finite_max_array)
    num_rows, num_cols = solver_matrix.shape
    biggest_cost = (finite_max * max(num_rows, num_cols)) + 1
    solver_matrix[np.isinf(solver_matrix)] = biggest_cost

    # Solve
    vehicle_indices, request_indices = linear_sum_assignment(solver_matrix)

    assignments_to_make = []
    for v_id, r_id in zip(vehicle_indices, request_indices):

        cost = feasible_matrix[v_id, r_id]
        if cost == float("inf"):
            continue

        vehicle = serviceable_vehicles[v_id]
        request = serviceable_requests[r_id]
        assignments_to_make.append((vehicle, request))

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
