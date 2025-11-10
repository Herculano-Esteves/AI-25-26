from models.node import Node
from typing import Optional, List


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
        path: Optional[List[Node]] = None,
        path_distance: float = 0.0,
        path_time: float = 0.0,
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
        self.path = path
        self.path_distance = path_distance
        self.path_time = path_time

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
