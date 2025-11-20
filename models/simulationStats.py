class SimulationStats:
    def __init__(self):
        # Total Stats
        self.total_operational_cost: float = 0.0
        self.total_revenue_generated: float = 0.0
        self.total_kms_driven: float = 0.0
        self.total_kms_driven_with_passenger: float = 0.0
        self.total_kms_driven_empty: float = 0.0
        self.total_kms_driven_ev: float = 0.0
        self.total_kms_driven_gas: float = 0.0
        self.total_kms_driven_empty_ev: float = 0.0
        self.total_kms_driven_empty_gas: float = 0.0

        self.total_requests_completed: int = 0
        self.total_requests_failed: int = 0
        self.total_requests_cancelled_timeout: int = 0
        self.total_co2_emitted: float = 0.0
        self.total_station_time_ev: float = 0.0
        self.total_station_time_gas: float = 0.0

        # Criação -> Entrega
        self.total_time_for_completed_requests: float = 0.0
        self.min_total_trip_time: float = float("inf")
        self.max_total_trip_time: float = 0.0

        # Criação -> Recolha
        self.total_requests_picked_up: int = 0
        self.total_wait_time_for_pickup: float = 0.0
        self.min_wait_time: float = float("inf")
        self.max_wait_time: float = 0.0

        # Frame Stats
        self.step_assignment_cost: float = 0.0
        self.step_operational_cost: float = 0.0
        self.step_revenue_generated: float = 0.0
        self.step_kms_driven: float = 0.0
        self.step_kms_driven_ev: float = 0.0
        self.step_kms_driven_gas: float = 0.0
        self.step_kms_driven_with_passenger: float = 0.0
        self.step_kms_driven_empty: float = 0.0
        self.step_kms_driven_empty_ev: float = 0.0
        self.step_kms_driven_empty_gas: float = 0.0
        self.step_co2_emitted: float = 0.0

        self.step_station_time_ev: float = 0.0
        self.step_station_time_gas: float = 0.0
        self.step_requests_cancelled_timeout: int = 0

        self.step_pending_requests: int = 0
        self.step_vehicles_available: int = 0
        self.step_vehicles_on_trip: int = 0
        self.step_vehicles_charging: int = 0
        self.step_vehicles_unavailable: int = 0

    def reset_step_metrics(self):
        # Clear old frame values
        self.step_assignment_cost = 0.0
        self.step_operational_cost = 0.0
        self.step_revenue_generated = 0.0
        self.step_kms_driven = 0.0
        self.step_kms_driven_ev = 0.0
        self.step_kms_driven_gas = 0.0
        self.step_kms_driven_with_passenger = 0.0
        self.step_kms_driven_empty = 0.0
        self.step_kms_driven_empty_ev = 0.0
        self.step_kms_driven_empty_gas = 0.0
        self.step_co2_emitted = 0.0

        self.step_station_time_ev = 0.0
        self.step_station_time_gas = 0.0
        self.step_requests_cancelled_timeout = 0

        self.step_pending_requests = 0
        self.step_vehicles_available = 0
        self.step_vehicles_on_trip = 0
        self.step_vehicles_charging = 0
        self.step_vehicles_unavailable = 0
