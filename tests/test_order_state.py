import pytest

from app.models import OrderStatus as S
from app.services.order_service import calculate_total
from app.services.order_state import (
    ALLOWED_TRANSITIONS,
    InvalidStatusTransitionError,
    can_transition,
    ensure_transition,
)

VALID = [
    (S.PENDING, S.CONFIRMED),
    (S.PENDING, S.CANCELLED),
    (S.CONFIRMED, S.PREPARING),
    (S.CONFIRMED, S.CANCELLED),
    (S.PREPARING, S.READY),
    (S.READY, S.DELIVERED),
]


@pytest.mark.parametrize("current,target", VALID)
def test_valid_transitions_are_allowed(current, target):
    assert can_transition(current, target)
    ensure_transition(current, target)  # must not raise


def test_every_status_has_a_rule():
    assert set(ALLOWED_TRANSITIONS) == set(S)


@pytest.mark.parametrize("terminal", [S.DELIVERED, S.CANCELLED])
def test_terminal_statuses_allow_no_transition(terminal):
    assert all(not can_transition(terminal, target) for target in S)


def test_delivered_order_cannot_go_back_to_preparing():
    with pytest.raises(InvalidStatusTransitionError):
        ensure_transition(S.DELIVERED, S.PREPARING)


def test_steps_cannot_be_skipped():
    with pytest.raises(InvalidStatusTransitionError):
        ensure_transition(S.PENDING, S.READY)


@pytest.mark.parametrize("current", [S.PREPARING, S.READY])
def test_cannot_cancel_once_preparation_started(current):
    assert not can_transition(current, S.CANCELLED)


def test_same_status_is_not_a_transition():
    assert not can_transition(S.PENDING, S.PENDING)


def test_calculate_total():
    assert calculate_total([(300000, 2), (50000, 1)]) == 650000
    assert calculate_total([]) == 0