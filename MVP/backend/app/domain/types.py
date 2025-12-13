"""Core domain types for Session Contracts."""
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Session lifecycle states."""
    CREATED = "created"
    ACTIVE = "active"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class StartMode(str, Enum):
    """Session start trigger."""
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class EndMode(str, Enum):
    """Session end trigger."""
    TIMED = "timed"
    MANUAL = "manual"


class EventType(str, Enum):
    """Event sourcing event types."""
    SESSION_CREATED = "SessionCreated"
    PARTICIPANT_JOINED = "ParticipantJoined"
    INITIAL_ALLOCATION_ASSIGNED = "InitialAllocationAssigned"
    SESSION_STARTED = "SessionStarted"
    PRICE_TICK = "PriceTick"
    RFQ_REQUESTED = "RFQRequested"
    QUOTE_PROVIDED = "QuoteProvided"
    TRADE_EXECUTED = "TradeExecuted"
    SESSION_SETTLED = "SessionSettled"
    ORDER_PLACED = "OrderPlaced"
    ORDER_CANCELLED = "OrderCancelled"
    ORDER_MATCHED = "OrderMatched"


class RFQStatus(str, Enum):
    """RFQ lifecycle states."""
    OPEN = "open"
    QUOTED = "quoted"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OrderType(str, Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"


class OrderSide(str, Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order lifecycle states."""
    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Session(BaseModel):
    """Session domain model."""
    session_id: str
    legs: List[str]  # e.g., ["AAPL", "NVDA", "META", "ORCL"]
    q: List[float]  # basket quantities
    t1: Optional[datetime] = None  # start time
    t2: Optional[datetime] = None  # end time
    status: SessionStatus = SessionStatus.CREATED
    start_mode: StartMode = StartMode.IMMEDIATE
    end_mode: EndMode = EndMode.MANUAL
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Participant(BaseModel):
    """Participant in a session."""
    participant_id: str
    session_id: str
    name: Optional[str] = None
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class Allocation(BaseModel):
    """Current allocation for a participant."""
    session_id: str
    participant_id: str
    allocations: Dict[str, float]  # leg -> quantity


class PriceTick(BaseModel):
    """Price snapshot for all legs."""
    session_id: str
    timestamp: datetime
    prices: Dict[str, float]  # leg -> price


class RFQ(BaseModel):
    """Request for quote."""
    rfq_id: str
    session_id: str
    requester_id: str
    leg_from: str
    leg_to: str
    amount_from: float  # amount willing to give
    status: RFQStatus = RFQStatus.OPEN
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class Quote(BaseModel):
    """Quote response to an RFQ."""
    quote_id: str
    rfq_id: str
    quoter_id: str
    rate: float  # amount_to / amount_from (e.g., 0.62 means give 10, get 6.2)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class Trade(BaseModel):
    """Executed trade."""
    trade_id: str
    session_id: str
    rfq_id: str
    quote_id: str
    participant_a: str  # requester
    participant_b: str  # quoter
    leg_from: str
    leg_to: str
    amount_from: float
    amount_to: float
    executed_at: datetime = Field(default_factory=datetime.utcnow)


class Order(BaseModel):
    """Market or limit order."""
    order_id: str
    session_id: str
    participant_id: str
    asset: str  # the leg being traded
    side: OrderSide  # buy or sell
    order_type: OrderType  # market or limit
    quantity: float  # quantity of asset
    price: Optional[float] = None  # limit price (None for market orders)
    filled_quantity: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Settlement(BaseModel):
    """Settlement result."""
    session_id: str
    settlement_prices: Dict[str, float]  # S_t2
    payouts: Dict[str, float]  # participant_id -> payout
    settled_at: datetime = Field(default_factory=datetime.utcnow)


class Event(BaseModel):
    """Event sourcing event."""
    event_id: str
    session_id: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict  # event-specific payload
    sequence: int = 0  # for ordering
