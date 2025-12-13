"""Event store implementation."""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from .database import get_db
from ..domain.types import Event, EventType


class EventStore:
    """Event sourcing store."""

    def append(self, session_id: str, event_type: EventType, data: Dict[str, Any]) -> Event:
        """
        Append a new event to the store.

        Args:
            session_id: Session identifier
            event_type: Type of event
            data: Event payload

        Returns:
            The created event
        """
        with get_db() as conn:
            cursor = conn.cursor()

            # Get next sequence number
            cursor.execute(
                "SELECT COALESCE(MAX(sequence), -1) + 1 FROM events WHERE session_id = ?",
                (session_id,)
            )
            sequence = cursor.fetchone()[0]

            event = Event(
                event_id=str(uuid.uuid4()),
                session_id=session_id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                data=data,
                sequence=sequence
            )

            cursor.execute(
                """
                INSERT INTO events (event_id, session_id, event_type, timestamp, sequence, data)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.session_id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.sequence,
                    json.dumps(event.data)
                )
            )

            conn.commit()
            return event

    def get_events(self, session_id: str, from_sequence: int = 0) -> List[Event]:
        """
        Get all events for a session.

        Args:
            session_id: Session identifier
            from_sequence: Starting sequence number (inclusive)

        Returns:
            List of events in order
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT event_id, session_id, event_type, timestamp, sequence, data
                FROM events
                WHERE session_id = ? AND sequence >= ?
                ORDER BY sequence ASC
                """,
                (session_id, from_sequence)
            )

            events = []
            for row in cursor.fetchall():
                events.append(Event(
                    event_id=row[0],
                    session_id=row[1],
                    event_type=EventType(row[2]),
                    timestamp=datetime.fromisoformat(row[3]),
                    sequence=row[4],
                    data=json.loads(row[5])
                ))

            return events

    def replay_events(self, session_id: str) -> Dict[str, Any]:
        """
        Replay all events to reconstruct current state.

        Args:
            session_id: Session identifier

        Returns:
            Reconstructed state dictionary
        """
        events = self.get_events(session_id)

        state = {
            "session": None,
            "participants": {},
            "allocations": {},
            "rfqs": {},
            "quotes": {},
            "trades": [],
            "settlement": None,
            "latest_prices": {}
        }

        for event in events:
            self._apply_event(state, event)

        return state

    def _apply_event(self, state: Dict[str, Any], event: Event) -> None:
        """Apply an event to update state."""
        if event.event_type == EventType.SESSION_CREATED:
            state["session"] = event.data

        elif event.event_type == EventType.PARTICIPANT_JOINED:
            participant_id = event.data["participant_id"]
            state["participants"][participant_id] = event.data

        elif event.event_type == EventType.INITIAL_ALLOCATION_ASSIGNED:
            participant_id = event.data["participant_id"]
            allocations = event.data["allocations"]
            state["allocations"][participant_id] = allocations

        elif event.event_type == EventType.SESSION_STARTED:
            if state["session"]:
                state["session"]["status"] = "active"
                state["session"]["t1"] = event.data.get("t1")

        elif event.event_type == EventType.PRICE_TICK:
            state["latest_prices"] = event.data["prices"]

        elif event.event_type == EventType.RFQ_REQUESTED:
            rfq_id = event.data["rfq_id"]
            state["rfqs"][rfq_id] = event.data

        elif event.event_type == EventType.QUOTE_PROVIDED:
            quote_id = event.data["quote_id"]
            state["quotes"][quote_id] = event.data

        elif event.event_type == EventType.TRADE_EXECUTED:
            trade = event.data
            state["trades"].append(trade)

            # Update allocations
            participant_a = trade["participant_a"]
            participant_b = trade["participant_b"]
            leg_from = trade["leg_from"]
            leg_to = trade["leg_to"]
            amount_from = trade["amount_from"]
            amount_to = trade["amount_to"]

            # A gives amount_from of leg_from, receives amount_to of leg_to
            if participant_a not in state["allocations"]:
                state["allocations"][participant_a] = {}
            state["allocations"][participant_a][leg_from] = (
                state["allocations"][participant_a].get(leg_from, 0.0) - amount_from
            )
            state["allocations"][participant_a][leg_to] = (
                state["allocations"][participant_a].get(leg_to, 0.0) + amount_to
            )

            # B receives amount_from of leg_from, gives amount_to of leg_to
            if participant_b not in state["allocations"]:
                state["allocations"][participant_b] = {}
            state["allocations"][participant_b][leg_from] = (
                state["allocations"][participant_b].get(leg_from, 0.0) + amount_from
            )
            state["allocations"][participant_b][leg_to] = (
                state["allocations"][participant_b].get(leg_to, 0.0) - amount_to
            )

            # Update RFQ status
            rfq_id = trade["rfq_id"]
            if rfq_id in state["rfqs"]:
                state["rfqs"][rfq_id]["status"] = "executed"

        elif event.event_type == EventType.SESSION_SETTLED:
            state["settlement"] = event.data
            if state["session"]:
                state["session"]["status"] = "settled"
