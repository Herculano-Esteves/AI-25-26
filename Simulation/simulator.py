from mapGen import (
    generate_map,
    generate_random_request,
    create_vehicle_fleet,
    generate_requests,
)
from models import Vehicle, Request, Node
from typing import List

from Simulation.vehicle_simulation import manage_vehicle
from Simulation.request_simulation import (
    assign_pending_requests,
    generate_new_requests_if_needed,
)


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

        for v in self.vehicles:
            manage_vehicle(self, v, time_to_advance)

        assign_pending_requests(self)
        generate_new_requests_if_needed(self)
