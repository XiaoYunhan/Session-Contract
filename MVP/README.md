# Session Contracts — Local Prototype (Multi-Asset Allocation Market)

A lightweight, **fully local** demo system to validate the core mechanics of **Session Contracts**: a ring-fenced collateral pool on a fixed basket of legs, where participants trade **reallocations of claims** (relative value) and settle against a **predefined price source** at maturity.

This is **not** an exchange, not custody, not production trading infrastructure. It's a verification and demo harness: conservation, no-unfunded positions, deterministic settlement, auditable state transitions.

---

## ⚡ Quick Start (ONE COMMAND!)

```bash
cd MVP
./start-demo.sh
```

This will:
1. Start the backend API server (port 8000)
2. Create a demo session with AAPL, NVDA, META, ORCL
3. Start the price oracle streaming live prices
4. Launch the frontend UI (port 5173)
5. Open your browser automatically

**Access:**
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

**Stop everything:**
```bash
./stop-demo.sh
```

**Alternative - Docker:**
```bash
# Start backend + frontend
docker compose up -d --build

# Create session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo","legs":["AAPL","NVDA","META","ORCL"],"q":[100,60,80,120],"start_mode":"immediate","end_mode":"manual"}'

# Start oracle
docker compose --profile oracle up -d
```

**Run Tests:**
```bash
cd backend
source .venv/bin/activate
pytest app/tests/ -v
# Result: 18 passed in 0.27s ✅
```

---

## What this prototype demonstrates (MVP)

- **Multi-asset sessions** (e.g., `{AAPL, NVDA, META, ORCL}` or curve legs like `{GOLD 3m, 1y, 5y}` in “unitized” form)
- **Closed pool** with fixed basket vector `q` and conservation: `Σ_i x_i(t) = q`
- **Reallocation-only trading** via **RFQ/quote swaps** between two legs (fast, robust, simple)
- **Deterministic settlement** at `t2` using an oracle-provided `S_t2`
- **Event-sourced ledger** (append-only events log) + derived “current allocations” projection
- **Local price oracle**:
  - `sim` mode (correlated random walk)
  - `replay` mode (CSV replay)

---

## Tech stack (local-first)

- **Backend**: FastAPI (Python)
- **DB**: SQLite (default; single file, zero setup)
- **Realtime**: WebSocket (push allocations/trades/oracle ticks)
- **Frontend**: React (Vite) or Next.js (choose one; Vite is lighter)
- **Oracle**: Python process that streams prices to backend
- **One-command local**: `docker compose up` (optional but recommended)

> You can run everything **without Docker** too.

---

## Repo layout

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry
│   │   ├── domain/                 # core types + invariants
│   │   ├── services/               # session, trading, settlement
│   │   ├── storage/                # sqlite repo + event store
│   │   ├── api/                    # REST + WS routes
│   │   └── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/                  # Dashboard / Portfolio / Trading
│   │   └── lib/                    # API client, ws client
│   ├── package.json
│   └── .env.example
├── oracle/
│   ├── oracle.py                   # sim/replay publisher
│   ├── configs/
│   └── data/
│       └── prices_demo.csv         # optional replay file
├── docker-compose.yml              # optional one-command local
└── README.md
````

---

## Quickstart (Docker, easiest)

### 1) Requirements

* Docker + Docker Compose

### 2) Run

```bash
docker compose up --build
```

### 3) Open

* Frontend: [http://localhost:5173](http://localhost:5173)
* Backend API: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)

---

## Quickstart (No Docker)

### 1) Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 2) Oracle (in a second terminal)

```bash
cd oracle
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # if you keep one, or use a minimal requirements file
python oracle.py --mode sim --session-id demo
# or: python oracle.py --mode replay --csv data/prices_demo.csv --session-id demo
```

### 3) Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev -- --port 5173
```

---

## Demo: multi-asset session scenario (suggested flow)

### Step 0 — Create a session

Create a session with:

* legs: `["AAPL","NVDA","META","ORCL"]`
* basket `q`: e.g. `[100, 60, 80, 120]` (units/shares)
* `t1` / `t2`: e.g. 10 minutes duration (or manual settle for demos)

You can create sessions from the UI (preferred) or via API:

```bash
curl -X POST http://localhost:8000/sessions \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id":"demo",
    "legs":["AAPL","NVDA","META","ORCL"],
    "q":[100,60,80,120],
    "start_mode":"immediate",
    "end_mode":"manual"
  }'
