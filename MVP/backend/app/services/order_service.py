"""Order service for order placement and matching."""
import uuid
from typing import List, Dict, Optional
from datetime import datetime

from ..domain.types import (
    Order, OrderType, OrderSide, OrderStatus,
    EventType, Trade
)
from ..storage.event_store import EventStore
from ..storage.order_repository import OrderRepository
from ..storage.repository import SessionRepository, AllocationRepository, TradingRepository


class OrderService:
    """Service for order management and matching."""

    def __init__(
        self,
        event_store: EventStore,
        order_repo: OrderRepository,
        session_repo: SessionRepository,
        alloc_repo: AllocationRepository,
        trading_repo: TradingRepository
    ):
        self.event_store = event_store
        self.order_repo = order_repo
        self.session_repo = session_repo
        self.alloc_repo = alloc_repo
        self.trading_repo = trading_repo

    def place_order(
        self,
        session_id: str,
        participant_id: str,
        asset: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None
    ) -> Order:
        """Place a new order."""
        # Validate session exists and is active
        session = self.session_repo.get_session(session_id)
        if not session:
            raise ValueError("Session not found")

        if session.status != "active":
            raise ValueError("Session is not active")

        # Validate asset is in session legs
        if asset not in session.legs:
            raise ValueError(f"Asset {asset} not in session legs")

        # Validate limit orders have a price
        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("Limit orders must have a price")

        # Check participant has sufficient holdings if selling
        if side == OrderSide.SELL:
            allocations = self.alloc_repo.get_allocations(session_id)
            participant_alloc = allocations.get(participant_id, {})
            current_holding = participant_alloc.get(asset, 0)

            if current_holding < quantity:
                raise ValueError(f"Insufficient {asset} holdings. Have {current_holding}, need {quantity}")

        # Create order
        order = Order(
            order_id=str(uuid.uuid4()),
            session_id=session_id,
            participant_id=participant_id,
            asset=asset,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            filled_quantity=0.0,
            status=OrderStatus.PENDING
        )

        # Save order
        self.order_repo.save_order(order)

        # Emit event
        self.event_store.append_event(
            session_id=session_id,
            event_type=EventType.ORDER_PLACED,
            data={
                "order_id": order.order_id,
                "participant_id": participant_id,
                "asset": asset,
                "side": side.value,
                "order_type": order_type.value,
                "quantity": quantity,
                "price": price
            }
        )

        # Try to match immediately
        self._match_orders(session_id, asset)

        # Return updated order
        return self.order_repo.get_order(order.order_id)

    def cancel_order(self, order_id: str) -> Order:
        """Cancel an order."""
        order = self.order_repo.get_order(order_id)
        if not order:
            raise ValueError("Order not found")

        if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
            raise ValueError(f"Cannot cancel order with status {order.status}")

        order.status = OrderStatus.CANCELLED
        self.order_repo.update_order(order)

        self.event_store.append_event(
            session_id=order.session_id,
            event_type=EventType.ORDER_CANCELLED,
            data={"order_id": order_id}
        )

        return order

    def get_order_book(self, session_id: str, asset: str) -> dict:
        """Get order book for an asset."""
        return self.order_repo.get_order_book(session_id, asset)

    def get_orders(self, session_id: str) -> List[Order]:
        """Get all orders for a session."""
        return self.order_repo.get_orders_by_session(session_id)

    def _match_orders(self, session_id: str, asset: str):
        """Match pending orders for an asset."""
        pending_orders = self.order_repo.get_pending_orders(session_id, asset)

        # Separate into buy and sell orders
        buy_orders = [o for o in pending_orders if o.side == OrderSide.BUY]
        sell_orders = [o for o in pending_orders if o.side == OrderSide.SELL]

        # Sort: market orders first, then by price
        buy_orders.sort(key=lambda x: (
            0 if x.order_type == OrderType.MARKET else 1,
            -(x.price or float('inf'))
        ))
        sell_orders.sort(key=lambda x: (
            0 if x.order_type == OrderType.MARKET else 1,
            x.price or 0
        ))

        # Match orders
        while buy_orders and sell_orders:
            buy_order = buy_orders[0]
            sell_order = sell_orders[0]

            # Check if orders can match
            if not self._can_match(buy_order, sell_order):
                break

            # Execute trade
            buy_remaining = buy_order.quantity - buy_order.filled_quantity
            sell_remaining = sell_order.quantity - sell_order.filled_quantity
            trade_quantity = min(buy_remaining, sell_remaining)

            # Determine trade price (use limit price if available, otherwise use sell price)
            trade_price = self._determine_trade_price(buy_order, sell_order)

            # Execute trade and update allocations
            self._execute_trade(
                session_id=session_id,
                buyer_id=buy_order.participant_id,
                seller_id=sell_order.participant_id,
                asset=asset,
                quantity=trade_quantity,
                price=trade_price,
                buy_order_id=buy_order.order_id,
                sell_order_id=sell_order.order_id
            )

            # Update orders
            buy_order.filled_quantity += trade_quantity
            if buy_order.filled_quantity >= buy_order.quantity:
                buy_order.status = OrderStatus.FILLED
                buy_orders.pop(0)
            else:
                buy_order.status = OrderStatus.PARTIAL

            sell_order.filled_quantity += trade_quantity
            if sell_order.filled_quantity >= sell_order.quantity:
                sell_order.status = OrderStatus.FILLED
                sell_orders.pop(0)
            else:
                sell_order.status = OrderStatus.PARTIAL

            self.order_repo.update_order(buy_order)
            self.order_repo.update_order(sell_order)

    def _can_match(self, buy_order: Order, sell_order: Order) -> bool:
        """Check if two orders can match."""
        # Market orders can always match
        if buy_order.order_type == OrderType.MARKET or sell_order.order_type == OrderType.MARKET:
            return True

        # Limit orders: buy price must be >= sell price
        if buy_order.price and sell_order.price:
            return buy_order.price >= sell_order.price

        return False

    def _determine_trade_price(self, buy_order: Order, sell_order: Order) -> float:
        """Determine the trade price based on order types."""
        # If one is a market order, use the limit order's price
        if buy_order.order_type == OrderType.MARKET and sell_order.price:
            return sell_order.price
        if sell_order.order_type == OrderType.MARKET and buy_order.price:
            return buy_order.price

        # Both are limit orders: use the sell order price (price-time priority)
        if sell_order.price:
            return sell_order.price

        # Fallback (shouldn't happen)
        return buy_order.price or 0.0

    def _execute_trade(
        self,
        session_id: str,
        buyer_id: str,
        seller_id: str,
        asset: str,
        quantity: float,
        price: float,
        buy_order_id: str,
        sell_order_id: str
    ):
        """Execute a trade and update allocations."""
        # Get current allocations
        allocations = self.alloc_repo.get_allocations(session_id)

        # Update buyer: increase asset, decrease cash
        buyer_alloc = allocations.get(buyer_id, {})
        buyer_alloc[asset] = buyer_alloc.get(asset, 0) + quantity
        buyer_alloc["CASH"] = buyer_alloc.get("CASH", 0) - (quantity * price)

        # Update seller: decrease asset, increase cash
        seller_alloc = allocations.get(seller_id, {})
        seller_alloc[asset] = seller_alloc.get(asset, 0) - quantity
        seller_alloc["CASH"] = seller_alloc.get("CASH", 0) + (quantity * price)

        # Update allocations in database
        self.alloc_repo.update_allocation(session_id, buyer_id, buyer_alloc)
        self.alloc_repo.update_allocation(session_id, seller_id, seller_alloc)

        # Create trade record
        trade_id = str(uuid.uuid4())
        trade = Trade(
            trade_id=trade_id,
            session_id=session_id,
            rfq_id=buy_order_id,  # Reusing field for buy order ID
            quote_id=sell_order_id,  # Reusing field for sell order ID
            participant_a=buyer_id,
            participant_b=seller_id,
            leg_from="CASH",
            leg_to=asset,
            amount_from=quantity * price,
            amount_to=quantity,
            executed_at=datetime.utcnow()
        )

        # Save trade
        self.trading_repo.save_trade(trade)

        # Emit event
        self.event_store.append_event(
            session_id=session_id,
            event_type=EventType.ORDER_MATCHED,
            data={
                "trade_id": trade_id,
                "buyer_id": buyer_id,
                "seller_id": seller_id,
                "asset": asset,
                "quantity": quantity,
                "price": price,
                "buy_order_id": buy_order_id,
                "sell_order_id": sell_order_id
            }
        )
