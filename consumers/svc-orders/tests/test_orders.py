import pytest

from orders.application.place_order import PlaceOrder
from orders.domain.order import Order, OrderError, OrderLine
from orders.infrastructure.memory_repository import InMemoryOrders
from orders.interfaces.cli import main


def test_a_line_total_is_quantity_times_unit_price():
    assert OrderLine("pen", 3, 125).total_cents == 375


def test_an_order_total_sums_its_lines():
    order = Order("o-1", (OrderLine("pen", 2, 100), OrderLine("pad", 1, 450)))
    assert order.total_cents == 650


@pytest.mark.parametrize(
    "build",
    [
        lambda: OrderLine("", 1, 1),
        lambda: OrderLine("pen", 0, 1),
        lambda: OrderLine("pen", 1, -1),
        lambda: Order("o-1", ()),
    ],
)
def test_invalid_orders_are_rejected_with_a_named_error(build):
    with pytest.raises(OrderError):
        build()


def test_placing_an_order_stores_it_and_a_duplicate_id_is_refused():
    place = PlaceOrder(InMemoryOrders())
    assert place("o-1", [("pen", 1, 100)]).total_cents == 100
    repository = InMemoryOrders()
    place = PlaceOrder(repository)
    place("o-1", [("pen", 1, 100)])
    with pytest.raises(KeyError):
        place("o-1", [("pen", 1, 100)])


def test_the_command_prints_the_total_in_currency_units(capsys):
    assert main(["o-9", "pen:2:150", "pad:1:50"]) == 0
    assert capsys.readouterr().out.strip() == "o-9: 3.50"


def test_the_command_reports_an_invalid_order_with_exit_code_1(capsys):
    assert main(["o-9", "pen:0:150"]) == 1
    assert "at least 1" in capsys.readouterr().err


def test_the_command_without_arguments_is_a_usage_error(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err
