from typing import List, TYPE_CHECKING
from models import VehicleCondition, Vehicle, Request, Node
from search import find_a_star_route, _heuristic_distance
from mapGen import generate_random_request

if TYPE_CHECKING:
    from simulator import Simulator


def assign_pending_requests(simulator: "Simulator"):
    if not simulator.requests:
        return

    available_vehicles = [
        v for v in simulator.vehicles if v.condition == VehicleCondition.AVAILABLE
    ]

    if not available_vehicles:
        return

    # Iterate over a copy of the list to allow removal
    for request in simulator.requests[:]:
        if not available_vehicles:
            break

        best_vehicle = None
        lowest_weight = float("inf")

        # Find the closest vehicle (by straight-line distance)
        for v in available_vehicles:
            # Use the imported heuristic
            weight = _heuristic_distance(v.position_node, request.start_node)
            if weight < lowest_weight:
                lowest_weight = weight
                best_vehicle = v

        if best_vehicle:
            simulator.requests.remove(request)
            available_vehicles.remove(best_vehicle)
            assign_request_to_vehicle(simulator, request, best_vehicle)


def assign_request_to_vehicle(simulator: "Simulator", request: Request, v: Vehicle):
    simulator.requests_to_pickup.append(request)
    v.request = request
    v.condition = VehicleCondition.ON_WAY_TO_CLIENT

    print(
        f"[Assignment] {v.id} (mais próximo) aceitou {request.id}. "
        f"A caminho de {request.start_node.position}"
    )

    path, time, distance = find_a_star_route(
        simulator.map, v.position_node, request.start_node
    )
    v.route_to_do = path if path else []


def generate_new_requests_if_needed(simulator: "Simulator"):
    if not simulator.requests:
        print(
            f"[Simulação] Fila de requests vazia. A gerar {simulator.NUM_REQUESTS_TO_GENERATE} novos requests."
        )
        for _ in range(simulator.NUM_REQUESTS_TO_GENERATE):
            simulator.requests.append(generate_random_request(list(simulator.map.nos)))
