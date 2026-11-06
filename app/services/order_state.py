"""Pure business rules for order status changes (no DB, no HTTP)."""
from app.models.enums import OrderStatus

S = OrderStatus

ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    S.PENDING: frozenset({S.CONFIRMED, S.CANCELLED}),
    S.CONFIRMED: frozenset({S.PREPARING, S.CANCELLED}),
    S.PREPARING: frozenset({S.READY}),
    S.READY: frozenset({S.DELIVERED}),
    S.DELIVERED: frozenset(),  # terminal
    S.CANCELLED: frozenset(),  # terminal
}


class InvalidStatusTransitionError(Exception):
    def __init__(self, current: OrderStatus, target: OrderStatus):
        self.current = current
        self.target = target
        super().__init__(
            f"Cannot change order status from {current.value} to {target.value}"
        )


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: OrderStatus, target: OrderStatus) -> None:
    if not can_transition(current, target):
        raise InvalidStatusTransitionError(current, target)