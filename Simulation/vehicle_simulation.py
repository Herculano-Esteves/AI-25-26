from search_algorithms import find_route, _heuristic_distance
from models.vehicle import Vehicle, VehicleCondition, Motor
from models.node import Node
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Simulation.simulator import Simulator


PENALTY_TIME = 30.0
GAS_REFUEL_TIME_MINUTES = 5.0
# https://www.acp.pt/o-clube/revista-acp/atualidade/detalhe/nivel-das-emissoes-poluentes-de-carros-novos-cresceu-em-2024
# Portugal regista emissões médias de CO2 de 86,8 g/km.
CO2_GRAMS_PER_KM_COMBUSTION = 87


def manage_vehicle(simulator: "Simulator", v: Vehicle, time_to_advance: float):
    if v.current_route:
        _update_continuous_movement(simulator, v, time_to_advance)
    else:
        _manage_stopped_vehicle_state(simulator, v, time_to_advance)


def _update_continuous_movement(simulator: "Simulator", v: Vehicle, time_to_advance: float):
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

        segment_distance, segment_total_time_base, segment_max_speed = edge_info
        current_traffic_factor = 1.0
        if simulator.traffic_manager:
            # Calcula o trânsito na posição atual DO VEÍCULO e na hora DO SIMULADOR
            current_traffic_factor = simulator.traffic_manager.get_traffic_factor(
                v.position_node.position, simulator.current_time
            )

        # O tempo real para cruzar aumenta (velocidade diminui)
        segment_total_time_real = segment_total_time_base * current_traffic_factor

        speed_km_per_min = 0.0
        if segment_total_time_real > 0:
            speed_km_per_min = segment_distance / segment_total_time_real

        # Usa o tempo real para calcular progresso
        time_needed_to_finish_segment = segment_total_time_real - v.current_segment_progress_time

        if time_remaining_in_tick < time_needed_to_finish_segment:
            # Save distance on stats
            dist_this_tick = speed_km_per_min * time_remaining_in_tick
            _record_vehicle_movement_stats(simulator, v, dist_this_tick)

            # Vehicle will not finish the segment this tick
            v.current_segment_progress_time += time_remaining_in_tick
            _update_gui_coordinates(v, start_node, end_node, segment_total_time_real)
            time_remaining_in_tick = 0.0
        else:
            # Save distance on stats
            dist_this_tick = speed_km_per_min * time_needed_to_finish_segment
            _record_vehicle_movement_stats(simulator, v, dist_this_tick)

            # Vehicle will finish the segment this tick
            time_remaining_in_tick -= time_needed_to_finish_segment

            v.remaining_km -= segment_distance

            if v.remaining_km <= 0:
                print(f"[Vehicle] Veículo {v.id} ficou sem autonomia!")
                v.remaining_km = 0
                v.condition = VehicleCondition.UNAVAILABLE
                v.time_stopped = 0.0
                v.current_route = []
                v.current_segment_index = 0
                v.times_borken += 1
                simulator.stats.total_requests_failed += 1

                if v.request:
                    print(f"[Vehicle] Pedido {v.request.id} foi cancelado.")
                    if v.request in simulator.requests_to_pickup:
                        simulator.requests_to_pickup.remove(v.request)
                    if v.request in simulator.requests_to_dropoff:
                        simulator.requests_to_dropoff.remove(v.request)
                    simulator.requests.append(v.request)
                    v.request = None

                time_remaining_in_tick = 0.0
                break

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

            # Stats waiting time
            stats = simulator.stats
            wait_time = simulator.current_time - v.request.creation_time

            stats.total_requests_picked_up += 1
            stats.total_wait_time_for_pickup += wait_time
            stats.min_wait_time = min(stats.min_wait_time, wait_time)
            stats.max_wait_time = max(stats.max_wait_time, wait_time)

            simulator.requests_to_pickup.remove(v.request)
            simulator.requests_to_dropoff.append(v.request)
            v.condition = VehicleCondition.ON_TRIP_WITH_CLIENT

            if v.request and v.request.path:
                v.current_route = v.request.path
                v.current_segment_index = 0
                v.current_segment_progress_time = 0.0
            else:
                # Error
                print(
                    f"[Vehicle] ERROR: Caminho não encontrado no pedido {v.request.id if v.request else 'N/A'}."
                )
                if v.request in simulator.requests_to_dropoff:
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

            # Stats of the trip
            stats = simulator.stats
            stats.total_requests_completed += 1

            # Real time
            total_life_time = simulator.current_time - v.request.creation_time
            stats.total_time_for_completed_requests += total_life_time
            stats.min_total_trip_time = min(stats.min_total_trip_time, total_life_time)
            stats.max_total_trip_time = max(stats.max_total_trip_time, total_life_time)

            # Revenue
            stats.total_revenue_generated += v.request.price
            stats.step_revenue_generated += v.request.price

            simulator.requests_to_dropoff.remove(v.request)

            # Occupancy Stats
            occupancy = v.request.passenger_capacity / v.passenger_capacity
            v.total_trips += 1
            v.sum_occupancy += occupancy

        v.condition = VehicleCondition.AVAILABLE
        v.request = None

    elif v.condition == VehicleCondition.ON_WAY_TO_STATION:
        print(f"[Vehicle] {v.id} chegou à estação em {v.position_node.position}.")
        v.condition = VehicleCondition.AT_STATION
        v.time_stopped = 0.0

    elif v.condition == VehicleCondition.AT_STATION:
        pass


