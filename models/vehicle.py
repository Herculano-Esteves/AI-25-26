from enum import Enum, auto
from typing import Optional, List, Tuple, TYPE_CHECKING
from models.node import Node

if TYPE_CHECKING:
    from models.request import Request


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
        request: Optional["Request"] = None,
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
