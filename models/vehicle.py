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

    # Tiny optimization
    __slots__ = (
        "id",
        "motor",
        "position_node",
        "passenger_capacity",
        "price_per_km",
        "max_km",
        "remaining_km",
        "condition",
        "times_borken",
        "request",
        "current_route",
        "current_segment_index",
        "current_segment_progress_time",
        "time_stopped",
        "map_coordinates",
        "co2_emitted",
        "total_station_time",
        "total_trips",
        "sum_occupancy",
    )

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
        self.current_segment_index = 0
        self.current_segment_progress_time: float = 0.0

        self.time_stopped: float = 0.0  # Time penalty
        self.total_station_time: float = 0.0  #  Total time spent refueling
        self.co2_emitted: float = 0.0  # Total CO2 emitted

        self.total_trips: int = 0
        self.sum_occupancy: float = 0.0

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
