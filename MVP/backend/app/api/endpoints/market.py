from typing import List
from fastapi import APIRouter, HTTPException, Depends
from ...domain import InvariantViolation
from ...domain.types import OrderType, OrderSide
from ...services import PriceService, OrderService
from ..models import (
    UpdatePricesRequest, PriceTickResponse, PlaceOrderRequest, OrderResponse, OrderBookResponse
)
from ..dependencies import get_price_service, get_order_service

router = APIRouter()

# Price routes
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
        from ..websocket import broadcast_price_update
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
