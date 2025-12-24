from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from ...domain import StartMode, EndMode, InvariantViolation
from ...services import SessionService, SettlementService
from ..models import (
    CreateSessionRequest, SessionResponse, AssignAllocationsRequest,
    SettlementResponse
)
from ..dependencies import get_session_service, get_settlement_service

router = APIRouter()

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    service: SessionService = Depends(get_session_service)
):
    """Create a new session. Basket quantities (q) are optional and will be auto-calculated from allocations if not provided."""
    try:
        # If basket quantities not provided, use placeholder zeros (will be calculated from allocations)
        q = request.q if request.q else [0.0] * len(request.legs)

        session = service.create_session(
            session_id=request.session_id,
            legs=request.legs,
            q=q,
            start_mode=StartMode(request.start_mode),
            end_mode=EndMode(request.end_mode),
            duration_minutes=request.duration_minutes
        )
        return SessionResponse(
            session_id=session.session_id,
            legs=session.legs,
            q=session.q,
            t1=session.t1.isoformat() if session.t1 else None,
            t2=session.t2.isoformat() if session.t2 else None,
            status=session.status.value,
            start_mode=session.start_mode.value,
            end_mode=session.end_mode.value,
            created_at=session.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(service: SessionService = Depends(get_session_service)):
    """List all sessions."""
    sessions = service.list_sessions()
    return [
        SessionResponse(
            session_id=s.session_id,
            legs=s.legs,
            q=s.q,
            t1=s.t1.isoformat() if s.t1 else None,
            t2=s.t2.isoformat() if s.t2 else None,
            status=s.status.value,
            start_mode=s.start_mode.value,
            end_mode=s.end_mode.value,
            created_at=s.created_at.isoformat()
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
):
    """Get session details."""
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=session.session_id,
        legs=session.legs,
        q=session.q,
        t1=session.t1.isoformat() if session.t1 else None,
        t2=session.t2.isoformat() if session.t2 else None,
        status=session.status.value,
        start_mode=session.start_mode.value,
        end_mode=session.end_mode.value,
        created_at=session.created_at.isoformat()
    )


@router.post("/sessions/{session_id}/start")
async def start_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
):
    """Start a session manually."""
    try:
        service.start_session(session_id)
        return {"status": "started"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
):
    """Delete a session."""
    try:
        from ...storage.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            # Delete in reverse order of foreign keys
            cursor.execute("DELETE FROM allocations WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM price_ticks WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM trades WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM quotes WHERE rfq_id IN (SELECT rfq_id FROM rfqs WHERE session_id = ?)", (session_id,))
            cursor.execute("DELETE FROM rfqs WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM participants WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM settlements WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM events WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        return {"status": "deleted", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Allocation routes (Session related)
@router.post("/sessions/{session_id}/allocations")
async def assign_allocations(
    session_id: str,
    request: AssignAllocationsRequest,
    service: SessionService = Depends(get_session_service)
):
    """Assign initial allocations."""
    try:
        allocations = service.assign_initial_allocations(
            session_id=session_id,
            allocations=request.allocations
        )
        return {"allocations": allocations}
    except (ValueError, InvariantViolation) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/allocations")
async def get_allocations(
    session_id: str,
    service: SessionService = Depends(get_session_service)
):
    """Get current allocations."""
    allocations = service.get_allocations(session_id)
    return {"allocations": allocations}

# Settlement routes (Session related)
@router.post("/sessions/{session_id}/settle", response_model=SettlementResponse)
async def settle_session(
    session_id: str,
    service: SettlementService = Depends(get_settlement_service)
):
    """Settle a session."""
    try:
        settlement = service.settle_session(session_id)
        return SettlementResponse(
            session_id=settlement.session_id,
            settlement_prices=settlement.settlement_prices,
            payouts=settlement.payouts,
            settled_at=settlement.settled_at.isoformat()
        )
    except (ValueError, InvariantViolation) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/settlement", response_model=SettlementResponse)
async def get_settlement(
    session_id: str,
    service: SettlementService = Depends(get_settlement_service)
):
    """Get settlement for a session."""
    settlement = service.get_settlement(session_id)
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")

    return SettlementResponse(
        session_id=settlement.session_id,
        settlement_prices=settlement.settlement_prices,
        payouts=settlement.payouts,
        settled_at=settlement.settled_at.isoformat()
    )
