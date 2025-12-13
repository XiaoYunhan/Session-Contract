"""Data repository layer."""
import json
from typing import List, Dict, Optional
from datetime import datetime
from .database import get_db
from ..domain.types import (
    Session, SessionStatus, Participant, Allocation, RFQ, Quote, Trade,
    PriceTick, Settlement, StartMode, EndMode
)


class SessionRepository:
    """Repository for session data."""

    def create_session(self, session: Session) -> None:
        """Create a new session."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (session_id, legs, basket_q, t1, t2, status, start_mode, end_mode, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    json.dumps(session.legs),
                    json.dumps(session.q),
                    session.t1.isoformat() if session.t1 else None,
                    session.t2.isoformat() if session.t2 else None,
                    session.status.value,
                    session.start_mode.value,
                    session.end_mode.value,
                    session.created_at.isoformat()
                )
            )

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return Session(
                session_id=row["session_id"],
                legs=json.loads(row["legs"]),
                q=json.loads(row["basket_q"]),
                t1=datetime.fromisoformat(row["t1"]) if row["t1"] else None,
                t2=datetime.fromisoformat(row["t2"]) if row["t2"] else None,
                status=SessionStatus(row["status"]),
                start_mode=StartMode(row["start_mode"]),
                end_mode=EndMode(row["end_mode"]),
                created_at=datetime.fromisoformat(row["created_at"])
            )

    def update_session(self, session: Session) -> None:
        """Update session (including basket quantities)."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sessions
                SET basket_q = ?, t1 = ?, t2 = ?, status = ?
                WHERE session_id = ?
                """,
                (
                    json.dumps(session.q),
                    session.t1.isoformat() if session.t1 else None,
                    session.t2.isoformat() if session.t2 else None,
                    session.status.value,
                    session.session_id
                )
            )

    def update_session_status(self, session_id: str, status: SessionStatus) -> None:
        """Update session status."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET status = ? WHERE session_id = ?",
                (status.value, session_id)
            )

    def list_sessions(self) -> List[Session]:
        """List all sessions."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")

            sessions = []
            for row in cursor.fetchall():
                sessions.append(Session(
                    session_id=row["session_id"],
                    legs=json.loads(row["legs"]),
                    q=json.loads(row["basket_q"]),
                    t1=datetime.fromisoformat(row["t1"]) if row["t1"] else None,
                    t2=datetime.fromisoformat(row["t2"]) if row["t2"] else None,
                    status=SessionStatus(row["status"]),
                    start_mode=StartMode(row["start_mode"]),
                    end_mode=EndMode(row["end_mode"]),
                    created_at=datetime.fromisoformat(row["created_at"])
                ))

            return sessions


class ParticipantRepository:
    """Repository for participant data."""

    def add_participant(self, participant: Participant) -> None:
        """Add participant to session."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO participants (participant_id, session_id, name, joined_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    participant.participant_id,
                    participant.session_id,
                    participant.name,
                    participant.joined_at.isoformat()
                )
            )

    def get_participants(self, session_id: str) -> List[Participant]:
        """Get all participants in a session."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM participants WHERE session_id = ?",
                (session_id,)
            )

            participants = []
            for row in cursor.fetchall():
                participants.append(Participant(
                    participant_id=row["participant_id"],
                    session_id=row["session_id"],
                    name=row["name"],
                    joined_at=datetime.fromisoformat(row["joined_at"])
                ))

            return participants


class AllocationRepository:
    """Repository for allocation data."""

    def set_allocations(self, session_id: str, participant_id: str, allocations: Dict[str, float]) -> None:
        """Set allocations for a participant."""
        with get_db() as conn:
            cursor = conn.cursor()

            # Delete existing allocations
            cursor.execute(
                "DELETE FROM allocations WHERE session_id = ? AND participant_id = ?",
                (session_id, participant_id)
            )

            # Insert new allocations
            for leg, amount in allocations.items():
                cursor.execute(
                    """
                    INSERT INTO allocations (session_id, participant_id, leg, amount)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, participant_id, leg, amount)
                )

    def get_allocations(self, session_id: str) -> Dict[str, Dict[str, float]]:
        """Get all allocations for a session."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT participant_id, leg, amount FROM allocations WHERE session_id = ?",
                (session_id,)
            )

            allocations: Dict[str, Dict[str, float]] = {}
            for row in cursor.fetchall():
                participant_id = row["participant_id"]
                leg = row["leg"]
                amount = row["amount"]

                if participant_id not in allocations:
                    allocations[participant_id] = {}

                allocations[participant_id][leg] = amount

            return allocations

    def get_participant_allocation(self, session_id: str, participant_id: str) -> Dict[str, float]:
        """Get allocation for a specific participant."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT leg, amount FROM allocations WHERE session_id = ? AND participant_id = ?",
                (session_id, participant_id)
            )

            allocation = {}
            for row in cursor.fetchall():
                allocation[row["leg"]] = row["amount"]

            return allocation


