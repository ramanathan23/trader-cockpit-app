from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class Currency(str, Enum):
    INR = "INR"


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency = Currency.INR

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: int | float | Decimal) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __truediv__(self, divisor: int | float | Decimal) -> "Money":
        return Money(self.amount / Decimal(str(divisor)), self.currency)

    def __lt__(self, other: "Money") -> bool:
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        return self.amount >= other.amount

    def is_zero(self) -> bool:
        return self.amount == Decimal("0")

    def is_negative(self) -> bool:
        return self.amount < Decimal("0")

    def abs(self) -> "Money":
        return Money(abs(self.amount), self.currency)

    @classmethod
    def zero(cls) -> "Money":
        return cls(amount=Decimal("0"))

    @classmethod
    def from_float(cls, value: float, currency: Currency = Currency.INR) -> "Money":
        return cls(amount=Decimal(str(round(value, 2))), currency=currency)

    def to_float(self) -> float:
        return float(self.amount)

    def __repr__(self) -> str:
        return f"₹{self.amount:,.2f}"
