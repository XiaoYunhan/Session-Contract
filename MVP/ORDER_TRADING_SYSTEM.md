# Order-Based Trading System - Implementation Summary

## Overview

The Session Contracts system has been refactored to support a traditional **order-based trading model** with market and limit orders, replacing the previous RFQ (Request for Quote) system. This allows investors to trade assets more intuitively during active sessions.

## Key Features

### 1. **Session Initialization**
- Define which assets are included in the session (e.g., AAPL, NVDA, META, ORCL)
- Set the basket quantities for each asset
- Assign initial allocations to participants when they join
- Start/stop sessions manually or automatically

### 2. **Investor Holdings**
- Each participant has holdings tracked across all assets
- Initial allocations can be set when participants join
- Holdings are updated in real-time as trades execute
- CASH balance is maintained for each participant

### 3. **Order Types**
- **Market Orders**: Execute immediately at the best available price
- **Limit Orders**: Execute only at the specified price or better
- **Buy Orders**: Purchase assets using CASH
- **Sell Orders**: Sell assets for CASH

### 4. **Order Matching**
- Automatic matching engine processes orders in real-time
- Price-time priority: earlier orders at the same price execute first
- Market orders have highest priority
- Partial fills supported for large orders

### 5. **Trading Dashboard**
- View all orders (pending, filled, cancelled)
- Monitor order book (bids and asks) for each asset
- Track executed trades in real-time
- View current allocations for all participants

## Architecture Changes

### New Domain Models

**`Order`** (`backend/app/domain/types.py`)
```python
class Order:
    order_id: str
    session_id: str
    participant_id: str
    asset: str
    side: OrderSide  # buy or sell
    order_type: OrderType  # market or limit
    quantity: float
    price: Optional[float]  # None for market orders
    filled_quantity: float
    status: OrderStatus  # pending, partial, filled, cancelled
```

**Order Status Flow:**
- `PENDING` → Order placed, awaiting match
- `PARTIAL` → Partially filled, still active
- `FILLED` → Completely executed
- `CANCELLED` → Manually cancelled by participant

### New Database Tables

**`orders` table:**
- Stores all orders with their current status
- Indexed by `session_id` and `asset` for fast order book queries
- Tracks filled quantity for partial fills

### New Services

**`OrderService`** (`backend/app/services/order_service.py`)
- `place_order()`: Submit new market or limit order
- `cancel_order()`: Cancel pending/partial orders
- `get_order_book()`: View bids and asks for an asset
- `get_orders()`: List all orders for a session
- `_match_orders()`: Internal matching engine

**`OrderRepository`** (`backend/app/storage/order_repository.py`)
- Database operations for orders
- Order book generation
- Pending order queries

## API Endpoints

### Place an Order
```http
POST /api/v1/sessions/{session_id}/orders
Content-Type: application/json

{
  "participant_id": "alice",
  "asset": "AAPL",
  "side": "buy",           // "buy" or "sell"
  "order_type": "limit",   // "market" or "limit"
  "quantity": 10.0,
  "price": 150.50          // Required for limit orders, omit for market
}
```

**Response:**
```json
{
  "order_id": "uuid-here",
  "session_id": "demo",
  "participant_id": "alice",
  "asset": "AAPL",
  "side": "buy",
  "order_type": "limit",
  "quantity": 10.0,
  "price": 150.50,
  "filled_quantity": 0.0,
  "status": "pending",
  "created_at": "2025-12-13T14:20:00",
  "updated_at": "2025-12-13T14:20:00"
}
```

### Get All Orders
```http
GET /api/v1/sessions/{session_id}/orders
```

### Get Order Book
```http
GET /api/v1/sessions/{session_id}/orderbook/{asset}
```

**Response:**
```json
{
  "asset": "AAPL",
  "bids": [
    {
      "order_id": "uuid-1",
      "participant_id": "alice",
      "price": 150.50,
      "quantity": 10.0,
      "order_type": "limit"
    }
  ],
  "asks": [
    {
      "order_id": "uuid-2",
      "participant_id": "bob",
      "price": 151.00,
      "quantity": 5.0,
      "order_type": "limit"
    }
  ]
}
```

### Cancel an Order
```http
DELETE /api/v1/orders/{order_id}
```

## Example Workflow

### 1. Create a Session
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "trading_demo",
    "legs": ["AAPL", "NVDA", "META", "ORCL", "CASH"],
    "q": [100, 60, 80, 120, 100000],
    "start_mode": "manual",
    "end_mode": "manual"
  }'
```

### 2. Add Participants with Initial Holdings
```bash
# Add Alice
curl -X POST http://localhost:8000/api/v1/sessions/trading_demo/participants \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "alice",
    "name": "Alice"
  }'

# Add Bob
curl -X POST http://localhost:8000/api/v1/sessions/trading_demo/participants \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "bob",
    "name": "Bob"
  }'
