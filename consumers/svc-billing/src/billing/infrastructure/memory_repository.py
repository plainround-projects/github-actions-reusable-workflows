"""In-memory invoice storage."""

from __future__ import annotations

from billing.domain.invoice import Invoice


class InMemoryInvoices:
    """Keeps invoices in a dictionary for the lifetime of the process."""

    def __init__(self) -> None:
        self._invoices: dict[str, Invoice] = {}

    def add(self, invoice: Invoice) -> None:
        """Store ``invoice``; raise ``KeyError`` when the id is already taken."""
        if invoice.invoice_id in self._invoices:
            raise KeyError(f"invoice {invoice.invoice_id} already exists")
        self._invoices[invoice.invoice_id] = invoice
