"""API request/response models."""
from typing import List, Dict, Optional
from pydantic import BaseModel


# Request models
class CreateSessionRequest(BaseModel):
    session_id: str
    legs: List[str]
    q: Optional[List[float]] = None  # Optional: auto-calculated from allocations if not provided
    start_mode: str = "immediate"
    end_mode: str = "manual"
    duration_minutes: Optional[int] = None


class AddParticipantRequest(BaseModel):
    participant_id: str
    name: Optional[str] = None
    initial_allocations: Optional[Dict[str, float]] = None  # leg -> quantity


class AssignAllocationsRequest(BaseModel):
    allocations: Optional[Dict[str, Dict[str, float]]] = None


class CreateRFQRequest(BaseModel):
    requester_id: str
    leg_from: str
    leg_to: str
    amount_from: float


class ProvideQuoteRequest(BaseModel):
    quoter_id: str
    rate: float


class UpdatePricesRequest(BaseModel):
    prices: Dict[str, float]


# Response models
class SessionResponse(BaseModel):
    session_id: str
    legs: List[str]
    q: List[float]
    t1: Optional[str] = None
    t2: Optional[str] = None
    status: str
    start_mode: str
    end_mode: str
    created_at: str


class ParticipantResponse(BaseModel):
    participant_id: str
    session_id: str
    name: Optional[str] = None
    joined_at: str


class AllocationResponse(BaseModel):
    session_id: str
    participant_id: str
    allocations: Dict[str, float]


class RFQResponse(BaseModel):
    rfq_id: str
    session_id: str
    requester_id: str
    leg_from: str
    leg_to: str
    amount_from: float
    status: str
    created_at: str


class QuoteResponse(BaseModel):
    quote_id: str
    rfq_id: str
    quoter_id: str
    rate: float
    created_at: str


class TradeResponse(BaseModel):
    trade_id: str
    session_id: str
    rfq_id: str
    quote_id: str
    participant_a: str
    participant_b: str
    leg_from: str
    leg_to: str
    amount_from: float
    amount_to: float
    executed_at: str


class SettlementResponse(BaseModel):
    session_id: str
    settlement_prices: Dict[str, float]
    payouts: Dict[str, float]
    settled_at: str


class PriceTickResponse(BaseModel):
    session_id: str
    timestamp: str
    prices: Dict[str, float]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# Order-based trading models
class PlaceOrderRequest(BaseModel):
    participant_id: str
    asset: str
    side: str  # "buy" or "sell"
    order_type: str  # "market" or "limit"
    quantity: float
    price: Optional[float] = None  # Required for limit orders


class OrderResponse(BaseModel):
    order_id: str
    session_id: str
    participant_id: str
    asset: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    filled_quantity: float
    status: str
    created_at: str
    updated_at: str


class OrderBookResponse(BaseModel):
    asset: str
    bids: List[Dict]
    asks: List[Dict]