def _manage_stopped_vehicle_state(simulator: "Simulator", v: Vehicle, time_to_advance: float):

    if v.condition == VehicleCondition.UNAVAILABLE:
        v.time_stopped += time_to_advance

        if v.time_stopped >= PENALTY_TIME:
            print(f"[Vehicle] {v.id} cumpriu penalidade. A voltar ao serviço.")
            v.condition = VehicleCondition.AVAILABLE
            v.remaining_km = simulator.LOW_AUTONOMY_THRESHOLD
            v.time_stopped = 0.0

    elif v.condition == VehicleCondition.AVAILABLE:
        if v.remaining_km < simulator.LOW_AUTONOMY_THRESHOLD:
            _find_station_and_set_route(simulator, v)

    elif v.condition == VehicleCondition.AT_STATION:
        _handle_refueling_at_station(simulator, v, time_to_advance)


def _handle_refueling_at_station(simulator: "Simulator", v: Vehicle, time_to_advance: float):
    """
    Gere o tempo de paragem para recarga (EV) ou reabastecimento (Gas).
    """
    v.time_stopped += time_to_advance
    v.total_station_time += time_to_advance

    if v.motor == Motor.ELECTRIC:
        simulator.stats.step_station_time_ev += time_to_advance
    else:
        simulator.stats.step_station_time_gas += time_to_advance

    if v.motor == Motor.ELECTRIC:
        node = v.position_node
        rate_km_per_hour = node.energy_recharge_rate_kw

        if rate_km_per_hour <= 0:
            rate_km_per_hour = 300.0

        rate_km_per_minute = rate_km_per_hour / 60.0
        km_recharged_this_tick = time_to_advance * rate_km_per_minute

        v.remaining_km += km_recharged_this_tick

        if v.remaining_km >= v.max_km:
            v.remaining_km = v.max_km
            v.condition = VehicleCondition.AVAILABLE
            v.time_stopped = 0.0
            print(f"[Vehicle] {v.id} (EV) carregamento completo.")

    else:
        if v.time_stopped >= GAS_REFUEL_TIME_MINUTES:
            v.remaining_km = v.max_km
            v.condition = VehicleCondition.AVAILABLE
            v.time_stopped = 0.0
            print(f"[Vehicle] {v.id} (Gas) reabastecimento completo após 5 min.")


def _find_station_and_set_route(simulator: "Simulator", v: Vehicle):

    target_nodes = []
    if v.motor == Motor.ELECTRIC:
        target_nodes = [n for n in simulator.map.ev_stations if n.is_available]
    else:
        target_nodes = [n for n in simulator.map.gas_stations if n.is_available]

    if not target_nodes:
        print(f"[Vehicle] AVISO: {v.id} não encontrou estações de {v.motor.name}!")
        return

    closest_candidates = sorted(
        target_nodes, key=lambda n: _heuristic_distance(v.position_node, n)
    )[:3]

    best_station = None
    best_path_info = None
    min_time = float("inf")

    for station in closest_candidates:
        path_info = find_route("astar", simulator.map, v.position_node, station)

        if path_info:
            path, time, distance = path_info

            if v.remaining_km > distance and time < min_time:
                min_time = time
                best_station = station
                best_path_info = path_info

    if best_path_info:
        path, time, distance = best_path_info
        if best_station:
            print(
                f"[Vehicle] {v.id} (Autonomia: {v.remaining_km:.1f}km) a caminho da estação {best_station.position}. Dist: {distance:.1f}km"
            )

        v.current_route = path
        v.current_segment_index = 0
        v.current_segment_progress_time = 0.0
        v.condition = VehicleCondition.ON_WAY_TO_STATION
    else:
        v.current_route = []
        v.current_segment_index = 0
        v.current_segment_progress_time = 0.0
        v.condition = VehicleCondition.ON_WAY_TO_STATION
        print(
            f"[Vehicle] AVISO: {v.id} não consegue alcançar nenhuma estação de {v.motor.name} com {v.remaining_km:.1f}km de autonomia!"
        )


def _update_gui_coordinates(
    v: Vehicle, start_node: Node, end_node: Node, segment_total_time: float
):
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


def _record_vehicle_movement_stats(simulator: "Simulator", v: Vehicle, distance_this_tick: float):
    stats = simulator.stats
    cost = distance_this_tick * v.price_per_km
    stats.step_operational_cost += cost

    stats.step_kms_driven += distance_this_tick
    if v.motor == Motor.ELECTRIC:
        stats.step_kms_driven_ev += distance_this_tick
    else:
        stats.step_kms_driven_gas += distance_this_tick

    if v.motor == Motor.COMBUSTION:
        emitted_kg = (distance_this_tick * CO2_GRAMS_PER_KM_COMBUSTION) / 1000.0
        v.co2_emitted += emitted_kg
        stats.step_co2_emitted += emitted_kg

    if v.condition == VehicleCondition.ON_TRIP_WITH_CLIENT:
        stats.step_kms_driven_with_passenger += distance_this_tick

    elif v.condition in [VehicleCondition.ON_WAY_TO_CLIENT, VehicleCondition.ON_WAY_TO_STATION]:
        stats.step_kms_driven_empty += distance_this_tick
        if v.motor == Motor.ELECTRIC:
            stats.step_kms_driven_empty_ev += distance_this_tick
        else:
            stats.step_kms_driven_empty_gas += distance_this_tick