class TradingRepository:
    """Repository for trading data (RFQs, quotes, trades)."""

    def create_rfq(self, rfq: RFQ) -> None:
        """Create a new RFQ."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO rfqs (rfq_id, session_id, requester_id, leg_from, leg_to, amount_from, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rfq.rfq_id,
                    rfq.session_id,
                    rfq.requester_id,
                    rfq.leg_from,
                    rfq.leg_to,
                    rfq.amount_from,
                    rfq.status.value,
                    rfq.created_at.isoformat(),
                    rfq.expires_at.isoformat() if rfq.expires_at else None
                )
            )

    def create_quote(self, quote: Quote) -> None:
        """Create a new quote."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO quotes (quote_id, rfq_id, quoter_id, rate, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    quote.quote_id,
                    quote.rfq_id,
                    quote.quoter_id,
                    quote.rate,
                    quote.created_at.isoformat(),
                    quote.expires_at.isoformat() if quote.expires_at else None
                )
            )

    def create_trade(self, trade: Trade) -> None:
        """Record a new trade."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO trades (trade_id, session_id, rfq_id, quote_id, participant_a, participant_b,
                                   leg_from, leg_to, amount_from, amount_to, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.trade_id,
                    trade.session_id,
                    trade.rfq_id,
                    trade.quote_id,
                    trade.participant_a,
                    trade.participant_b,
                    trade.leg_from,
                    trade.leg_to,
                    trade.amount_from,
                    trade.amount_to,
                    trade.executed_at.isoformat()
                )
            )

    def get_rfq(self, rfq_id: str) -> Optional[RFQ]:
        """Get RFQ by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rfqs WHERE rfq_id = ?", (rfq_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return RFQ(
                rfq_id=row["rfq_id"],
                session_id=row["session_id"],
                requester_id=row["requester_id"],
                leg_from=row["leg_from"],
                leg_to=row["leg_to"],
                amount_from=row["amount_from"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            )

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Get quote by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM quotes WHERE quote_id = ?", (quote_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return Quote(
                quote_id=row["quote_id"],
                rfq_id=row["rfq_id"],
                quoter_id=row["quoter_id"],
                rate=row["rate"],
                created_at=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
            )


class PriceRepository:
    """Repository for price data."""

    def save_tick(self, tick: PriceTick) -> None:
        """Save a price tick."""
        with get_db() as conn:
            cursor = conn.cursor()
            for leg, price in tick.prices.items():
                cursor.execute(
                    """
                    INSERT INTO price_ticks (session_id, timestamp, leg, price)
                    VALUES (?, ?, ?, ?)
                    """,
                    (tick.session_id, tick.timestamp.isoformat(), leg, price)
                )

    def get_latest_prices(self, session_id: str) -> Optional[Dict[str, float]]:
        """Get the latest prices for all legs."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT leg, price FROM price_ticks
                WHERE session_id = ? AND timestamp = (
                    SELECT MAX(timestamp) FROM price_ticks WHERE session_id = ?
                )
                """,
                (session_id, session_id)
            )

            prices = {}
            for row in cursor.fetchall():
                prices[row["leg"]] = row["price"]

            return prices if prices else None


class SettlementRepository:
    """Repository for settlement data."""

    def save_settlement(self, settlement: Settlement) -> None:
        """Save settlement result."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO settlements (session_id, settlement_prices, payouts, settled_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    settlement.session_id,
                    json.dumps(settlement.settlement_prices),
                    json.dumps(settlement.payouts),
                    settlement.settled_at.isoformat()
                )
            )

    def get_settlement(self, session_id: str) -> Optional[Settlement]:
        """Get settlement for a session."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM settlements WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return Settlement(
                session_id=row["session_id"],
                settlement_prices=json.loads(row["settlement_prices"]),
                payouts=json.loads(row["payouts"]),
                settled_at=datetime.fromisoformat(row["settled_at"])
            )
