"""Order repository for database operations."""
import json
import uuid
from typing import List, Optional
from datetime import datetime

from .database import get_db
from ..domain.types import Order, OrderStatus, OrderSide, OrderType


class OrderRepository:
    """Repository for order data."""

    def save_order(self, order: Order) -> Order:
        """Save an order."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (
                    order_id, session_id, participant_id, asset,
                    side, order_type, quantity, price,
                    filled_quantity, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.order_id,
                order.session_id,
                order.participant_id,
                order.asset,
                order.side.value,
                order.order_type.value,
                order.quantity,
                order.price,
                order.filled_quantity,
                order.status.value,
                order.created_at.isoformat(),
                order.updated_at.isoformat()
            ))
            return order

    def update_order(self, order: Order) -> Order:
        """Update an existing order."""
        order.updated_at = datetime.utcnow()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE orders
                SET filled_quantity = ?, status = ?, updated_at = ?
                WHERE order_id = ?
            """, (
                order.filled_quantity,
                order.status.value,
                order.updated_at.isoformat(),
                order.order_id
            ))
            return order

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM orders WHERE order_id = ?
            """, (order_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return Order(
                order_id=row["order_id"],
                session_id=row["session_id"],
                participant_id=row["participant_id"],
                asset=row["asset"],
                side=OrderSide(row["side"]),
                order_type=OrderType(row["order_type"]),
                quantity=row["quantity"],
                price=row["price"],
                filled_quantity=row["filled_quantity"],
                status=OrderStatus(row["status"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )

    def get_orders_by_session(self, session_id: str) -> List[Order]:
        """Get all orders for a session."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM orders
                WHERE session_id = ?
                ORDER BY created_at DESC
            """, (session_id,))
            rows = cursor.fetchall()

            return [
                Order(
                    order_id=row["order_id"],
                    session_id=row["session_id"],
                    participant_id=row["participant_id"],
                    asset=row["asset"],
                    side=OrderSide(row["side"]),
                    order_type=OrderType(row["order_type"]),
                    quantity=row["quantity"],
                    price=row["price"],
                    filled_quantity=row["filled_quantity"],
                    status=OrderStatus(row["status"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"])
                )
                for row in rows
            ]

    def get_pending_orders(self, session_id: str, asset: str) -> List[Order]:
        """Get all pending/partial orders for a specific asset in a session."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM orders
                WHERE session_id = ? AND asset = ?
                AND status IN ('pending', 'partial')
                ORDER BY
                    CASE
                        WHEN order_type = 'market' THEN 0
                        ELSE 1
                    END,
                    created_at ASC
            """, (session_id, asset))
            rows = cursor.fetchall()

            return [
                Order(
                    order_id=row["order_id"],
                    session_id=row["session_id"],
                    participant_id=row["participant_id"],
                    asset=row["asset"],
                    side=OrderSide(row["side"]),
                    order_type=OrderType(row["order_type"]),
                    quantity=row["quantity"],
                    price=row["price"],
                    filled_quantity=row["filled_quantity"],
                    status=OrderStatus(row["status"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"])
                )
                for row in rows
            ]

    def get_order_book(self, session_id: str, asset: str) -> dict:
        """Get order book (bids and asks) for a specific asset."""
        pending_orders = self.get_pending_orders(session_id, asset)

        bids = []  # buy orders
        asks = []  # sell orders

        for order in pending_orders:
            remaining = order.quantity - order.filled_quantity
            order_data = {
                "order_id": order.order_id,
                "participant_id": order.participant_id,
                "price": order.price,
                "quantity": remaining,
                "order_type": order.order_type.value
            }

            if order.side == OrderSide.BUY:
                bids.append(order_data)
            else:
                asks.append(order_data)

        # Sort bids (highest price first)
        bids.sort(key=lambda x: (x["order_type"] == "market", x["price"] or float('inf')), reverse=True)
        # Sort asks (lowest price first)
        asks.sort(key=lambda x: (x["order_type"] == "limit", x["price"] or 0))

        return {
            "asset": asset,
            "bids": bids,
            "asks": asks
        }
