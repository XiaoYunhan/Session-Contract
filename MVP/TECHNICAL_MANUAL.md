# Session Contracts MVP - Technical Manual

## 1. System Overview

The Session Contracts system supports a traditional **order-based trading model** with market and limit orders. This system allows investors to trade assets intuitively during active sessions, backed by a ring-fenced collateral pool on a fixed basket of legs.

### Core Architecture
- **Backend:** FastAPI (Python) - Manages sessions, orders, and matching.
- **Frontend:** React (Vite) - Professional "Bloomberg-style" terminal interface.
- **Oracle:** Python - Streams simulated or replayed prices.
- **Database:** SQLite - ZERO setup, single file.
- **Realtime:** WebSocket - Pushes prices, trades, and allocation updates.

---

## 2. Getting Started

### Prerequisites
- Docker (Recommended)
- OR Python 3.9+ and Node.js 16+ (for manual setup)

### Running with Docker (Recommended)

1. **Start Services**
   ```bash
   cd MVP
   docker compose up -d --build
   ```

2. **Create a Demo Session**
   ```bash
   curl -X POST http://localhost:8000/api/v1/sessions \
     -H "Content-Type: application/json" \
     -d '{
       "session_id":"demo",
       "legs":["AAPL","NVDA","META","ORCL"],
       "q":[100,60,80,120],
       "start_mode":"immediate",
       "end_mode":"manual"
     }'
   ```

3. **Start Price Oracle**
   ```bash
   docker compose --profile oracle up -d
   ```

4. **Access**
   - Frontend: http://localhost:5173
   - API Docs: http://localhost:8000/docs

### Running Manually (Without Docker)

If you prefer to run services individually (equivalent to the old `start-demo.sh` script):

1. **Backend** (Term 1)
   ```bash
   cd MVP/backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Oracle** (Term 2)
   ```bash
   cd MVP/oracle
   python3 -m venv .venv
   source .venv/bin/activate
   pip install httpx
   # Sim Mode (Random Walk)
   python oracle.py --mode sim --session-id demo --tick-ms 1000
   ```
   *Note: Ensure a session exists before starting the oracle (see API call above).*

3. **Frontend** (Term 3)
   ```bash
   cd MVP/frontend
   npm install
   npm run dev -- --port 5173
   ```

### Stopping Services
To stop manually running services:
```bash
pkill -f "uvicorn app.main:app"
pkill -f "oracle.py"
pkill -f "vite"
```

---

## 3. Features & Functionality

### Order Trading System
- **Order Types:**
  - **Market Orders:** Execute immediately at best available price.
  - **Limit Orders:** Execute at specified price or better.
- **Matching Engine:**
  - **Price-Time Priority:** Better prices first; then earlier orders.
  - **Partial Fills:** Large orders can be filled in chunks.
  - **Validation:** Enforces cash availability (Buy) and asset holdings (Sell).

### Session Management
- **Creation:** Define assets (`legs`) and basket quantities (`q`).
- **Custom Allocations:** 
  - Assign specific initial holdings to participants at creation.
  - Or use default equal pro-rata distribution.
- **Deletion:** Full session deletion supported from the Dashboard.

### User Interface (Terminal Design)
The UI features a **Professional Financial Terminal** aesthetic:
- **Dark Theme:** `#0a0e14` background with trading colors (Green/Red/Blue).
- **Typography:** Monospace (Roboto Mono) for data precision.
- **Data Display:** Ticker-style price cards and real-time order books.
- **Live Updates:** WebSocket integration means **no manual refresh** is needed. Prices and allocations update automatically.

---

## 4. API Reference

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sessions` | Create a new session |
| `DELETE`| `/sessions/{id}` | Delete a session |
| `POST` | `/sessions/{id}/orders` | Place a market/limit order |
| `GET` | `/sessions/{id}/orders` | List all orders |
| `GET` | `/sessions/{id}/orderbook/{asset}` | Get Bids/Asks |
| `POST` | `/sessions/{id}/settle` | Settle session at maturity |

### Example: Place Order
```http
POST /api/v1/sessions/demo/orders
{
  "participant_id": "alice",
  "asset": "AAPL",
  "side": "buy",
  "order_type": "limit",
  "quantity": 10,
  "price": 150.00
}
```

---

## 5. Event Sourcing & Invariants
The system maintains strict invariants for correctness:
1. **Conservation:** Total assets in the pool must remain constant (`Σ x_i = q`).
2. **No Internal Shorting:** Participants cannot hold negative assets (unless explicitly allowed, currently MVP enforces >= 0).
3. **Auditability:** Every state change (Trade, Order, Allocation) is recorded as an immutable event.
