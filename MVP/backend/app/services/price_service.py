"""Price oracle service."""
from typing import Dict, Optional
from datetime import datetime

from ..domain import PriceTick, EventType
from ..storage import EventStore, PriceRepository


class PriceService:
    """Service for handling price updates from oracle."""

    def __init__(
        self,
        event_store: EventStore,
        price_repo: PriceRepository
    ):
        self.event_store = event_store
        self.price_repo = price_repo

    def update_prices(self, session_id: str, prices: Dict[str, float]) -> PriceTick:
        """
        Update prices for a session.

        Args:
            session_id: Session identifier
            prices: Price map (leg -> price)

        Returns:
            Created price tick
        """
        tick = PriceTick(
            session_id=session_id,
            timestamp=datetime.utcnow(),
            prices=prices
        )

        # Append event
        self.event_store.append(
            session_id,
            EventType.PRICE_TICK,
            {
                "session_id": session_id,
                "timestamp": tick.timestamp.isoformat(),
                "prices": prices
            }
        )

        # Update projection
        self.price_repo.save_tick(tick)

        return tick

    def get_latest_prices(self, session_id: str) -> Optional[Dict[str, float]]:
        """Get latest prices for a session."""
        return self.price_repo.get_latest_prices(session_id)
