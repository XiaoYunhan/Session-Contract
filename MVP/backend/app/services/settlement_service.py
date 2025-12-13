"""Settlement service."""
from typing import Dict, Optional
from datetime import datetime

from ..domain import (
    SessionStatus, Settlement, EventType,
    check_settlement_sum
)
from ..storage import (
    EventStore, SessionRepository, AllocationRepository,
    PriceRepository, SettlementRepository
)


class SettlementService:
    """Service for session settlement."""

    def __init__(
        self,
        event_store: EventStore,
        session_repo: SessionRepository,
        allocation_repo: AllocationRepository,
        price_repo: PriceRepository,
        settlement_repo: SettlementRepository
    ):
        self.event_store = event_store
        self.session_repo = session_repo
        self.allocation_repo = allocation_repo
        self.price_repo = price_repo
        self.settlement_repo = settlement_repo

    def settle_session(self, session_id: str) -> Settlement:
        """
        Settle a session using latest prices.

        Args:
            session_id: Session identifier

        Returns:
            Settlement result

        Raises:
            ValueError: If session cannot be settled or invariants fail
        """
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status == SessionStatus.SETTLED:
            raise ValueError(f"Session {session_id} already settled")

        # Get latest prices (S_t2)
        settlement_prices = self.price_repo.get_latest_prices(session_id)
        if not settlement_prices:
            raise ValueError(f"No prices available for session {session_id}")

        # Verify all legs have prices
        for leg in session.legs:
            if leg not in settlement_prices:
                raise ValueError(f"Missing price for leg {leg}")

        # Get final allocations
        allocations = self.allocation_repo.get_allocations(session_id)
        if not allocations:
            raise ValueError(f"No allocations for session {session_id}")

        # Calculate payouts: payout_i = Σ_k (x_i[k] * S_t2[k])
        payouts: Dict[str, float] = {}
        for participant_id, participant_alloc in allocations.items():
            payout = sum(
                participant_alloc.get(leg, 0.0) * settlement_prices[leg]
                for leg in session.legs
            )
            payouts[participant_id] = payout

        # Validate settlement sum
        basket = {leg: qty for leg, qty in zip(session.legs, session.q)}
        check_settlement_sum(payouts, basket, settlement_prices)

        settlement = Settlement(
            session_id=session_id,
            settlement_prices=settlement_prices,
            payouts=payouts,
            settled_at=datetime.utcnow()
        )

        # Append event
        self.event_store.append(
            session_id,
            EventType.SESSION_SETTLED,
            {
                "session_id": session_id,
                "settlement_prices": settlement_prices,
                "payouts": payouts,
                "settled_at": settlement.settled_at.isoformat()
            }
        )

        # Update projections
        self.settlement_repo.save_settlement(settlement)
        self.session_repo.update_session_status(session_id, SessionStatus.SETTLED)

        return settlement

    def get_settlement(self, session_id: str) -> Optional[Settlement]:
        """Get settlement for a session."""
        return self.settlement_repo.get_settlement(session_id)