```

### Step 1 — Add participants + initial allocations

For a clean demo:

* 1 organiser (admin)
* 2–3 traders
* 1 market maker (optional)

Initial allocations can be equal-pro-rata (default) or custom.

### Step 2 — Start oracle stream

* `sim` mode generates plausible relative moves
* `replay` mode uses a CSV so the demo is deterministic

### Step 3 — Trade reallocations using RFQ swaps

Example: trader requests swap **10 AAPL** into **NVDA**.
A maker quotes `rate = 0.62` meaning:

* trader gives `10 AAPL` and receives `6.2 NVDA`
* maker receives `10 AAPL` and gives `6.2 NVDA`

All trades are checked to ensure:

* allocations stay non-negative (MVP rule)
* conservation holds

### Step 4 — Settle at maturity

Backend records `S_t2` and computes cash payouts:

* `payout_i = x_i(t2) · S_t2`
  and verifies:
* `Σ payouts = q · S_t2`

---

## Oracle modes

### `sim` (default)

* Generates correlated prices for each leg
* Useful for stress-testing “relative” dynamics quickly

Run:

```bash
python oracle.py --mode sim --session-id demo --tick-ms 500
```

### `replay` (deterministic demo)

CSV format example:

```csv
ts,AAPL,NVDA,META,ORCL
2025-12-13T10:00:00,190.1,480.2,350.0,104.3
2025-12-13T10:00:01,190.2,481.0,349.8,104.4
...
```

Run:

```bash
python oracle.py --mode replay --csv data/prices_demo.csv --session-id demo --tick-ms 250
```

---

## Core invariants (what we validate on every trade)

1. **Conservation**

* For each leg `k`: `Σ_i x[i][k] == q[k]` (within tolerance)

2. **No internal shorting (MVP)**

* For all `i,k`: `x[i][k] >= 0`

3. **Reallocation-only**

* Every executed trade has `Δx_maker + Δx_taker = 0` (vector)

4. **Settlement sum**

* `Σ_i payout_i = q · S_t2`

If any invariant fails:

* trade is rejected
* event log is still consistent (no partial writes)

---

## API overview (minimal)

* `POST /sessions` create session
* `POST /sessions/{id}/participants` join
* `GET /sessions/{id}` session status + legs + q
* `GET /sessions/{id}/allocations` current allocations
* `POST /sessions/{id}/rfq` create RFQ
* `POST /rfq/{rfq_id}/quote` submit quote
* `POST /quotes/{quote_id}/accept` execute trade
* `POST /sessions/{id}/settle` settle (manual or timed)

Realtime:

* `WS /ws/sessions/{id}` pushes ticks, trades, allocations, status

OpenAPI docs:

* [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Event sourcing (auditability)

The backend writes **every state transition** as an append-only event:

* `SessionCreated`
* `ParticipantJoined`
* `InitialAllocationAssigned`
* `RFQRequested`
* `QuoteProvided`
* `TradeExecuted`
* `SessionSettled`

The “current allocations” view is a projection derived from events.

Why:

* deterministic replay for debugging
* easy verification of conservation + trade correctness
* clean path to more complex market mechanisms later (auction / order book)

---

## Configuration

Backend (`backend/.env`):

```env
DATABASE_URL=sqlite:///./session_contracts.db
ALLOW_MANUAL_SETTLE=true
INVARIANT_TOLERANCE=1e-9
```

Frontend (`frontend/.env`):

```env
VITE_API_BASE=http://localhost:8000
VITE_WS_BASE=ws://localhost:8000
```

Oracle args control mode/tick speed.

---

## Tests

Backend unit tests focus on:

* trade execution math
* invariant enforcement
* settlement calculations
* event replay determinism

Run:

```bash
cd backend
pytest -q
```

---

## Troubleshooting

* **Port in use**:

  * frontend default: `5173`
  * backend default: `8000`
    Change ports in your run commands or docker compose.

* **No prices in UI**:

  * ensure oracle is running and session id matches
  * check WS connection in browser devtools

* **Trade rejected**:

  * most common: insufficient inventory under no-shorting rule
  * check allocations panel and quoted amount/rate

---

## Roadmap (optional next steps)

* Batch auction every N seconds (improves fairness + reduces spam)
* Allow bounded shorting with internal margin (still fully funded)
* More explicit corporate-action handling (for equity realism)
* Pluggable fixing window design (VWAP / close / composite)
* Basic market surveillance signals (wash-trade heuristics, quote stuffing)

---

## Disclaimer

This project is for **research and demonstration** only.
No custody, no KYC/AML, no regulatory compliance, no live trading.
Not financial advice.
