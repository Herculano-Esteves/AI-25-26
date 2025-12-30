from Simulation.search_algorithms import find_route, _heuristic_distance
from models.vehicle import Vehicle, VehicleCondition, Motor
from models.node import Node
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Simulation.simulator import Simulator

PENALTY_TIME = 30.0
GAS_REFUEL_MINUTES = 5.0
CO2_G_PER_KM = 87  # Média Portugal 2024


def manage_vehicle(sim: "Simulator", v: Vehicle, dt: float):
    """Actualiza estado do veículo: movimento ou paragem."""
    if v.current_route:
        # Veículo está em movimento
        _move(sim, v, dt)
    else:
        _handle_stopped(sim, v, dt)


def _move(sim: "Simulator", v: Vehicle, dt: float):
    """Move veículo ao longo da rota."""
    time_left = dt

    # Processa movimento enquanto houver tempo no tick
    while time_left > 0:
        # Verifica se chegou ao fim da rota
        if not v.current_route or v.current_segment_index >= len(v.current_route) - 1:
            had_route = bool(v.current_route)
            v.current_route = []
            v.current_segment_index = 0
            v.current_segment_progress_time = 0.0
            if had_route:
                _on_arrival(sim, v)
            break

        start = v.current_route[v.current_segment_index]
        end = v.current_route[v.current_segment_index + 1]

        edge = sim.map.connection_weight(start, end)
        if not edge:
            # Aresta inválida
            v.current_route = []
            break

        dist, time_base, _ = edge
        
        traffic = 1.0
        if sim.traffic_manager:
            traffic = sim.traffic_manager.get_traffic_factor(v.position_node.position, sim.current_time)

        time_real = time_base * traffic
        speed = dist / time_real if time_real > 0 else 0.0
        time_to_finish = time_real - v.current_segment_progress_time

        if time_left < time_to_finish:
            # Não termina segmento neste tick
            _record_stats(sim, v, speed * time_left)
            v.current_segment_progress_time += time_left
            _update_coords(v, start, end, time_real)
            break
        else:
            # Termina segmento e passa ao próximo
            _record_stats(sim, v, speed * time_to_finish)
            time_left -= time_to_finish
            v.remaining_km -= dist

            if v.remaining_km <= 0:
                _breakdown(sim, v)
                break

            v.position_node = end
            v.map_coordinates = end.position
            v.current_segment_index += 1
            v.current_segment_progress_time = 0.0

            if v.current_segment_index >= len(v.current_route) - 1:
                # Era o último segmento
                v.current_route = []
                v.current_segment_index = 0
                _on_arrival(sim, v)
                break


def _breakdown(sim: "Simulator", v: Vehicle):
    """Veículo ficou sem autonomia."""
    print(f"[Avaria] Veículo {v.id} sem autonomia!")
    v.remaining_km = 0
    v.condition = VehicleCondition.UNAVAILABLE
    v.time_stopped = 0.0
    v.current_route = []
    v.current_segment_index = 0
    v.times_borken += 1
    sim.stats.total_requests_failed += 1

    if v.request:
        # Cancela pedido em curso
        print(f"[Avaria] Pedido {v.request.id} cancelado")
        if v.request in sim.requests_to_pickup:
            sim.requests_to_pickup.remove(v.request)
        if v.request in sim.requests_to_dropoff:
            sim.requests_to_dropoff.remove(v.request)
        sim.requests.append(v.request)
        v.request = None
        sim.assignment_needed = True


def _on_arrival(sim: "Simulator", v: Vehicle):
    """Chegou ao destino da rota actual."""
    
    if v.condition == VehicleCondition.ON_WAY_TO_CLIENT and v.request:
        # Chegou ao ponto de recolha do cliente
        wait = sim.current_time - v.request.creation_time
        sim.stats.total_requests_picked_up += 1
        sim.stats.total_wait_time_for_pickup += wait
        sim.stats.min_wait_time = min(sim.stats.min_wait_time, wait)
        sim.stats.max_wait_time = max(sim.stats.max_wait_time, wait)

        sim.requests_to_pickup.remove(v.request)
        sim.requests_to_dropoff.append(v.request)
        v.condition = VehicleCondition.ON_TRIP_WITH_CLIENT

        if v.request.path:
            # Define rota para o destino do cliente
            v.current_route = v.request.path
            v.current_segment_index = 0
            v.current_segment_progress_time = 0.0
        else:
            print(f"[Erro] Pedido {v.request.id} sem rota!")
            sim.requests_to_dropoff.remove(v.request)
            sim.requests.append(v.request)
            v.request = None
            v.condition = VehicleCondition.AVAILABLE
            sim.assignment_needed = True

    elif v.condition == VehicleCondition.ON_TRIP_WITH_CLIENT and v.request:
        # Entregou o cliente no destino
        total_time = sim.current_time - v.request.creation_time
        sim.stats.total_requests_completed += 1
        sim.stats.total_time_for_completed_requests += total_time
        sim.stats.min_total_trip_time = min(sim.stats.min_total_trip_time, total_time)
        sim.stats.max_total_trip_time = max(sim.stats.max_total_trip_time, total_time)
        sim.stats.total_revenue_generated += v.request.price
        sim.stats.step_revenue_generated += v.request.price

        sim.requests_to_dropoff.remove(v.request)
        v.total_trips += 1
        v.sum_occupancy += v.request.passenger_capacity / v.passenger_capacity
        v.condition = VehicleCondition.AVAILABLE
        v.request = None
        sim.assignment_needed = True

    elif v.condition == VehicleCondition.ON_WAY_TO_STATION:
        # Chegou à estação de abastecimento
        v.condition = VehicleCondition.AT_STATION
        v.time_stopped = 0.0


