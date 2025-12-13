"""Tests for settlement service."""
import pytest
import os
import tempfile
import uuid
from ..services import SessionService, SettlementService, PriceService
from ..storage import (
    EventStore, SessionRepository, ParticipantRepository,
    AllocationRepository, PriceRepository, SettlementRepository, init_db
)


@pytest.fixture
def setup_test_db():
    """Setup a temporary test database."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.environ['DATABASE_URL'] = f'sqlite:///{path}'
    init_db()
    yield path
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def session_service():
    return SessionService(
        EventStore(),
        SessionRepository(),
        ParticipantRepository(),
        AllocationRepository()
    )


@pytest.fixture
def settlement_service():
    return SettlementService(
        EventStore(),
        SessionRepository(),
        AllocationRepository(),
        PriceRepository(),
        SettlementRepository()
    )


@pytest.fixture
def price_service():
    return PriceService(EventStore(), PriceRepository())


def test_settlement_calculation(setup_test_db, session_service, settlement_service, price_service):
    """Test settlement calculation."""
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    # Create session
    session_service.create_session(session_id, ["AAPL", "NVDA"], [100.0, 60.0])
    session_service.add_participant(session_id, "alice")
    session_service.add_participant(session_id, "bob")
    session_service.assign_initial_allocations(session_id)

    # Set prices
    price_service.update_prices(session_id, {"AAPL": 200.0, "NVDA": 500.0})

    # Settle
    settlement = settlement_service.settle_session(session_id)

    # Each participant has 50 AAPL and 30 NVDA
    # Expected payout: 50 * 200 + 30 * 500 = 10000 + 15000 = 25000 each
    assert settlement.settlement_prices == {"AAPL": 200.0, "NVDA": 500.0}
    assert abs(settlement.payouts["alice"] - 25000.0) < 1e-6
    assert abs(settlement.payouts["bob"] - 25000.0) < 1e-6


def test_settlement_sum_invariant(setup_test_db, session_service, settlement_service, price_service):
    """Test that settlement sum equals basket value."""
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    # Create session with 3 participants
    session_service.create_session(session_id, ["AAPL", "NVDA", "META"], [100.0, 60.0, 80.0])
    session_service.add_participant(session_id, "alice")
    session_service.add_participant(session_id, "bob")
    session_service.add_participant(session_id, "charlie")
    session_service.assign_initial_allocations(session_id)

    # Set prices
    prices = {"AAPL": 190.0, "NVDA": 480.0, "META": 350.0}
    price_service.update_prices(session_id, prices)

    # Settle
    settlement = settlement_service.settle_session(session_id)

    # Calculate expected total
    expected_total = 100.0 * 190.0 + 60.0 * 480.0 + 80.0 * 350.0
    actual_total = sum(settlement.payouts.values())

    # Should match within tolerance
    assert abs(actual_total - expected_total) < 1e-6


def test_settlement_without_prices_fails(setup_test_db, session_service, settlement_service):
    """Test that settlement without prices fails."""
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    session_service.create_session(session_id, ["AAPL", "NVDA"], [100.0, 60.0])
    session_service.add_participant(session_id, "alice")
    session_service.assign_initial_allocations(session_id)

    # Try to settle without prices
    with pytest.raises(ValueError, match="No prices available"):
        settlement_service.settle_session(session_id)
