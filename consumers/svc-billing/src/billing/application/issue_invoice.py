"""Use case: issue an invoice and keep it."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Protocol

from billing.domain.invoice import Invoice, InvoiceError, InvoiceLine


class InvoiceRepository(Protocol):
    """Where issued invoices are kept."""

    def add(self, invoice: Invoice) -> None:
        """Store ``invoice``; raise ``KeyError`` when the id is already taken."""
        ...


class IssueInvoice:
    """Build an invoice from raw text values and store it."""

    def __init__(self, repository: InvoiceRepository) -> None:
        self._repository = repository

    def __call__(self, invoice_id: str, tax_rate: str, lines: list[tuple[str, int, str]]) -> Invoice:
        """Issue the invoice; invalid data raises :class:`~billing.domain.invoice.InvoiceError`."""
        try:
            invoice = Invoice(
                invoice_id,
                tuple(InvoiceLine(description, quantity, Decimal(price)) for description, quantity, price in lines),
                Decimal(tax_rate),
            )
        except InvalidOperation as error:
            raise InvoiceError(f"not a decimal number: {error}") from error
        self._repository.add(invoice)
        return invoice
