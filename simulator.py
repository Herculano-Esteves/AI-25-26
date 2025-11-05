from mapGen import (
    generate_map,
    generate_random_request,
    create_vehicle_fleet,
    generate_requests,
)
from search import find_a_star_route, _heuristic_distance
from models import VehicleCondition, Vehicle, Request, Node
from typing import List


class Simulator:
    # Simulation Constants
    MAP_WIDTH = 20
    MAP_HEIGHT = 20
    SIM_TIME_PER_TICK = 0.1  # Time in minutes per frame
    LOW_AUTONOMY_THRESHOLD = 50.0
    NUM_EV_VEHICLES = 3
    NUM_GAS_VEHICLES = 3
    NUM_INITIAL_REQUESTS = 5
    NUM_REQUESTS_TO_GENERATE = 4

    def __init__(self):
        # Variables
        self.map = None
        self.vehicles: List[Vehicle] = []
        self.requests: List[Request] = []
        self.requests_to_pickup: List[Request] = []
        self.requests_to_dropoff: List[Request] = []

        # Setup
        self.setup_new_map()

    def setup_new_map(self):
        print("A criar novo map...")
        # 1. Generate the map graph
        self.map = generate_map(self.MAP_WIDTH, self.MAP_HEIGHT, 0.02, 0.005)

        all_nodes = list(self.map.nos)

        # 2. Generate the vehicle fleet
        self.vehicles = create_vehicle_fleet(
            all_nodes, self.NUM_EV_VEHICLES, self.NUM_GAS_VEHICLES
        )

        # 3. Generate the initial requests
        self.requests = generate_requests(all_nodes, self.NUM_INITIAL_REQUESTS)

        self.requests_to_pickup = []
        self.requests_to_dropoff = []

    def simulation_step(self):
        time_to_advance = self.SIM_TIME_PER_TICK

        # 1. Manage movement and state for each vehicle
        for v in self.vehicles:
            self._manage_vehicle(v, time_to_advance)

        # 2. Assign pending requests to available vehicles
        self._assign_pending_requests()

        # 3. Generate new requests if the queue is empty
        self._generate_new_requests_if_needed()

    def _manage_vehicle(self, v: Vehicle, time_to_advance: float):
        self._update_vehicle_movement(v, time_to_advance)

        # If the vehicle is not moving, manage its state.
        if not v.end_node:
            self._manage_stopped_vehicle(v)

    def _assign_pending_requests(self):
        if not self.requests:
            return

        available_vehicles = [
            v for v in self.vehicles if v.condition == VehicleCondition.AVAILABLE
        ]

        if not available_vehicles:
            return

        # Iterate over a copy of the list to allow removal
        for request in self.requests[:]:
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
                self.requests.remove(request)
                available_vehicles.remove(best_vehicle)
                self._assign_request_to_vehicle(request, best_vehicle)

    def _generate_new_requests_if_needed(self):
        if not self.requests:
            print(
                f"[Simulação] Fila de requests vazia. A gerar {self.NUM_REQUESTS_TO_GENERATE} novos requests."
            )
            for _ in range(self.NUM_REQUESTS_TO_GENERATE):
                self.requests.append(generate_random_request(list(self.map.nos)))

    def _update_vehicle_movement(self, v: Vehicle, time_to_advance: float):
        # Updates the position of a vehicle in transit between two nodes
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
            x1, y1 = v.start_node.position
            x2, y2 = v.end_node.position
            new_x = x1 + (x2 - x1) * progress
            new_y = y1 + (y2 - y1) * progress
            v.map_coordinates = (new_x, new_y)

    def _manage_stopped_vehicle(self, v: Vehicle):
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

                edge_info = self.map.connection_weight(v.start_node, v.end_node)
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
            self._manage_state_on_way_to_client(v)

        elif v.condition == VehicleCondition.ON_TRIP_WITH_CLIENT:
            self._manage_state_on_trip(v)

        elif v.condition == VehicleCondition.AVAILABLE:
            # TODO: Check if it needs to refuel
            # if v.remaining_km < self.LOW_AUTONOMY_THRESHOLD:
            #    _find_station_and_set_route(v)
            pass

    def _assign_request_to_vehicle(self, request: Request, v: Vehicle):
        self.requests_to_pickup.append(request)
        v.request = request
        v.condition = VehicleCondition.ON_WAY_TO_CLIENT

        print(
            f"[Assignment] {v.id} (mais próximo) aceitou {request.id}. "
            f"A caminho de {request.start_node.position}"
        )

        path = find_a_star_route(self.map, v.position_node, request.start_node)
        v.route_to_do = path if path else []

    def _manage_state_on_way_to_client(self, v: Vehicle):
        print(
            f"{v.id} em {v.position_node.position}. A iniciar viagem para {v.request.end_node.position}"
        )

        self.requests_to_pickup.remove(v.request)
        self.requests_to_dropoff.append(v.request)
        v.condition = VehicleCondition.ON_TRIP_WITH_CLIENT

        # Calculate the route to the final end_node
        path = find_a_star_route(self.map, v.position_node, v.request.end_node)
        v.route_to_do = path if path else []

    def _manage_state_on_trip(self, v: Vehicle):
        print(
            f"{v.id} completou a viagem em {v.position_node.position}. Disponível."
            f"Autonomia restante: {v.remaining_km:.1f} km"
        )
        self.requests_to_dropoff.remove(v.request)
        v.condition = VehicleCondition.AVAILABLE
        v.request = None
        v.route_to_do = []
