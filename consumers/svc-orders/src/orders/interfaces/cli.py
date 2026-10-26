"""``python -m orders ORDER_ID SKU:QUANTITY:UNIT_CENTS ...`` prints the order total."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from orders.application.place_order import PlaceOrder
from orders.domain.order import OrderError
from orders.infrastructure.memory_repository import InMemoryOrders


def main(argv: Sequence[str] | None = None) -> int:
    """Run the program; return 0 on success and 1 when the order is invalid."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print("usage: python -m orders ORDER_ID SKU:QUANTITY:UNIT_CENTS ...", file=sys.stderr)
        return 2
    try:
        lines = [(sku, int(quantity), int(price)) for sku, quantity, price in (part.split(":") for part in args[1:])]
        order = PlaceOrder(InMemoryOrders())(args[0], lines)
    except (OrderError, ValueError) as error:
        print(f"orders: {error}", file=sys.stderr)
        return 1
    print(f"{order.order_id}: {order.total_cents / 100:.2f}")
    return 0
