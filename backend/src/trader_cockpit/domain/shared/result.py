from dataclasses import dataclass
from typing import TypeVar, Generic, Callable

T = TypeVar("T")
E = TypeVar("E")


@dataclass
class Ok(Generic[T]):
    value: T
    is_ok: bool = True
    is_err: bool = False

    def map(self, fn: Callable[[T], T]) -> "Ok[T]":
        return Ok(fn(self.value))

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:  # noqa: ARG002
        return self.value


@dataclass
class Err(Generic[E]):
    error: E
    is_ok: bool = False
    is_err: bool = True

    def map(self, fn: Callable) -> "Err[E]":
        return self  # errors pass through unchanged

    def unwrap(self) -> None:
        raise RuntimeError(f"Called unwrap() on Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        return default


# Type alias — Result is either Ok[T] or Err[str]
type Result[T] = Ok[T] | Err[str]
