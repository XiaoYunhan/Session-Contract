from typing import List
from fastapi import APIRouter, HTTPException, Depends
from ...services import SessionService
from ..models import (
    AddParticipantRequest, ParticipantResponse
)
from ..dependencies import get_session_service

router = APIRouter()

@router.post("/sessions/{session_id}/participants", response_model=ParticipantResponse)
async def add_participant(
    session_id: str,
    request: AddParticipantRequest,
    service: SessionService = Depends(get_session_service)
):
    """Add participant to session with optional initial allocations."""
    try:
        participant = service.add_participant(
            session_id=session_id,
            participant_id=request.participant_id,
            name=request.name
        )

        # Set initial allocations if provided
        if request.initial_allocations:
            service.assign_initial_allocations(
                session_id=session_id,
                allocations={request.participant_id: request.initial_allocations}
            )

        return ParticipantResponse(
            participant_id=participant.participant_id,
            session_id=participant.session_id,
            name=participant.name,
            joined_at=participant.joined_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/participants", response_model=List[ParticipantResponse])
async def get_participants(
    session_id: str,
    service: SessionService = Depends(get_session_service)
):
    """Get all participants in a session."""
    participants = service.get_participants(session_id)
    return [
        ParticipantResponse(
            participant_id=p.participant_id,
            session_id=p.session_id,
            name=p.name,
            joined_at=p.joined_at.isoformat()
        )
        for p in participants
    ]