def _handle_stopped(sim: "Simulator", v: Vehicle, dt: float):
    """Gere veículo parado."""
    
    if v.condition == VehicleCondition.UNAVAILABLE:
        # Avariado: a cumprir tempo de penalidade
        v.time_stopped += dt
        if v.time_stopped >= PENALTY_TIME:
            # Penalidade cumprida, volta ao serviço
            v.condition = VehicleCondition.AVAILABLE
            v.remaining_km = sim.LOW_AUTONOMY_THRESHOLD
            v.time_stopped = 0.0
            sim.assignment_needed = True

    elif v.condition == VehicleCondition.AVAILABLE:
        # Disponível: verifica se precisa de ir abastecer
        if v.remaining_km < sim.LOW_AUTONOMY_THRESHOLD:
            _go_to_station(sim, v)

    elif v.condition == VehicleCondition.AT_STATION:
        # Na estação: a carregar/abastecer
        _refuel(sim, v, dt)


def _refuel(sim: "Simulator", v: Vehicle, dt: float):
    """Recarrega/reabastece veículo."""
    v.time_stopped += dt
    v.total_station_time += dt

    if v.motor == Motor.ELECTRIC:
        # EV: carregamento progressivo
        sim.stats.step_station_time_ev += dt
        rate = v.position_node.energy_recharge_rate_kw or 300.0
        v.remaining_km += dt * (rate / 60.0)

        if v.remaining_km >= v.max_km:
            # Carregamento completo
            v.remaining_km = v.max_km
            v.condition = VehicleCondition.AVAILABLE
            v.time_stopped = 0.0
            sim.assignment_needed = True
    else:
        # Combustão: reabastecimento fixo de 5 minutos
        sim.stats.step_station_time_gas += dt
        if v.time_stopped >= GAS_REFUEL_MINUTES:
            # Reabastecimento completo
            v.remaining_km = v.max_km
            v.condition = VehicleCondition.AVAILABLE
            v.time_stopped = 0.0
            sim.assignment_needed = True


def _go_to_station(sim: "Simulator", v: Vehicle):
    """Procura estação mais próxima e define rota."""
    stations = sim.map.ev_stations if v.motor == Motor.ELECTRIC else sim.map.gas_stations
    available = [s for s in stations if s.is_available]

    if not available:
        print(f"[Aviso] Sem estações disponíveis para {v.id}")
        return

    # Ordena por distância e pega nas 3 mais próximas
    candidates = sorted(available, key=lambda n: _heuristic_distance(v.position_node, n))[:3]

    best_path, best_station = None, None
    min_time = float("inf")

    # Procura a melhor estação alcançável
    for station in candidates:
        info = find_route("astar", sim.map, v.position_node, station)
        if info:
            path, time, dist = info
            if v.remaining_km > dist and time < min_time:
                min_time = time
                best_path = path
                best_station = station

    if best_path:
        v.current_route = best_path
        v.current_segment_index = 0
        v.current_segment_progress_time = 0.0
        v.condition = VehicleCondition.ON_WAY_TO_STATION
    else:
        # Não consegue chegar a nenhuma estação
        print(f"[Aviso] {v.id} não consegue chegar a estação com {v.remaining_km:.0f}km")
        v.condition = VehicleCondition.ON_WAY_TO_STATION


def _update_coords(v: Vehicle, start: Node, end: Node, total_time: float):
    """Actualiza coordenadas GUI baseado no progresso."""
    progress = v.current_segment_progress_time / total_time if total_time > 0 else 1.0
    progress = max(0.0, min(1.0, progress))
    x1, y1 = start.position
    x2, y2 = end.position
    v.map_coordinates = (x1 + (x2 - x1) * progress, y1 + (y2 - y1) * progress)


def _record_stats(sim: "Simulator", v: Vehicle, dist: float):
    """Regista estatísticas de movimento."""
    s = sim.stats
    s.step_operational_cost += dist * v.price_per_km
    s.step_kms_driven += dist

    if v.motor == Motor.ELECTRIC:
        s.step_kms_driven_ev += dist
    else:
        s.step_kms_driven_gas += dist
        co2 = (dist * CO2_G_PER_KM) / 1000.0
        v.co2_emitted += co2
        s.step_co2_emitted += co2

    if v.condition == VehicleCondition.ON_TRIP_WITH_CLIENT:
        # Km com passageiro
        s.step_kms_driven_with_passenger += dist
    elif v.condition in [VehicleCondition.ON_WAY_TO_CLIENT, VehicleCondition.ON_WAY_TO_STATION]:
        # Km em vazio
        s.step_kms_driven_empty += dist
        if v.motor == Motor.ELECTRIC:
            s.step_kms_driven_empty_ev += dist
        else:
            s.step_kms_driven_empty_gas += dist
