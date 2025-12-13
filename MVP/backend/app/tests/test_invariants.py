"""Tests for invariant checks."""
import pytest
from ..domain.invariants import (
    check_conservation,
    check_no_negative_positions,
    check_trade_conservation,
    check_settlement_sum,
    validate_trade_feasibility,
    InvariantViolation
)


def test_conservation_valid():
    """Test that valid conservation passes."""
    allocations = {
        "alice": {"AAPL": 50.0, "NVDA": 30.0},
        "bob": {"AAPL": 50.0, "NVDA": 30.0}
    }
    basket = {"AAPL": 100.0, "NVDA": 60.0}

    # Should not raise
    check_conservation(allocations, basket)


def test_conservation_violation():
    """Test that conservation violation is detected."""
    allocations = {
        "alice": {"AAPL": 60.0, "NVDA": 30.0},
        "bob": {"AAPL": 50.0, "NVDA": 30.0}
    }
    basket = {"AAPL": 100.0, "NVDA": 60.0}

    with pytest.raises(InvariantViolation):
        check_conservation(allocations, basket)


def test_no_negative_positions_valid():
    """Test that non-negative positions pass."""
    allocations = {
        "alice": {"AAPL": 50.0, "NVDA": 30.0},
        "bob": {"AAPL": 50.0, "NVDA": 30.0}
    }

    # Should not raise
    check_no_negative_positions(allocations)


def test_negative_position_violation():
    """Test that negative positions are detected."""
    allocations = {
        "alice": {"AAPL": -10.0, "NVDA": 30.0},
        "bob": {"AAPL": 110.0, "NVDA": 30.0}
    }

    with pytest.raises(InvariantViolation):
        check_no_negative_positions(allocations)


def test_trade_conservation_valid():
    """Test that zero-sum trades pass."""
    delta_a = {"AAPL": -10.0, "NVDA": 6.2}
    delta_b = {"AAPL": 10.0, "NVDA": -6.2}
    legs = ["AAPL", "NVDA", "META", "ORCL"]

    # Should not raise
    check_trade_conservation(delta_a, delta_b, legs)


def test_trade_conservation_violation():
    """Test that non-zero-sum trades are detected."""
    delta_a = {"AAPL": -10.0, "NVDA": 6.2}
    delta_b = {"AAPL": 11.0, "NVDA": -6.2}  # Imbalanced
    legs = ["AAPL", "NVDA", "META", "ORCL"]

    with pytest.raises(InvariantViolation):
        check_trade_conservation(delta_a, delta_b, legs)


def test_settlement_sum_valid():
    """Test that valid settlement passes."""
    payouts = {"alice": 800.0, "bob": 800.0}
    basket = {"AAPL": 100.0, "NVDA": 60.0}
    prices = {"AAPL": 10.0, "NVDA": 10.0}

    # Total payout should equal basket value: 100*10 + 60*10 = 1600
    check_settlement_sum(payouts, basket, prices)


def test_settlement_sum_violation():
    """Test that settlement sum mismatch is detected."""
    payouts = {"alice": 900.0, "bob": 1000.0}  # Total 1900, should be 2000
    basket = {"AAPL": 100.0, "NVDA": 60.0}
    prices = {"AAPL": 10.0, "NVDA": 10.0}

    with pytest.raises(InvariantViolation):
        check_settlement_sum(payouts, basket, prices)


def test_trade_feasibility_valid():
    """Test that feasible trades pass."""
    allocations = {
        "alice": {"AAPL": 50.0, "NVDA": 30.0},
        "bob": {"AAPL": 50.0, "NVDA": 30.0}
    }

    # Alice wants to trade 10 AAPL for NVDA from Bob
    validate_trade_feasibility(
        allocations,
        participant_a="alice",
        participant_b="bob",
        leg_from="AAPL",
        leg_to="NVDA",
        amount_from=10.0,
        amount_to=6.2
    )


def test_trade_feasibility_insufficient_inventory():
    """Test that insufficient inventory is detected."""
    allocations = {
        "alice": {"AAPL": 5.0, "NVDA": 30.0},  # Only 5 AAPL
        "bob": {"AAPL": 95.0, "NVDA": 30.0}
    }

    # Alice wants to trade 10 AAPL but only has 5
    with pytest.raises(InvariantViolation):
        validate_trade_feasibility(
            allocations,
            participant_a="alice",
            participant_b="bob",
            leg_from="AAPL",
            leg_to="NVDA",
            amount_from=10.0,
            amount_to=6.2
        )
