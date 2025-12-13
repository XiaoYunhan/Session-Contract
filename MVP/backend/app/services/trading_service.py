"""Trading service for RFQ/quote mechanism."""
import uuid
from typing import Dict
from datetime import datetime

from ..domain import (
    RFQ, RFQStatus, Quote, Trade, EventType,
    validate_trade_feasibility, check_conservation, check_no_negative_positions
)
from ..storage import (
    EventStore, SessionRepository, TradingRepository, AllocationRepository
)


class TradingService:
    """Service for RFQ/quote trading mechanism."""

    def __init__(
        self,
        event_store: EventStore,
        session_repo: SessionRepository,
        trading_repo: TradingRepository,
        allocation_repo: AllocationRepository
    ):
        self.event_store = event_store
        self.session_repo = session_repo
        self.trading_repo = trading_repo
        self.allocation_repo = allocation_repo

    def create_rfq(
        self,
        session_id: str,
        requester_id: str,
        leg_from: str,
        leg_to: str,
        amount_from: float
    ) -> RFQ:
        """
        Create a request for quote.

        Args:
            session_id: Session identifier
            requester_id: Participant requesting the quote
            leg_from: Leg to give
            leg_to: Leg to receive
            amount_from: Amount to give

        Returns:
            Created RFQ
        """
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if leg_from not in session.legs or leg_to not in session.legs:
            raise ValueError("Invalid legs")

        if leg_from == leg_to:
            raise ValueError("Cannot swap same leg")

        if amount_from <= 0:
            raise ValueError("Amount must be positive")

        rfq = RFQ(
            rfq_id=str(uuid.uuid4()),
            session_id=session_id,
            requester_id=requester_id,
            leg_from=leg_from,
            leg_to=leg_to,
            amount_from=amount_from,
            status=RFQStatus.OPEN,
            created_at=datetime.utcnow()
        )

        # Append event
        self.event_store.append(
            session_id,
            EventType.RFQ_REQUESTED,
            {
                "rfq_id": rfq.rfq_id,
                "session_id": session_id,
                "requester_id": requester_id,
                "leg_from": leg_from,
                "leg_to": leg_to,
                "amount_from": amount_from,
                "status": rfq.status.value,
                "created_at": rfq.created_at.isoformat()
            }
        )

        # Update projection
        self.trading_repo.create_rfq(rfq)

        return rfq

    def provide_quote(
        self,
        rfq_id: str,
        quoter_id: str,
        rate: float
    ) -> Quote:
        """
        Provide a quote for an RFQ.

        Args:
            rfq_id: RFQ identifier
            quoter_id: Participant providing the quote
            rate: Exchange rate (amount_to / amount_from)

        Returns:
            Created quote
        """
        rfq = self.trading_repo.get_rfq(rfq_id)
        if not rfq:
            raise ValueError(f"RFQ {rfq_id} not found")

        if rfq.status != RFQStatus.OPEN:
            raise ValueError(f"RFQ {rfq_id} is {rfq.status}")

        if quoter_id == rfq.requester_id:
            raise ValueError("Cannot quote your own RFQ")

        if rate <= 0:
            raise ValueError("Rate must be positive")

        quote = Quote(
            quote_id=str(uuid.uuid4()),
            rfq_id=rfq_id,
            quoter_id=quoter_id,
            rate=rate,
            created_at=datetime.utcnow()
        )

        # Append event
        self.event_store.append(
            rfq.session_id,
            EventType.QUOTE_PROVIDED,
            {
                "quote_id": quote.quote_id,
                "rfq_id": rfq_id,
                "quoter_id": quoter_id,
                "rate": rate,
                "created_at": quote.created_at.isoformat()
            }
        )

        # Update projection
        self.trading_repo.create_quote(quote)

        return quote

    def accept_quote(self, quote_id: str) -> Trade:
        """
        Accept a quote and execute the trade.

        Args:
            quote_id: Quote identifier

        Returns:
            Executed trade

        Raises:
            ValueError: If trade would violate invariants
        """
        quote = self.trading_repo.get_quote(quote_id)
        if not quote:
            raise ValueError(f"Quote {quote_id} not found")

        rfq = self.trading_repo.get_rfq(quote.rfq_id)
        if not rfq:
            raise ValueError(f"RFQ {quote.rfq_id} not found")

        session = self.session_repo.get_session(rfq.session_id)
        if not session:
            raise ValueError(f"Session {rfq.session_id} not found")

        # Calculate amounts
        amount_from = rfq.amount_from
        amount_to = amount_from * quote.rate

        # Get current allocations
        allocations = self.allocation_repo.get_allocations(rfq.session_id)

        # Validate trade feasibility
        validate_trade_feasibility(
            allocations,
            rfq.requester_id,
            quote.quoter_id,
            rfq.leg_from,
            rfq.leg_to,
            amount_from,
            amount_to
        )

        # Execute trade
        trade = Trade(
            trade_id=str(uuid.uuid4()),
            session_id=rfq.session_id,
            rfq_id=rfq.rfq_id,
            quote_id=quote_id,
            participant_a=rfq.requester_id,
            participant_b=quote.quoter_id,
            leg_from=rfq.leg_from,
            leg_to=rfq.leg_to,
            amount_from=amount_from,
            amount_to=amount_to,
            executed_at=datetime.utcnow()
        )

        # Update allocations (temporary for validation)
        new_allocations = {pid: alloc.copy() for pid, alloc in allocations.items()}

        # A gives amount_from, receives amount_to
        new_allocations[rfq.requester_id][rfq.leg_from] -= amount_from
        new_allocations[rfq.requester_id][rfq.leg_to] = (
            new_allocations[rfq.requester_id].get(rfq.leg_to, 0.0) + amount_to
        )

        # B receives amount_from, gives amount_to
        new_allocations[quote.quoter_id][rfq.leg_from] = (
            new_allocations[quote.quoter_id].get(rfq.leg_from, 0.0) + amount_from
        )
        new_allocations[quote.quoter_id][rfq.leg_to] -= amount_to

        # Validate post-trade state
        basket = {leg: qty for leg, qty in zip(session.legs, session.q)}
        check_conservation(new_allocations, basket)
        check_no_negative_positions(new_allocations)

        # Append event
        self.event_store.append(
            rfq.session_id,
            EventType.TRADE_EXECUTED,
            {
                "trade_id": trade.trade_id,
                "session_id": trade.session_id,
                "rfq_id": trade.rfq_id,
                "quote_id": quote_id,
                "participant_a": trade.participant_a,
                "participant_b": trade.participant_b,
                "leg_from": trade.leg_from,
                "leg_to": trade.leg_to,
                "amount_from": amount_from,
                "amount_to": amount_to,
                "executed_at": trade.executed_at.isoformat()
            }
        )

        # Update projections
        self.trading_repo.create_trade(trade)
        self.allocation_repo.set_allocations(
            rfq.session_id,
            rfq.requester_id,
            new_allocations[rfq.requester_id]
        )
        self.allocation_repo.set_allocations(
            rfq.session_id,
            quote.quoter_id,
            new_allocations[quote.quoter_id]
        )

        return trade
