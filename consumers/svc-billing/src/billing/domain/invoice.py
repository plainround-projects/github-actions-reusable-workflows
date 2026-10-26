"""An invoice prices lines with :class:`~decimal.Decimal`; tax is rounded half-even to the cent, once."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

CENT = Decimal("0.01")


class InvoiceError(ValueError):
    """The invoice breaks a rule: no lines, a bad quantity, a negative price or an impossible tax rate."""


@dataclass(frozen=True, slots=True)
class InvoiceLine:
    """A quantity of one item at a unit price."""

    description: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise InvoiceError(f"quantity of {self.description} must be at least 1")
        if self.unit_price < 0:
            raise InvoiceError(f"price of {self.description} must not be negative")

    @property
    def amount(self) -> Decimal:
        """Quantity times unit price, exact."""
        return self.unit_price * self.quantity


@dataclass(frozen=True, slots=True)
class Invoice:
    """Lines plus a tax rate between 0 and 1."""

    invoice_id: str
    lines: tuple[InvoiceLine, ...]
    tax_rate: Decimal

    def __post_init__(self) -> None:
        if not self.lines:
            raise InvoiceError("an invoice needs at least one line")
        if not Decimal(0) <= self.tax_rate <= Decimal(1):
            raise InvoiceError("tax rate must be between 0 and 1")

    @property
    def subtotal(self) -> Decimal:
        """Sum of the line amounts, rounded to the cent."""
        return sum((line.amount for line in self.lines), Decimal(0)).quantize(CENT, ROUND_HALF_EVEN)

    @property
    def tax(self) -> Decimal:
        """Tax on the subtotal, rounded half-even to the cent."""
        return (self.subtotal * self.tax_rate).quantize(CENT, ROUND_HALF_EVEN)

    @property
    def total(self) -> Decimal:
        """Subtotal plus tax."""
        return self.subtotal + self.tax