```

### 3. Assign Initial Allocations
```bash
curl -X POST http://localhost:8000/api/v1/sessions/trading_demo/allocations \
  -H "Content-Type: application/json" \
  -d '{
    "allocations": {
      "alice": {
        "AAPL": 50,
        "NVDA": 30,
        "META": 40,
        "ORCL": 60,
        "CASH": 50000
      },
      "bob": {
        "AAPL": 50,
        "NVDA": 30,
        "META": 40,
        "ORCL": 60,
        "CASH": 50000
      }
    }
  }'
```

### 4. Start the Session
```bash
curl -X POST http://localhost:8000/api/v1/sessions/trading_demo/start
```

### 5. Place Orders

**Alice places a limit buy order for AAPL:**
```bash
curl -X POST http://localhost:8000/api/v1/sessions/trading_demo/orders \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "alice",
    "asset": "AAPL",
    "side": "buy",
    "order_type": "limit",
    "quantity": 10,
    "price": 150.00
  }'
```

**Bob places a limit sell order for AAPL:**
```bash
curl -X POST http://localhost:8000/api/v1/sessions/trading_demo/orders \
  -H "Content-Type": application/json" \
  -d '{
    "participant_id": "bob",
    "asset": "AAPL",
    "side": "sell",
    "order_type": "limit",
    "quantity": 10,
    "price": 150.00
  }'
```

**Orders will automatically match!** Alice buys 10 AAPL from Bob at $150.

### 6. Place a Market Order

**Alice places a market buy order (executes at best available price):**
```bash
curl -X POST http://localhost:8000/api/v1/sessions/trading_demo/orders \
  -H "Content-Type: application/json" \
  -d '{
    "participant_id": "alice",
    "asset": "NVDA",
    "side": "buy",
    "order_type": "market",
    "quantity": 5
  }'
```

### 7. View Order Book
```bash
curl http://localhost:8000/api/v1/sessions/trading_demo/orderbook/AAPL
```

### 8. View All Trades
The existing `/api/v1/sessions/{session_id}/allocations` endpoint shows current holdings after trades.

### 9. Settle the Session
```bash
curl -X POST http://localhost:8000/api/v1/sessions/trading_demo/settle
```

## Matching Engine Logic

The order matching engine follows these rules:

1. **Order Priority:**
   - Market orders execute first
   - Limit orders sorted by price (best price first)
   - Same price: time priority (earlier orders first)

2. **Buy Order Matching:**
   - Matches with the lowest-priced sell order
   - Buy limit price must be >= sell limit price
   - Market buy matches any sell order

3. **Sell Order Matching:**
   - Matches with the highest-priced buy order
   - Sell limit price must be <= buy limit price
   - Market sell matches any buy order

4. **Trade Execution:**
   - Trade price determined by limit order (price-time priority)
   - Buyer's CASH decreases by `quantity * price`
   - Seller's CASH increases by `quantity * price`
   - Asset holdings updated accordingly
   - Partial fills supported

5. **Validation:**
   - Buyers must have sufficient CASH
   - Sellers must have sufficient asset holdings
   - All trades maintain conservation of assets

## Event Sourcing

New event types added:
- `ORDER_PLACED`: When an order is submitted
- `ORDER_CANCELLED`: When an order is cancelled
- `ORDER_MATCHED`: When orders execute (replaces TRADE_EXECUTED for order-based trades)

## Next Steps

### Frontend Integration (Recommended)
1. Create order placement form with:
   - Asset selector
   - Buy/Sell toggle
   - Market/Limit selector
   - Quantity input
   - Price input (for limit orders)

2. Display order book with:
   - Real-time bids (buy orders)
   - Real-time asks (sell orders)
   - Current spread

3. Show trade history:
   - Executed trades
   - Price and quantity
   - Timestamp

4. Participant dashboard:
   - Current holdings
   - Pending orders
   - Order history

### Additional Features (Optional)
- Order expiration times
- Stop-loss orders
- Good-till-cancel (GTC) orders
- Order modification (instead of cancel + replace)
- Trade notifications via WebSocket
- Price charts and market depth visualization

## Migration from RFQ System

The RFQ system (`/rfq`, `/quote`) is still available for backward compatibility, but new applications should use the order system (`/orders`, `/orderbook`) for better user experience and more flexible trading.

Key differences:
- **RFQ**: Participant A requests quote, Participant B responds, A accepts → trade
- **Orders**: Participants place orders, system automatically matches → trades

## Testing

The system is ready to test! Use the API endpoints above or visit:
- API Documentation: http://localhost:8000/docs
- Interactive API: http://localhost:8000/redoc

## Summary

This refactoring enables:
- ✅ Session initialization with customizable assets
- ✅ Participant-specific initial holdings
- ✅ Market and limit order trading
- ✅ Automatic order matching
- ✅ Real-time order book monitoring
- ✅ Complete trade history
- ✅ Dashboard-ready data endpoints

The system is now ready for traditional trading workflows while maintaining all the safety invariants and event sourcing capabilities of the original architecture!
