"""Tests for trading service."""
import pytest
import os
import tempfile
import uuid
from ..domain import InvariantViolation
from ..services import SessionService, TradingService
from ..storage import (
    EventStore, SessionRepository, ParticipantRepository,
    AllocationRepository, TradingRepository, init_db
)


@pytest.fixture
def setup_test_db():
    """Setup a temporary test database."""
    # Create a temporary database file
    fd, path = tempfile.mkstemp(suffix='.db')
    os.environ['DATABASE_URL'] = f'sqlite:///{path}'

    # Initialize database
    init_db()

    yield path

    # Cleanup
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def session_service():
    """Create session service."""
    return SessionService(
        EventStore(),
        SessionRepository(),
        ParticipantRepository(),
        AllocationRepository()
    )


@pytest.fixture
def trading_service():
    """Create trading service."""
    return TradingService(
        EventStore(),
        SessionRepository(),
        TradingRepository(),
        AllocationRepository()
    )


def test_rfq_creation(setup_test_db, session_service, trading_service):
    """Test RFQ creation."""
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    # Create session
    session = session_service.create_session(
        session_id=session_id,
        legs=["AAPL", "NVDA"],
        q=[100.0, 60.0]
    )

    # Add participants
    session_service.add_participant(session_id, "alice")
    session_service.add_participant(session_id, "bob")

    # Assign allocations
    session_service.assign_initial_allocations(session_id)

    # Create RFQ
    rfq = trading_service.create_rfq(
        session_id=session_id,
        requester_id="alice",
        leg_from="AAPL",
        leg_to="NVDA",
        amount_from=10.0
    )

    assert rfq.session_id == session_id
    assert rfq.requester_id == "alice"
    assert rfq.leg_from == "AAPL"
    assert rfq.leg_to == "NVDA"
    assert rfq.amount_from == 10.0


def test_quote_provision(setup_test_db, session_service, trading_service):
    """Test quote provision."""
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    # Setup
    session_service.create_session(session_id, ["AAPL", "NVDA"], [100.0, 60.0])
    session_service.add_participant(session_id, "alice")
    session_service.add_participant(session_id, "bob")
    session_service.assign_initial_allocations(session_id)

    # Create RFQ
    rfq = trading_service.create_rfq(session_id, "alice", "AAPL", "NVDA", 10.0)

    # Provide quote
    quote = trading_service.provide_quote(
        rfq_id=rfq.rfq_id,
        quoter_id="bob",
        rate=0.62
    )

    assert quote.rfq_id == rfq.rfq_id
    assert quote.quoter_id == "bob"
    assert quote.rate == 0.62


def test_trade_execution(setup_test_db, session_service, trading_service):
    """Test trade execution and allocation updates."""
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    # Setup
    session_service.create_session(session_id, ["AAPL", "NVDA"], [100.0, 60.0])
    session_service.add_participant(session_id, "alice")
    session_service.add_participant(session_id, "bob")
    session_service.assign_initial_allocations(session_id)

    # Get initial allocations
    alloc_repo = AllocationRepository()
    initial_allocations = alloc_repo.get_allocations(session_id)

    assert initial_allocations["alice"]["AAPL"] == 50.0
    assert initial_allocations["alice"]["NVDA"] == 30.0
    assert initial_allocations["bob"]["AAPL"] == 50.0
    assert initial_allocations["bob"]["NVDA"] == 30.0

    # Create RFQ and quote
    rfq = trading_service.create_rfq(session_id, "alice", "AAPL", "NVDA", 10.0)
    quote = trading_service.provide_quote(rfq.rfq_id, "bob", 0.62)

    # Execute trade
    trade = trading_service.accept_quote(quote.quote_id)

    # Check trade details
    assert trade.participant_a == "alice"
    assert trade.participant_b == "bob"
    assert trade.amount_from == 10.0
    assert trade.amount_to == 6.2

    # Check updated allocations
    final_allocations = alloc_repo.get_allocations(session_id)

    # Alice gave 10 AAPL, received 6.2 NVDA
    assert final_allocations["alice"]["AAPL"] == 40.0
    assert final_allocations["alice"]["NVDA"] == 36.2

    # Bob received 10 AAPL, gave 6.2 NVDA
    assert final_allocations["bob"]["AAPL"] == 60.0
    assert final_allocations["bob"]["NVDA"] == 23.8


def test_trade_insufficient_inventory(setup_test_db, session_service, trading_service):
    """Test that trades with insufficient inventory are rejected."""
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    # Setup
    session_service.create_session(session_id, ["AAPL", "NVDA"], [100.0, 60.0])
    session_service.add_participant(session_id, "alice")
    session_service.add_participant(session_id, "bob")

    # Manually set allocations with Alice having only 5 AAPL
    alloc_repo = AllocationRepository()
    alloc_repo.set_allocations(session_id, "alice", {"AAPL": 5.0, "NVDA": 30.0})
    alloc_repo.set_allocations(session_id, "bob", {"AAPL": 95.0, "NVDA": 30.0})

    # Try to trade 10 AAPL (Alice only has 5)
    rfq = trading_service.create_rfq(session_id, "alice", "AAPL", "NVDA", 10.0)
    quote = trading_service.provide_quote(rfq.rfq_id, "bob", 0.62)

    # Should raise InvariantViolation
    with pytest.raises(InvariantViolation):
        trading_service.accept_quote(quote.quote_id)


def test_conservation_after_multiple_trades(setup_test_db, session_service, trading_service):
    """Test that conservation holds after multiple trades."""
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    # Setup
    session_service.create_session(session_id, ["AAPL", "NVDA", "META"], [100.0, 60.0, 80.0])
    session_service.add_participant(session_id, "alice")
    session_service.add_participant(session_id, "bob")
    session_service.add_participant(session_id, "charlie")
    session_service.assign_initial_allocations(session_id)

    # Execute multiple trades
    rfq1 = trading_service.create_rfq(session_id, "alice", "AAPL", "NVDA", 5.0)
    quote1 = trading_service.provide_quote(rfq1.rfq_id, "bob", 0.6)
    trading_service.accept_quote(quote1.quote_id)

    rfq2 = trading_service.create_rfq(session_id, "bob", "META", "AAPL", 10.0)
    quote2 = trading_service.provide_quote(rfq2.rfq_id, "charlie", 0.5)
    trading_service.accept_quote(quote2.quote_id)

    # Check conservation
    alloc_repo = AllocationRepository()
    allocations = alloc_repo.get_allocations(session_id)

    total_aapl = sum(alloc.get("AAPL", 0) for alloc in allocations.values())
    total_nvda = sum(alloc.get("NVDA", 0) for alloc in allocations.values())
    total_meta = sum(alloc.get("META", 0) for alloc in allocations.values())

    assert abs(total_aapl - 100.0) < 1e-9
    assert abs(total_nvda - 60.0) < 1e-9
    assert abs(total_meta - 80.0) < 1e-9
