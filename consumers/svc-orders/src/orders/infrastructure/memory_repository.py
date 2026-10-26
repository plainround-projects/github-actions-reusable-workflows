"""In-memory order storage."""

from __future__ import annotations

from orders.domain.order import Order


class InMemoryOrders:
    """Keeps orders in a dictionary for the lifetime of the process."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def add(self, order: Order) -> None:
        """Store ``order``; raise ``KeyError`` when the id is already taken."""
        if order.order_id in self._orders:
            raise KeyError(f"order {order.order_id} already exists")
        self._orders[order.order_id] = order
