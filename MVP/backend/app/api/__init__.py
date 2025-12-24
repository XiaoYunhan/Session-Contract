"""API layer for Session Contracts."""
from fastapi import APIRouter
from .endpoints import sessions, participants, trading, market
from .websocket import websocket_endpoint, manager

router = APIRouter()
router.include_router(sessions.router, tags=["sessions"])
router.include_router(participants.router, tags=["participants"])
router.include_router(trading.router, tags=["trading"])
router.include_router(market.router, tags=["market"])

__all__ = ["router", "websocket_endpoint", "manager"]
