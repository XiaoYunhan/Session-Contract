"""Invariant checks for Session Contracts."""
from typing import Dict, List
import math


class InvariantViolation(Exception):
    """Raised when an invariant check fails."""
    pass


def check_conservation(
    allocations: Dict[str, Dict[str, float]],  # participant_id -> {leg -> amount}
    basket: Dict[str, float],  # leg -> total quantity
    tolerance: float = 1e-9
) -> None:
    """
    Verify conservation: Σ_i x[i][k] == q[k] for each leg k.

    Args:
        allocations: Current allocations per participant
        basket: Fixed basket quantities
        tolerance: Numerical tolerance for floating point comparison

    Raises:
        InvariantViolation: If conservation is violated
    """
    for leg, total_qty in basket.items():
        allocated_sum = sum(
            participant_alloc.get(leg, 0.0)
            for participant_alloc in allocations.values()
        )

        if abs(allocated_sum - total_qty) > tolerance:
            raise InvariantViolation(
                f"Conservation violated for leg {leg}: "
                f"allocated={allocated_sum:.10f}, basket={total_qty:.10f}, "
                f"diff={abs(allocated_sum - total_qty):.10e}"
            )


def check_no_negative_positions(
    allocations: Dict[str, Dict[str, float]],
    tolerance: float = -1e-9
) -> None:
    """
    Verify no internal shorting: x[i][k] >= 0 for all i, k.

    Args:
        allocations: Current allocations per participant
        tolerance: Small negative tolerance for rounding errors

    Raises:
        InvariantViolation: If any position is negative
    """
    for participant_id, participant_alloc in allocations.items():
        for leg, amount in participant_alloc.items():
            if amount < tolerance:
                raise InvariantViolation(
                    f"Negative position for participant {participant_id}, "
                    f"leg {leg}: {amount:.10f}"
                )


def check_trade_conservation(
    delta_a: Dict[str, float],
    delta_b: Dict[str, float],
    legs: List[str],
    tolerance: float = 1e-9
) -> None:
    """
    Verify trade is zero-sum: Δx_a + Δx_b = 0 (vectorwise).

    Args:
        delta_a: Changes for participant A
        delta_b: Changes for participant B
        legs: All legs in the session
        tolerance: Numerical tolerance

    Raises:
        InvariantViolation: If trade is not zero-sum
    """
    for leg in legs:
        total_delta = delta_a.get(leg, 0.0) + delta_b.get(leg, 0.0)
        if abs(total_delta) > tolerance:
            raise InvariantViolation(
                f"Trade not zero-sum for leg {leg}: "
                f"delta_a={delta_a.get(leg, 0.0):.10f}, "
                f"delta_b={delta_b.get(leg, 0.0):.10f}, "
                f"sum={total_delta:.10e}"
            )


def check_settlement_sum(
    payouts: Dict[str, float],
    basket: Dict[str, float],
    prices: Dict[str, float],
    tolerance: float = 1e-6
) -> None:
    """
    Verify settlement: Σ_i payout_i = q · S_t2.

    Args:
        payouts: Payout per participant
        basket: Fixed basket quantities
        prices: Settlement prices S_t2
        tolerance: Numerical tolerance

    Raises:
        InvariantViolation: If settlement sum doesn't match
    """
    total_payout = sum(payouts.values())
    expected_total = sum(basket[leg] * prices[leg] for leg in basket)

    if abs(total_payout - expected_total) > tolerance:
        raise InvariantViolation(
            f"Settlement sum mismatch: "
            f"total_payout={total_payout:.10f}, "
            f"expected={expected_total:.10f}, "
            f"diff={abs(total_payout - expected_total):.10e}"
        )


def validate_trade_feasibility(
    current_allocations: Dict[str, Dict[str, float]],
    participant_a: str,
    participant_b: str,
    leg_from: str,
    leg_to: str,
    amount_from: float,
    amount_to: float,
    tolerance: float = 1e-9
) -> None:
    """
    Check if a proposed trade would violate invariants.

    Args:
        current_allocations: Current state
        participant_a: Requester (gives amount_from, receives amount_to)
        participant_b: Quoter (receives amount_from, gives amount_to)
        leg_from: Leg being given by participant_a
        leg_to: Leg being received by participant_a
        amount_from: Amount given by participant_a
        amount_to: Amount received by participant_a
        tolerance: Numerical tolerance

    Raises:
        InvariantViolation: If trade would violate constraints
    """
    # Check participant A has enough of leg_from
    alloc_a = current_allocations.get(participant_a, {})
    if alloc_a.get(leg_from, 0.0) < amount_from - tolerance:
        raise InvariantViolation(
            f"Participant {participant_a} has insufficient {leg_from}: "
            f"has {alloc_a.get(leg_from, 0.0):.10f}, needs {amount_from:.10f}"
        )

    # Check participant B has enough of leg_to
    alloc_b = current_allocations.get(participant_b, {})
    if alloc_b.get(leg_to, 0.0) < amount_to - tolerance:
        raise InvariantViolation(
            f"Participant {participant_b} has insufficient {leg_to}: "
            f"has {alloc_b.get(leg_to, 0.0):.10f}, needs {amount_to:.10f}"
        )

    # Verify amounts are positive
    if amount_from <= 0 or amount_to <= 0:
        raise InvariantViolation(
            f"Trade amounts must be positive: "
            f"amount_from={amount_from}, amount_to={amount_to}"
        )
