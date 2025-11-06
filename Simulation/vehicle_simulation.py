from search import find_a_star_route, _heuristic_distance
from models import VehicleCondition, Vehicle, Request, Node
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from Simulation.simulator import Simulator


def manage_vehicle(simulator: "Simulator", v: Vehicle, time_to_advance: float):
    update_vehicle_movement(v, time_to_advance)

    if not v.end_node:
        manage_stopped_vehicle(simulator, v)


def update_vehicle_movement(v: Vehicle, time_to_advance: float):
    if not v.end_node:
        return

    v.time_passed_on_trip += time_to_advance

    if v.time_passed_on_trip >= v.extimated_trip_time:
        # Vehicle has arrived at the end_node
        v.remaining_km -= v.total_request_km

        v.position_node = v.end_node
        v.map_coordinates = v.position_node.position

        # Clear transit state
        v.start_node = None
        v.end_node = None
        v.time_passed_on_trip = 0
        v.extimated_trip_time = 0
        v.total_request_km = 0.0

    else:
        # Vehicle is mid-trip. Interpolate position for the GUI.
        progress = v.time_passed_on_trip / v.extimated_trip_time
        if v.start_node:
            x1, y1 = v.start_node.position
            if v.end_node:
                x2, y2 = v.end_node.position
                new_x = x1 + (x2 - x1) * progress
                new_y = y1 + (y2 - y1) * progress
                v.map_coordinates = (new_x, new_y)


def manage_stopped_vehicle(simulator: "Simulator", v: Vehicle):
    # 1. If it has a route, advance to the next node in the route
    if v.route_to_do:
        if v.route_to_do[0] != v.position_node:
            # Invalid route (doesn't start where the vehicle is)
            v.route_to_do = []

        elif len(v.route_to_do) >= 2:
            # Start movement to the next node in the route
            next_node = v.route_to_do[1]
            v.start_node = v.position_node
            v.end_node = next_node
            v.route_to_do = v.route_to_do[1:]  # Advance the route

            edge_info = simulator.map.connection_weight(v.start_node, v.end_node)
            if edge_info:
                distance, time = edge_info
                v.total_request_km = distance
                v.extimated_trip_time = time
                v.time_passed_on_trip = 0.0
            return  # The vehicle is now in motion

        else:
            # Reached the end of the route (list only has the current node)
            v.route_to_do = []

    # 2. If not moving, manage state (e.g., pickup/dropoff client)
    if v.condition == VehicleCondition.ON_WAY_TO_CLIENT:
        manage_state_on_way_to_client(simulator, v)

    elif v.condition == VehicleCondition.ON_TRIP_WITH_CLIENT:
        manage_state_on_trip(simulator, v)

    elif v.condition == VehicleCondition.AVAILABLE:
        # TODO: Check if it needs to refuel
        # if v.remaining_km < simulator.LOW_AUTONOMY_THRESHOLD:
        #    _find_station_and_set_route(v)
        pass


def manage_state_on_way_to_client(simulator: "Simulator", v: Vehicle):
    if v.request:
        print(
            f"{v.id} em {v.position_node.position}. A iniciar viagem para {v.request.end_node.position}"
        )

        simulator.requests_to_pickup.remove(v.request)
        simulator.requests_to_dropoff.append(v.request)
        v.condition = VehicleCondition.ON_TRIP_WITH_CLIENT

        # Calculate the route to the final end_node
        object = find_a_star_route(simulator.map, v.position_node, v.request.end_node)
        if object:
            path, time, distance = object
            v.route_to_do = path if path else []


def manage_state_on_trip(simulator: "Simulator", v: Vehicle):
    print(
        f"{v.id} completou a viagem em {v.position_node.position}. Disponível."
        f"Autonomia restante: {v.remaining_km:.1f} km"
    )
    if v.request:
        simulator.requests_to_dropoff.remove(v.request)
        v.condition = VehicleCondition.AVAILABLE
        v.request = None
        v.route_to_do = []
