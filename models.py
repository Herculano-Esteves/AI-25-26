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
    AT_STATION = auto()
    UNAVAILABLE = auto()


class Request:
    id_counter = 1

    def __init__(
        self,
        start_node: Node,
        end_node: Node,
        passenger_capacity: int,
        priority: int = 1,  # (1=low, 5=high)
        environmental_preference: bool = False,  # Electric preference
    ) -> None:
        self.id = Request.id_counter
        Request.id_counter += 1
        self.start_node = start_node
        self.end_node = end_node
        self.passenger_capacity = passenger_capacity
        self.priority = priority
        self.environmental_preference = environmental_preference

    def __repr__(self) -> str:
        return (
            f"Request(id={self.id}, from={self.start_node.position}, "
            f"to={self.end_node.position}, pax={self.passenger_capacity})"
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
        route_to_do: Optional[List[Node]] = None,
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
        self.total_request_km: float = 0.0

        if self.remaining_km > self.max_km:
            self.remaining_km = self.max_km

        self.route_to_do = route_to_do if route_to_do is not None else []
        self.request = request

        self.map_coordinates: Tuple[float, float] = position_node.position

        # Animation / movement attributes
        self.start_node: Optional[Node] = None
        self.end_node: Optional[Node] = None

        self.extimated_trip_time: float = (
            0.0  # Total time in minutes for the current trip
        )
        self.time_passed_on_trip: float = (
            0.0  # Total minutes passed since the start of the trip
        )

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
