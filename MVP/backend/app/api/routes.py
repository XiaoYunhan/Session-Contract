"""REST API routes."""
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Depends

from .models import (
    CreateSessionRequest, AddParticipantRequest, AssignAllocationsRequest,
    CreateRFQRequest, ProvideQuoteRequest, UpdatePricesRequest,
    SessionResponse, ParticipantResponse, AllocationResponse,
    RFQResponse, QuoteResponse, TradeResponse, SettlementResponse,
    PriceTickResponse, PlaceOrderRequest, OrderResponse, OrderBookResponse
)
from ..services import SessionService, TradingService, SettlementService, PriceService, OrderService
from ..storage import (
    EventStore, SessionRepository, ParticipantRepository,
    AllocationRepository, TradingRepository, PriceRepository,
    SettlementRepository, OrderRepository
)
from ..domain import StartMode, EndMode, InvariantViolation
from ..domain.types import OrderType, OrderSide


router = APIRouter()


# Dependency injection
def get_session_service() -> SessionService:
    return SessionService(
        EventStore(),
        SessionRepository(),
        ParticipantRepository(),
        AllocationRepository()
    )


def get_trading_service() -> TradingService:
    return TradingService(
        EventStore(),
        SessionRepository(),
        TradingRepository(),
        AllocationRepository()
    )


def get_settlement_service() -> SettlementService:
    return SettlementService(
        EventStore(),
        SessionRepository(),
        AllocationRepository(),
        PriceRepository(),
        SettlementRepository()
    )


def get_price_service() -> PriceService:
    return PriceService(
        EventStore(),
        PriceRepository()
    )


def get_order_service() -> OrderService:
    return OrderService(
        EventStore(),
        OrderRepository(),
        SessionRepository(),
        AllocationRepository(),
        TradingRepository()
    )


# Session routes
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
        from ..storage.database import get_db
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


# Participant routes
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


# Allocation routes
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


# Trading routes
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
        from .websocket import broadcast_trade, broadcast_allocation_update

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
        from ..storage import AllocationRepository
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


# Settlement routes
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


# Price routes (for oracle)
@router.post("/sessions/{session_id}/prices", response_model=PriceTickResponse)
async def update_prices(
    session_id: str,
    request: UpdatePricesRequest,
    service: PriceService = Depends(get_price_service)
):
    """Update prices (called by oracle)."""
    try:
        tick = service.update_prices(session_id, request.prices)

        # Broadcast price update via WebSocket
        from .websocket import broadcast_price_update
        await broadcast_price_update(session_id, request.prices)

        return PriceTickResponse(
            session_id=tick.session_id,
            timestamp=tick.timestamp.isoformat(),
            prices=tick.prices
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/prices")
async def get_latest_prices(
    session_id: str,
    service: PriceService = Depends(get_price_service)
):
    """Get latest prices for a session."""
    prices = service.get_latest_prices(session_id)
    if not prices:
        raise HTTPException(status_code=404, detail="No prices available")

    return {"prices": prices}


# Order routes
@router.post("/sessions/{session_id}/orders", response_model=OrderResponse)
async def place_order(
    session_id: str,
    request: PlaceOrderRequest,
    service: OrderService = Depends(get_order_service)
):
    """Place a market or limit order."""
    try:
        order = service.place_order(
            session_id=session_id,
            participant_id=request.participant_id,
            asset=request.asset,
            side=OrderSide(request.side),
            order_type=OrderType(request.order_type),
            quantity=request.quantity,
            price=request.price
        )
        return OrderResponse(
            order_id=order.order_id,
            session_id=order.session_id,
            participant_id=order.participant_id,
            asset=order.asset,
            side=order.side.value,
            order_type=order.order_type.value,
            quantity=order.quantity,
            price=order.price,
            filled_quantity=order.filled_quantity,
            status=order.status.value,
            created_at=order.created_at.isoformat(),
            updated_at=order.updated_at.isoformat()
        )
    except (ValueError, InvariantViolation) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{session_id}/orders", response_model=List[OrderResponse])
async def get_orders(
    session_id: str,
    service: OrderService = Depends(get_order_service)
):
    """Get all orders for a session."""
    orders = service.get_orders(session_id)
    return [
        OrderResponse(
            order_id=o.order_id,
            session_id=o.session_id,
            participant_id=o.participant_id,
            asset=o.asset,
            side=o.side.value,
            order_type=o.order_type.value,
            quantity=o.quantity,
            price=o.price,
            filled_quantity=o.filled_quantity,
            status=o.status.value,
            created_at=o.created_at.isoformat(),
            updated_at=o.updated_at.isoformat()
        )
        for o in orders
    ]


@router.get("/sessions/{session_id}/orderbook/{asset}", response_model=OrderBookResponse)
async def get_order_book(
    session_id: str,
    asset: str,
    service: OrderService = Depends(get_order_service)
):
    """Get order book for a specific asset."""
    order_book = service.get_order_book(session_id, asset)
    return OrderBookResponse(**order_book)


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    service: OrderService = Depends(get_order_service)
):
    """Cancel an order."""
    try:
        order = service.cancel_order(order_id)
        return {"status": "cancelled", "order_id": order_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
