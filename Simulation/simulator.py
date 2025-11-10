from mapGen import (
    generate_map,
    generate_random_request,
    create_vehicle_fleet,
    generate_requests,
)
from models import Vehicle, Request, Node, SimulationStats, VehicleCondition
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
    # Time constants
    SIM_TIME_PER_TICK = 0.5  # Time in minutes per frame
    MINUTES_PER_HOUR = 60
    HOURS_PER_DAY = 24
    MINUTES_PER_DAY = MINUTES_PER_HOUR * HOURS_PER_DAY
    MINUTES_PER_YEAR = MINUTES_PER_DAY * 365
    LOW_AUTONOMY_THRESHOLD = 50.0
    NUM_EV_VEHICLES = 3
    NUM_GAS_VEHICLES = 3
    NUM_INITIAL_REQUESTS = 10
    NUM_REQUESTS_TO_GENERATE = 4

    def __init__(self):
        self.vehicles: List[Vehicle] = []
        self.requests: List[Request] = []
        self.requests_to_pickup: List[Request] = []
        self.requests_to_dropoff: List[Request] = []

        self.current_time: float = 0.0
        self.stats = SimulationStats()

        self.setup_new_map()

    def setup_new_map(self):
        print("A criar novo mapa...")
        self.map = generate_map(self.MAP_WIDTH, self.MAP_HEIGHT, 0.02, 0.005)

        all_nodes = list(self.map.nos)

        self.vehicles = create_vehicle_fleet(all_nodes, self.NUM_EV_VEHICLES, self.NUM_GAS_VEHICLES)

        self.requests = generate_requests(
            self.map, all_nodes, self.NUM_INITIAL_REQUESTS, self.current_time
        )

        self.requests_to_pickup = []
        self.requests_to_dropoff = []

        self.current_time = 0.0
        self.stats = SimulationStats()

    def simulation_step(self):
        time_to_advance = self.SIM_TIME_PER_TICK

        self.current_time += time_to_advance
        self.stats.reset_step_metrics()

        for v in self.vehicles:
            manage_vehicle(self, v, time_to_advance)

        generate_new_requests_if_needed(self)
        assign_pending_requests(self)

        self._calculate_step_stats(time_to_advance)

    def _calculate_step_stats(self, time_to_advance: float):
        self.stats.step_pending_requests = len(self.requests)

        # State of the vehicles
        for v in self.vehicles:
            if v.condition == VehicleCondition.AVAILABLE:
                self.stats.step_vehicles_available += 1
            elif v.condition in [
                VehicleCondition.ON_WAY_TO_CLIENT,
                VehicleCondition.ON_TRIP_WITH_CLIENT,
            ]:
                self.stats.step_vehicles_on_trip += 1
            elif v.condition in [VehicleCondition.ON_WAY_TO_STATION, VehicleCondition.AT_STATION]:
                self.stats.step_vehicles_charging += 1
            elif v.condition == VehicleCondition.UNAVAILABLE:
                self.stats.step_vehicles_unavailable += 1

        # Total values
        self.stats.total_kms_driven += self.stats.step_kms_driven
        self.stats.total_operational_cost += self.stats.step_operational_cost
        self.stats.total_revenue_generated += self.stats.step_revenue_generated
        self.stats.total_kms_driven_with_passenger += self.stats.step_kms_driven_with_passenger
        self.stats.total_kms_driven_empty += self.stats.step_kms_driven_empty

    def get_current_time_of_day(self) -> tuple[int, int, int, int]:
        # return day, hour, minute, year
        current_year = int(self.current_time // self.MINUTES_PER_YEAR)
        minutes_into_year = self.current_time % self.MINUTES_PER_YEAR
        current_day = int(minutes_into_year // self.MINUTES_PER_DAY)
        minutes_into_day = minutes_into_year % self.MINUTES_PER_DAY
        current_hour = int(minutes_into_day // self.MINUTES_PER_HOUR)
        current_minute = int(minutes_into_day % self.MINUTES_PER_HOUR)
        return (current_day, current_hour, current_minute, current_year)

    def get_current_hour(self) -> int:
        minutes_into_day = self.current_time % self.MINUTES_PER_DAY
        current_hour = int(minutes_into_day // self.MINUTES_PER_HOUR)
        return current_hour
