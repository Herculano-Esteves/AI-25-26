from mapGen import (
    generate_map,
    create_vehicle_fleet,
    generate_requests,
)
from models.vehicle import Vehicle, VehicleCondition
from models.request import Request
from models.simulationStats import SimulationStats
from typing import List
import random

from Simulation.vehicle_simulation import manage_vehicle
from Simulation.request_simulation import (
    assign_pending_requests,
    generate_new_requests_if_needed,
)
from Simulation.hotspots import HotspotManager


class Simulator:
    # Simulation Constants
    MAP_WIDTH = 20
    MAP_HEIGHT = 20
    # Time constants
    SIM_TIME_PER_TICK = 1  # Base time in minutes per frame
    MINUTES_PER_HOUR = 60
    HOURS_PER_DAY = 24
    MINUTES_PER_DAY = MINUTES_PER_HOUR * HOURS_PER_DAY
    MINUTES_PER_YEAR = MINUTES_PER_DAY * 365
    LOW_AUTONOMY_THRESHOLD = 50.0
    NUM_EV_VEHICLES = 3
    NUM_GAS_VEHICLES = 3
    NUM_INITIAL_REQUESTS = 10
    NUM_REQUESTS_TO_GENERATE = 4
    STATION_FAILURE_PROB_PER_TICK = 0.0001  # Prob of a station to fail per tick
    STATION_DOWNTIME_MINUTES = 120.0

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
        self.map = generate_map()

        self.hotspot_manager = HotspotManager(self.map)

        all_nodes = list(self.map.nos)

        self.vehicles = create_vehicle_fleet(all_nodes, self.NUM_EV_VEHICLES, self.NUM_GAS_VEHICLES)

        self.current_time = 0.0  # 00:00

        self.requests = generate_requests(
            self.map, all_nodes, self.NUM_INITIAL_REQUESTS, self.current_time
        )

        self.requests_to_pickup = []
        self.requests_to_dropoff = []

        self.stats = SimulationStats()

    def simulation_step(self, time_multiplier: float = 1.0):
        """
        Executes one step of simulation.
        :param time_multiplier: Multiplier for the time passage (1.0 = normal, 2.0 = double speed)
        """
        # Apply the multiplier to the base tick time
        time_to_advance = self.SIM_TIME_PER_TICK * time_multiplier

        self.current_time += time_to_advance
        self.stats.reset_step_metrics()

        # Update Hotspots based on the time
        current_hour = self.get_current_hour()
        self.hotspot_manager.update(current_hour)

        for v in self.vehicles:
            manage_vehicle(self, v, time_to_advance)

        self._update_station_failures(time_to_advance)

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
        self.stats.total_kms_driven_with_passenger += self.stats.step_kms_driven_with_passenger
        self.stats.total_kms_driven_empty += self.stats.step_kms_driven_empty

    def _update_station_failures(self, time_to_advance: float):
        stations_to_check = []
        stations_to_check.extend(self.map.gas_stations)
        stations_to_check.extend(self.map.ev_stations)

        for node in stations_to_check:
            if node.is_available:
                if random.random() < self.STATION_FAILURE_PROB_PER_TICK:
                    node.is_available = False
                    node.time_down = 0.0
                    print(f"[Station Failure] Estação em {node.position} falhou!")
            else:
                node.time_down += time_to_advance
                if node.time_down >= self.STATION_DOWNTIME_MINUTES:
                    node.is_available = True
                    node.time_down = 0.0
                    print(f"[Station Repair] Estação em {node.position} está operacional.")

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
