from enum import Enum, auto
from typing import Optional, List, Tuple


class Node:
    def __init__(
        self,
        position: Tuple[int, int],
        gas_pumps: int = 0,
        energy_chargers: int = 0,
        energy_recharge_rate_km_h: int = 0,
    ) -> None:
        self.position = position
        self.gas_pumps = gas_pumps
        self.energy_chargers = energy_chargers
        self.energy_recharge_rate_kw = energy_recharge_rate_km_h

    def __str__(self) -> str:
        base = f"Node at {self.position}"
        details = []
        if self.gas_pumps > 0:
            details.append(f"Gas({self.gas_pumps} pumps)")
        if self.energy_chargers > 0:
            details.append(f"EV({self.energy_chargers} chargers)")

        if details:
            return f"{base} [{', '.join(details)}]"
        return base

    def __repr__(self) -> str:
        return (
            f"Node(position={self.position}, "
            f"gas_pumps={self.gas_pumps}, "
            f"energy_chargers={self.energy_chargers}, "
            f"energy_recharge_rate_kw={self.energy_recharge_rate_kw})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.position == other.position

    def __hash__(self) -> int:
        return hash(self.position)


class Motor(Enum):
    ELECTRIC = auto()
    COMBUSTION = auto()


class VehicleCondition(Enum):
    AVAILABLE = auto()
    ON_WAY_TO_CLIENT = auto()
    ON_TRIP_WITH_CLIENT = auto()
    ON_WAY_TO_STATION = auto()
    AT_STATION = auto()
    UNAVAILABLE = auto()


class Request:
    id_counter = 1

    def __init__(
        self,
        start_node: Node,
        end_node: Node,
        passenger_capacity: int,
        creation_time: float,
        price: float,
        priority: int = 1,  # (1=low, 5=high)
        environmental_preference: bool = False,  # Electric preference
    ) -> None:
        self.id = Request.id_counter
        Request.id_counter += 1
        self.start_node = start_node
        self.end_node = end_node
        self.passenger_capacity = passenger_capacity
        self.creation_time = creation_time
        self.price = price
        self.priority = priority
        self.environmental_preference = environmental_preference

    def __repr__(self) -> str:
        return (
            f"Request(id={self.id}, from={self.start_node.position}, "
            f"to={self.end_node.position}, pax={self.passenger_capacity}), price=€{self.price:.2f}"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, Request):
            return NotImplemented
        return self.id == other.id

    def __lt__(self, other):
        if not isinstance(other, Request):
            return NotImplemented
        return self.id < other.id


class Vehicle:
    def __init__(
        self,
        id: str,
        motor: Motor,
        position_node: Node,
        passenger_capacity: int,
        price_per_km: float,
        max_km: float,
        remaining_km: float = 0,
        condition: VehicleCondition = VehicleCondition.AVAILABLE,
        current_route: Optional[List[Node]] = None,
        request: Optional[Request] = None,
    ) -> None:
        self.id = id
        self.motor = motor
        self.position_node = position_node
        self.passenger_capacity = passenger_capacity
        self.price_per_km = price_per_km
        self.max_km = max_km
        self.remaining_km = remaining_km
        self.condition = condition
        self.times_borken = 0

        if self.remaining_km > self.max_km:
            self.remaining_km = self.max_km

        self.request = request
        self.current_route = current_route if current_route is not None else []

        # This index points to the START node of the current segment
        # Example: index 0 means moving from route[0] to route[1]
        self.current_segment_index = 0
        self.current_segment_progress_time: float = 0.0

        self.time_stopped: float = 0.0  # Time penalty

        # Coordinate for the GUI
        self.map_coordinates: Tuple[float, float] = position_node.position

    def __repr__(self) -> str:
        return (
            f"Vehicle(id={self.id}, "
            f"motor={self.motor.name}, "
            f"loc={self.position_node.position}, "
            f"condition={self.condition.name})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, Vehicle):
            return NotImplemented
        return self.id == other.id


class SimulationStats:
    def __init__(self):
        # Total Stats
        self.total_operational_cost: float = 0.0
        self.total_revenue_generated: float = 0.0
        self.total_kms_driven: float = 0.0
        self.total_kms_driven_with_passenger: float = 0.0
        self.total_kms_driven_empty: float = 0.0

        self.total_requests_completed: int = 0
        self.total_requests_failed: int = 0

        # (Criação -> Entrega) ---
        self.total_time_for_completed_requests: float = 0.0  # (Já existia)
        self.min_total_trip_time: float = float("inf")
        self.max_total_trip_time: float = 0.0

        # (Criação -> Recolha) ---
        self.total_requests_picked_up: int = 0
        self.total_wait_time_for_pickup: float = 0.0
        self.min_wait_time: float = float("inf")
        self.max_wait_time: float = 0.0

        # Framte Stats
        self.step_assignment_cost: float = 0.0  # Search price
        self.step_operational_cost: float = 0.0
        self.step_revenue_generated: float = 0.0
        self.step_kms_driven: float = 0.0
        self.step_kms_driven_with_passenger: float = 0.0
        self.step_kms_driven_empty: float = 0.0

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
        self.step_kms_driven_with_passenger = 0.0
        self.step_kms_driven_empty = 0.0

        self.step_pending_requests = 0
        self.step_vehicles_available = 0
        self.step_vehicles_on_trip = 0
        self.step_vehicles_charging = 0
        self.step_vehicles_unavailable = 0
