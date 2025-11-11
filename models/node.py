from typing import Tuple


class Node:
    def __init__(
        self,
        position: Tuple[float, float],
        gas_pumps: int = 0,
        energy_chargers: int = 0,
        energy_recharge_rate_km_h: int = 0,
        is_available: bool = True,
        time_down: float = 0.0,
    ) -> None:
        self.position = position
        self.gas_pumps = gas_pumps
        self.energy_chargers = energy_chargers
        self.energy_recharge_rate_kw = energy_recharge_rate_km_h
        self.is_available = is_available
        self.time_down = time_down

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
