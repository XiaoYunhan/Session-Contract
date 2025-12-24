from ..services import SessionService, TradingService, SettlementService, PriceService, OrderService
from ..storage import (
    EventStore, SessionRepository, ParticipantRepository,
    AllocationRepository, TradingRepository, PriceRepository,
    SettlementRepository, OrderRepository
)

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
