from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Price:
    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))
        if self.value <= 0:
            raise ValueError(f"Price must be positive: {self.value}")

    def pct_diff(self, other: "Price") -> Decimal:
        """Returns percentage difference from other to self."""
        if other.value == 0:
            raise ZeroDivisionError("Cannot compute pct_diff from zero price")
        return ((self.value - other.value) / other.value) * 100

    def __lt__(self, other: "Price") -> bool:
        return self.value < other.value

    def __le__(self, other: "Price") -> bool:
        return self.value <= other.value

    def __gt__(self, other: "Price") -> bool:
        return self.value > other.value

    def __ge__(self, other: "Price") -> bool:
        return self.value >= other.value

    def to_float(self) -> float:
        return float(self.value)

    @classmethod
    def from_float(cls, value: float) -> "Price":
        return cls(value=Decimal(str(round(value, 2))))
