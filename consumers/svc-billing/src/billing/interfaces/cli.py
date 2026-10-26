"""``python -m billing INVOICE_ID TAX_RATE DESCRIPTION:QUANTITY:UNIT_PRICE ...`` prints the invoice totals."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from billing.application.issue_invoice import IssueInvoice
from billing.domain.invoice import InvoiceError
from billing.infrastructure.memory_repository import InMemoryInvoices


def main(argv: Sequence[str] | None = None) -> int:
    """Run the program; return 0 on success and 1 when the invoice is invalid."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 3:
        print("usage: python -m billing INVOICE_ID TAX_RATE DESCRIPTION:QUANTITY:UNIT_PRICE ...", file=sys.stderr)
        return 2
    try:
        lines = [(item, int(quantity), price) for item, quantity, price in (part.split(":") for part in args[2:])]
        invoice = IssueInvoice(InMemoryInvoices())(args[0], args[1], lines)
    except (InvoiceError, ValueError) as error:
        print(f"billing: {error}", file=sys.stderr)
        return 1
    print(f"{invoice.invoice_id}: subtotal {invoice.subtotal} tax {invoice.tax} total {invoice.total}")
    return 0
