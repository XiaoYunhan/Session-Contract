"""WebSocket handler for real-time updates."""
import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime


class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        # session_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register a new connection."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a connection."""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, message: dict):
        """Broadcast message to all connections for a session."""
        if session_id not in self.active_connections:
            return

        # Add timestamp
        message["timestamp"] = datetime.utcnow().isoformat()

        dead_connections = set()
        for websocket in self.active_connections[session_id]:
            try:
                await websocket.send_json(message)
            except Exception:
                dead_connections.add(websocket)

        # Clean up dead connections
        for websocket in dead_connections:
            self.disconnect(websocket, session_id)

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to a specific connection."""
        message["timestamp"] = datetime.utcnow().isoformat()
        try:
            await websocket.send_json(message)
        except Exception:
            pass


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for session updates."""
    await manager.connect(websocket, session_id)

    try:
        # Send initial connection confirmation
        await manager.send_personal(websocket, {
            "type": "connected",
            "session_id": session_id,
            "message": "Connected to session updates"
        })

        # Keep connection alive and handle any incoming messages
        while True:
            data = await websocket.receive_text()
            # Echo or handle ping/pong
            if data == "ping":
                await manager.send_personal(websocket, {
                    "type": "pong",
                    "session_id": session_id
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        manager.disconnect(websocket, session_id)


# Helper functions to broadcast events
async def broadcast_price_update(session_id: str, prices: Dict[str, float]):
    """Broadcast price update."""
    await manager.broadcast(session_id, {
        "type": "price_update",
        "session_id": session_id,
        "prices": prices
    })


async def broadcast_trade(session_id: str, trade: dict):
    """Broadcast trade execution."""
    await manager.broadcast(session_id, {
        "type": "trade_executed",
        "session_id": session_id,
        "trade": trade
    })


async def broadcast_allocation_update(session_id: str, allocations: Dict[str, Dict[str, float]]):
    """Broadcast allocation update."""
    await manager.broadcast(session_id, {
        "type": "allocation_update",
        "session_id": session_id,
        "allocations": allocations
    })


async def broadcast_session_status(session_id: str, status: str):
    """Broadcast session status change."""
    await manager.broadcast(session_id, {
        "type": "session_status",
        "session_id": session_id,
        "status": status
    })


async def broadcast_rfq(session_id: str, rfq: dict):
    """Broadcast new RFQ."""
    await manager.broadcast(session_id, {
        "type": "rfq_created",
        "session_id": session_id,
        "rfq": rfq
    })


async def broadcast_quote(session_id: str, quote: dict):
    """Broadcast new quote."""
    await manager.broadcast(session_id, {
        "type": "quote_provided",
        "session_id": session_id,
        "quote": quote
    })
