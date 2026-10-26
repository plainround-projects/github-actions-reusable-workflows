"""An order is an id and one or more lines; prices are whole cents so no float ever touches money."""

from __future__ import annotations

from dataclasses import dataclass


class OrderError(ValueError):
    """The order breaks a rule: no lines, a non-positive quantity or a negative price."""


@dataclass(frozen=True, slots=True)
class OrderLine:
    """A quantity of one SKU at a price per unit, in cents."""

    sku: str
    quantity: int
    unit_price_cents: int

    def __post_init__(self) -> None:
        if not self.sku:
            raise OrderError("a line needs a sku")
        if self.quantity < 1:
            raise OrderError(f"quantity of {self.sku} must be at least 1")
        if self.unit_price_cents < 0:
            raise OrderError(f"price of {self.sku} must not be negative")

    @property
    def total_cents(self) -> int:
        """Quantity times unit price."""
        return self.quantity * self.unit_price_cents


@dataclass(frozen=True, slots=True)
class Order:
    """An order with at least one line."""

    order_id: str
    lines: tuple[OrderLine, ...]

    def __post_init__(self) -> None:
        if not self.lines:
            raise OrderError("an order needs at least one line")

    @property
    def total_cents(self) -> int:
        """Sum of the line totals."""
        return sum(line.total_cents for line in self.lines)
