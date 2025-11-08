from search import find_a_star_route
from models import VehicleCondition, Vehicle, Request, Node
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Simulation.simulator import Simulator


def manage_vehicle(simulator: "Simulator", v: Vehicle, time_to_advance: float):
    if v.current_route:
        _update_continuous_movement(simulator, v, time_to_advance)
    else:
        _manage_stopped_vehicle_state(simulator, v)


def _update_continuous_movement(
    simulator: "Simulator", v: Vehicle, time_to_advance: float
):
    # Updates the vehicle's position with its route
    time_remaining_in_tick = time_to_advance

    while time_remaining_in_tick > 0:
        if not v.current_route or v.current_segment_index >= len(v.current_route) - 1:
            # Check if the vehicle at the end of a route
            was_at_destination = bool(v.current_route)
            v.current_route = []
            v.current_segment_index = 0
            v.current_segment_progress_time = 0.0

            if was_at_destination:
                _handle_route_arrival(simulator, v)

            break

        # Get the start and end nodes
        start_node = v.current_route[v.current_segment_index]
        end_node = v.current_route[v.current_segment_index + 1]

        # Get the travel stats for this segment
        edge_info = simulator.map.connection_weight(start_node, end_node)
        if not edge_info:
            v.current_route = []
            break

        segment_distance, segment_total_time = edge_info
        time_needed_to_finish_segment = (
            segment_total_time - v.current_segment_progress_time
        )

        if time_remaining_in_tick < time_needed_to_finish_segment:
            # Vehicle will not finish the segment this tick
            v.current_segment_progress_time += time_remaining_in_tick
            _update_gui_coordinates(v, start_node, end_node, segment_total_time)
            time_remaining_in_tick = 0.0
        else:
            # Vehicle will finish the segment this tick
            time_remaining_in_tick -= time_needed_to_finish_segment

            v.remaining_km -= segment_distance
            v.position_node = end_node
            v.map_coordinates = end_node.position
            v.current_segment_index += 1
            v.current_segment_progress_time = 0.0

            if v.current_segment_index >= len(v.current_route) - 1:
                # This was the last segment
                v.current_route = []
                v.current_segment_index = 0
                _handle_route_arrival(simulator, v)
                time_remaining_in_tick = 0.0


def _handle_route_arrival(simulator: "Simulator", v: Vehicle):
    if v.condition == VehicleCondition.ON_WAY_TO_CLIENT:
        # Arrived at the client's pickup location
        if v.request:
            print(
                f"[Vehicle] Veiculo {v.id} chegou ao ponto de recolha de {v.request.id} na posição {v.position_node.position}."
            )

            simulator.requests_to_pickup.remove(v.request)
            simulator.requests_to_dropoff.append(v.request)
            v.condition = VehicleCondition.ON_TRIP_WITH_CLIENT

            # Route to the client's destination
            path_info = find_a_star_route(
                simulator.map, v.position_node, v.request.end_node
            )
            if path_info:
                path, time, distance = path_info
                v.current_route = path if path else []
                v.current_segment_index = 0
                v.current_segment_progress_time = 0.0
            else:
                print(f"[Vehicle] ERROR: Caminho não encontrado do veiculo {v.id}.")
                simulator.requests_to_dropoff.remove(v.request)
                simulator.requests.append(v.request)
                v.request = None
                v.condition = VehicleCondition.AVAILABLE

    elif v.condition == VehicleCondition.ON_TRIP_WITH_CLIENT:
        # Arrived at the client's destination
        if v.request:
            print(
                f"[Vehicle] {v.id} viagem completa do pedido {v.request.id} na posição {v.position_node.position}."
            )
            simulator.requests_to_dropoff.remove(v.request)
        v.condition = VehicleCondition.AVAILABLE
        v.request = None

    elif v.condition == VehicleCondition.AT_STATION:
        # TODO: Logic for finishing refueling
        pass


def _manage_stopped_vehicle_state(simulator: "Simulator", v: Vehicle):
    if v.condition == VehicleCondition.AVAILABLE:
        # Where the refueling check from your
        # original 'manage_stopped_vehicle' would go.
        # if v.remaining_km < simulator.LOW_AUTONOMY_THRESHOLD:
        #    _find_station_and_set_route(v)
        pass


def _update_gui_coordinates(
    v: Vehicle, start_node: Node, end_node: Node, segment_total_time: float
):
    # Interpolates the vehicle's (x, y) coordinates for the GUI.
    if segment_total_time == 0:
        progress = 1.0
    else:
        progress = v.current_segment_progress_time / segment_total_time

    progress = max(0.0, min(1.0, progress))
    x1, y1 = start_node.position
    x2, y2 = end_node.position
    new_x = x1 + (x2 - x1) * progress
    new_y = y1 + (y2 - y1) * progress
    v.map_coordinates = (new_x, new_y)
