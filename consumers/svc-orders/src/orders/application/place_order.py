"""Use case: place an order and keep it."""

from __future__ import annotations

from typing import Protocol

from orders.domain.order import Order, OrderLine


class OrderRepository(Protocol):
    """Where placed orders are kept."""

    def add(self, order: Order) -> None:
        """Store ``order``; raise ``KeyError`` when the id is already taken."""
        ...


class PlaceOrder:
    """Build an order from raw line data and store it."""

    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def __call__(self, order_id: str, lines: list[tuple[str, int, int]]) -> Order:
        """Place the order; invalid data raises :class:`~orders.domain.order.OrderError`."""
        order = Order(order_id, tuple(OrderLine(sku, quantity, price) for sku, quantity, price in lines))
        self._repository.add(order)
        return order
