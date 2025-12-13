"""FastAPI application entry point."""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .storage import init_db
from .api import router, websocket_endpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    init_db()
    yield
    # Shutdown (if needed)


app = FastAPI(
    title="Session Contracts API",
    description="Multi-asset allocation market with ring-fenced collateral",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API routes
app.include_router(router, prefix="/api/v1")

# WebSocket endpoint
@app.websocket("/ws/sessions/{session_id}")
async def websocket_handler(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time session updates."""
    await websocket_endpoint(websocket, session_id)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Session Contracts API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
