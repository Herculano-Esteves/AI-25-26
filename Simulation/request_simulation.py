from typing import List, TYPE_CHECKING
from models import VehicleCondition, Vehicle, Request, Node
from search import find_a_star_route, _heuristic_distance
from mapGen import generate_random_request

import numpy as np
from scipy.optimize import linear_sum_assignment


if TYPE_CHECKING:
    from simulator import Simulator


def assign_pending_requests(simulator: "Simulator"):
    # 1. Get initial lists
    pending_requests = simulator.requests
    if not pending_requests:
        return

    available_vehicles = [
        v for v in simulator.vehicles if v.condition == VehicleCondition.AVAILABLE
    ]
    if not available_vehicles:
        return

    # 2. Build the full Cost Matrix
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
            path_info = find_a_star_route(
                simulator.map, vehicle.position_node, request.start_node
            )
            if path_info:
                # The cost is the 'time'
                _, time, _ = path_info
                cost_matrix[i, j] = time
            # else: cost remains 'inf' (no path)

    # Find which requests (cols) are serviceable
    serviceable_request_indices = []
    serviceable_requests = []
    for j in range(num_requests):
        # If NOT all values in this column are 'inf'
        if not np.all(cost_matrix[:, j] == float("inf")):
            serviceable_request_indices.append(j)
            serviceable_requests.append(pending_requests[j])

    # If no requests are serviceable, stop
    if not serviceable_requests:
        return

    # Filter the matrix to only include serviceable requests
    pruned_matrix_cols = cost_matrix[:, serviceable_request_indices]

    # Find which vehicles (rows) are serviceable
    serviceable_vehicle_indices = []
    serviceable_vehicles = []
    for i in range(num_vehicles):
        # If NOT all values in this row (of the *pruned* matrix) are 'inf'
        if not np.all(pruned_matrix_cols[i, :] == float("inf")):
            serviceable_vehicle_indices.append(i)
            serviceable_vehicles.append(available_vehicles[i])

    # If no vehicles can service the remaining requests, stop
    if not serviceable_vehicles:
        return

    # We now have a clean, feasible matrix by multi-indexing
    # This selects only the rows and columns that are valid
    feasible_matrix = cost_matrix[
        np.ix_(serviceable_vehicle_indices, serviceable_request_indices)
    ]

    # 4. Check if any assignments are possible
    if feasible_matrix.size == 0:
        # No valid assignments exist
        return

    # 5. Solve the (now-feasible) Assignment Problem
    vehicle_indices, request_indices = linear_sum_assignment(feasible_matrix)

    # 6. Process the Optimal Assignments
    assignments_to_make = []
    for v_idx, r_idx in zip(vehicle_indices, request_indices):

        cost = feasible_matrix[v_idx, r_idx]
        if cost == float("inf"):
            continue

        vehicle = serviceable_vehicles[v_idx]
        request = serviceable_requests[r_idx]
        assignments_to_make.append((vehicle, request))

    # 7. Execute assignments
    for vehicle, request in assignments_to_make:
        if (
            request in simulator.requests
            and vehicle.condition == VehicleCondition.AVAILABLE
        ):

            assign_request_to_vehicle(simulator, request, vehicle)

            # This removes from the *original* simulator list
            simulator.requests.remove(request)


def assign_request_to_vehicle(simulator: "Simulator", request: Request, v: Vehicle):
    simulator.requests_to_pickup.append(request)
    v.request = request
    v.condition = VehicleCondition.ON_WAY_TO_CLIENT

    print(
        f"[Assignment] {v.id} (Optimal) aceitou {request.id}. "
        f"A caminho de {request.start_node.position}"
    )

    # We must re-calculate the path here, since we only stored the *time*
    path, time, distance = find_a_star_route(
        simulator.map, v.position_node, request.start_node
    )

    if path:
        v.route_to_do = path
    else:
        # This should not happen, as it would have been 'inf'
        # But as a fallback, we reset the vehicle
        print(f"[ERROR] No path found for {v.id} to {request.id}. Resetting vehicle.")
        v.request = None
        v.condition = VehicleCondition.AVAILABLE
        simulator.requests_to_pickup.remove(request)
        # Put request back in the queue
        simulator.requests.append(request)


def generate_new_requests_if_needed(simulator: "Simulator"):
    # Limit active requests (pending + in_progress)
    total_active_requests = (
        len(simulator.requests)
        + len(simulator.requests_to_pickup)
        + len(simulator.requests_to_dropoff)
    )

    # Check if we are below the desired threshold
    if total_active_requests < simulator.NUM_INITIAL_REQUESTS:
        num_to_gen = simulator.NUM_REQUESTS_TO_GENERATE
        print(
            f"[Simulação] Poucos requests ativos ({total_active_requests}). A gerar {num_to_gen} novos."
        )
        for _ in range(num_to_gen):
            simulator.requests.append(generate_random_request(list(simulator.map.nos)))
