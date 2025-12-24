from fastapi import APIRouter, HTTPException, Depends
from ...domain import InvariantViolation
from ...services import TradingService
from ..models import (
    CreateRFQRequest, RFQResponse, ProvideQuoteRequest, QuoteResponse, TradeResponse
)
from ..dependencies import get_trading_service

router = APIRouter()

@router.post("/sessions/{session_id}/rfq", response_model=RFQResponse)
async def create_rfq(
    session_id: str,
    request: CreateRFQRequest,
    service: TradingService = Depends(get_trading_service)
):
    """Create a request for quote."""
    try:
        rfq = service.create_rfq(
            session_id=session_id,
            requester_id=request.requester_id,
            leg_from=request.leg_from,
            leg_to=request.leg_to,
            amount_from=request.amount_from
        )
        return RFQResponse(
            rfq_id=rfq.rfq_id,
            session_id=rfq.session_id,
            requester_id=rfq.requester_id,
            leg_from=rfq.leg_from,
            leg_to=rfq.leg_to,
            amount_from=rfq.amount_from,
            status=rfq.status.value,
            created_at=rfq.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rfq/{rfq_id}/quote", response_model=QuoteResponse)
async def provide_quote(
    rfq_id: str,
    request: ProvideQuoteRequest,
    service: TradingService = Depends(get_trading_service)
):
    """Provide a quote for an RFQ."""
    try:
        quote = service.provide_quote(
            rfq_id=rfq_id,
            quoter_id=request.quoter_id,
            rate=request.rate
        )
        return QuoteResponse(
            quote_id=quote.quote_id,
            rfq_id=quote.rfq_id,
            quoter_id=quote.quoter_id,
            rate=quote.rate,
            created_at=quote.created_at.isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/quotes/{quote_id}/accept", response_model=TradeResponse)
async def accept_quote(
    quote_id: str,
    service: TradingService = Depends(get_trading_service)
):
    """Accept a quote and execute trade."""
    try:
        trade = service.accept_quote(quote_id)

        # Broadcast trade and updated allocations via WebSocket
        from ..websocket import broadcast_trade, broadcast_allocation_update

        # Broadcast trade
        await broadcast_trade(trade.session_id, {
            "trade_id": trade.trade_id,
            "participant_a": trade.participant_a,
            "participant_b": trade.participant_b,
            "leg_from": trade.leg_from,
            "leg_to": trade.leg_to,
            "amount_from": trade.amount_from,
            "amount_to": trade.amount_to,
            "executed_at": trade.executed_at.isoformat()
        })

        # Broadcast updated allocations
        from ...storage import AllocationRepository
        alloc_repo = AllocationRepository()
        allocations = alloc_repo.get_allocations(trade.session_id)
        await broadcast_allocation_update(trade.session_id, allocations)

        return TradeResponse(
            trade_id=trade.trade_id,
            session_id=trade.session_id,
            rfq_id=trade.rfq_id,
            quote_id=trade.quote_id,
            participant_a=trade.participant_a,
            participant_b=trade.participant_b,
            leg_from=trade.leg_from,
            leg_to=trade.leg_to,
            amount_from=trade.amount_from,
            amount_to=trade.amount_to,
            executed_at=trade.executed_at.isoformat()
        )
    except (ValueError, InvariantViolation) as e:
        raise HTTPException(status_code=400, detail=str(e))
