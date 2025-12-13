"""Session management service."""
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from ..domain import (
    Session, SessionStatus, Participant, StartMode, EndMode, EventType,
    check_conservation, check_no_negative_positions
)
from ..storage import (
    EventStore, SessionRepository, ParticipantRepository, AllocationRepository
)


class SessionService:
    """Service for session lifecycle management."""

    def __init__(
        self,
        event_store: EventStore,
        session_repo: SessionRepository,
        participant_repo: ParticipantRepository,
        allocation_repo: AllocationRepository
    ):
        self.event_store = event_store
        self.session_repo = session_repo
        self.participant_repo = participant_repo
        self.allocation_repo = allocation_repo

    def create_session(
        self,
        session_id: str,
        legs: List[str],
        q: List[float],
        start_mode: StartMode = StartMode.IMMEDIATE,
        end_mode: EndMode = EndMode.MANUAL,
        duration_minutes: Optional[int] = None
    ) -> Session:
        """
        Create a new session.

        Args:
            session_id: Unique session identifier
            legs: List of leg names (e.g., ["AAPL", "NVDA", "META", "ORCL"])
            q: Basket quantities for each leg
            start_mode: How the session starts
            end_mode: How the session ends
            duration_minutes: Duration in minutes (if timed)

        Returns:
            Created session
        """
        if len(legs) != len(q):
            raise ValueError("legs and q must have same length")

        # Allow all zeros (will be auto-calculated from allocations)
        # But if any quantity is set, they all must be positive
        if not all(qty == 0 for qty in q) and any(qty <= 0 for qty in q):
            raise ValueError("Basket quantities must be all positive or all zero (for auto-calculation)")

        session = Session(
            session_id=session_id,
            legs=legs,
            q=q,
            status=SessionStatus.CREATED,
            start_mode=start_mode,
            end_mode=end_mode,
            created_at=datetime.utcnow()
        )

        # Append event
        self.event_store.append(
            session_id,
            EventType.SESSION_CREATED,
            {
                "session_id": session_id,
                "legs": legs,
                "q": q,
                "start_mode": start_mode.value,
                "end_mode": end_mode.value,
                "created_at": session.created_at.isoformat()
            }
        )

        # Update projection
        self.session_repo.create_session(session)

        # Auto-start if immediate
        if start_mode == StartMode.IMMEDIATE:
            self.start_session(session_id)

        return session

    def start_session(self, session_id: str) -> None:
        """Start a session."""
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status != SessionStatus.CREATED:
            raise ValueError(f"Session {session_id} is already {session.status}")

        t1 = datetime.utcnow()

        # Append event
        self.event_store.append(
            session_id,
            EventType.SESSION_STARTED,
            {"t1": t1.isoformat()}
        )

        # Update projection
        self.session_repo.update_session_status(session_id, SessionStatus.ACTIVE)

    def add_participant(
        self,
        session_id: str,
        participant_id: str,
        name: Optional[str] = None
    ) -> Participant:
        """Add a participant to a session."""
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        participant = Participant(
            participant_id=participant_id,
            session_id=session_id,
            name=name,
            joined_at=datetime.utcnow()
        )

        # Append event
        self.event_store.append(
            session_id,
            EventType.PARTICIPANT_JOINED,
            {
                "participant_id": participant_id,
                "session_id": session_id,
                "name": name,
                "joined_at": participant.joined_at.isoformat()
            }
        )

        # Update projection
        self.participant_repo.add_participant(participant)

        return participant

    def assign_initial_allocations(
        self,
        session_id: str,
        allocations: Optional[Dict[str, Dict[str, float]]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Assign initial allocations to participants.

        Args:
            session_id: Session identifier
            allocations: Custom allocations (if None, use equal pro-rata)

        Returns:
            Assigned allocations
        """
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        participants = self.participant_repo.get_participants(session_id)
        if not participants:
            raise ValueError(f"No participants in session {session_id}")

        basket = {leg: qty for leg, qty in zip(session.legs, session.q)}

        # If no custom allocations, distribute equally
        if allocations is None:
            allocations = {}
            num_participants = len(participants)
            for participant in participants:
                allocations[participant.participant_id] = {
                    leg: qty / num_participants
                    for leg, qty in basket.items()
                }

        # Auto-calculate basket from allocations if basket is empty (all zeros)
        if all(qty == 0 for qty in session.q):
            # Calculate basket from sum of allocations
            calculated_basket = {}
            for leg in session.legs:
                calculated_basket[leg] = sum(
                    participant_alloc.get(leg, 0.0)
                    for participant_alloc in allocations.values()
                )

            # Update session basket
            new_q = [calculated_basket.get(leg, 0.0) for leg in session.legs]
            session.q = new_q
            self.session_repo.update_session(session)
            basket = calculated_basket

        # Validate conservation
        check_conservation(allocations, basket)
        check_no_negative_positions(allocations)

        # Append events and update projections
        for participant_id, participant_alloc in allocations.items():
            self.event_store.append(
                session_id,
                EventType.INITIAL_ALLOCATION_ASSIGNED,
                {
                    "participant_id": participant_id,
                    "allocations": participant_alloc
                }
            )
            self.allocation_repo.set_allocations(session_id, participant_id, participant_alloc)

        return allocations

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        return self.session_repo.get_session(session_id)

    def list_sessions(self) -> List[Session]:
        """List all sessions."""
        return self.session_repo.list_sessions()

    def get_participants(self, session_id: str) -> List[Participant]:
        """Get all participants in a session."""
        return self.participant_repo.get_participants(session_id)

    def get_allocations(self, session_id: str) -> Dict[str, Dict[str, float]]:
        """Get current allocations for a session."""
        return self.allocation_repo.get_allocations(session_id)
