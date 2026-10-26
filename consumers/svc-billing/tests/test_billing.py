from decimal import Decimal

import pytest

from billing.application.issue_invoice import IssueInvoice
from billing.domain.invoice import Invoice, InvoiceError, InvoiceLine
from billing.infrastructure.memory_repository import InMemoryInvoices
from billing.interfaces.cli import main


def invoice(rate="0.0825"):
    return Invoice("i-1", (InvoiceLine("widget", 3, Decimal("19.99")),), Decimal(rate))


def test_the_subtotal_is_exact_and_the_tax_is_rounded_half_even_once():
    assert invoice().subtotal == Decimal("59.97")
    assert invoice().tax == Decimal("4.95")
    assert invoice().total == Decimal("64.92")


def test_half_a_cent_rounds_to_the_even_cent():
    assert Invoice("i-2", (InvoiceLine("x", 1, Decimal("0.25")),), Decimal("0.10")).tax == Decimal("0.02")
    assert Invoice("i-3", (InvoiceLine("x", 1, Decimal("0.35")),), Decimal("0.10")).tax == Decimal("0.04")


@pytest.mark.parametrize(
    "build",
    [
        lambda: InvoiceLine("x", 0, Decimal(1)),
        lambda: InvoiceLine("x", 1, Decimal(-1)),
        lambda: Invoice("i", (), Decimal("0.1")),
        lambda: invoice("1.5"),
    ],
)
def test_invalid_invoices_are_rejected_with_a_named_error(build):
    with pytest.raises(InvoiceError):
        build()


def test_issuing_stores_the_invoice_and_refuses_a_duplicate_id():
    issue = IssueInvoice(InMemoryInvoices())
    issue("i-1", "0.05", [("a", 1, "10.00")])
    with pytest.raises(KeyError):
        issue("i-1", "0.05", [("a", 1, "10.00")])


def test_text_that_is_not_a_number_is_an_invoice_error():
    with pytest.raises(InvoiceError, match="decimal"):
        IssueInvoice(InMemoryInvoices())("i-1", "five", [("a", 1, "10.00")])


def test_the_command_prints_the_totals(capsys):
    assert main(["i-1", "0.0825", "widget:3:19.99"]) == 0
    assert capsys.readouterr().out.strip() == "i-1: subtotal 59.97 tax 4.95 total 64.92"


def test_the_command_reports_bad_input_with_exit_code_1(capsys):
    assert main(["i-1", "2", "widget:3:19.99"]) == 1
    assert "tax rate" in capsys.readouterr().err


def test_the_command_without_arguments_is_a_usage_error(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err
