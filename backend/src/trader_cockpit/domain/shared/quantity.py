from dataclasses import dataclass


@dataclass(frozen=True)
class Quantity:
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int):
            object.__setattr__(self, "value", int(self.value))
        if self.value <= 0:
            raise ValueError(f"Quantity must be positive: {self.value}")

    def __add__(self, other: "Quantity") -> "Quantity":
        return Quantity(self.value + other.value)

    def __sub__(self, other: "Quantity") -> "Quantity":
        result = self.value - other.value
        if result <= 0:
            raise ValueError(f"Quantity subtraction resulted in non-positive: {result}")
        return Quantity(result)

    def __lt__(self, other: "Quantity") -> bool:
        return self.value < other.value

    def __le__(self, other: "Quantity") -> bool:
        return self.value <= other.value

    def __gt__(self, other: "Quantity") -> bool:
        return self.value > other.value

    def __ge__(self, other: "Quantity") -> bool:
        return self.value >= other.value
