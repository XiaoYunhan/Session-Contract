#!/bin/bash
# Complete workflow to start Session Contracts with "demo" session

set -e  # Exit on error

echo "🚀 Starting Session Contracts Demo..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}Step 1:${NC} Starting Backend..."
cd "$SCRIPT_DIR/backend"

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install dependencies if needed
if ! pip show fastapi > /dev/null 2>&1; then
    echo "Installing backend dependencies..."
    pip install -q -r requirements.txt
fi

# Start backend in background
echo "Starting backend on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is healthy${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo "Backend failed to start. Check /tmp/backend.log"
        exit 1
    fi
done

echo ""
echo -e "${BLUE}Step 2:${NC} Creating 'demo' session..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo",
    "legs": ["AAPL", "NVDA", "META", "ORCL"],
    "q": [100, 60, 80, 120],
    "start_mode": "immediate",
    "end_mode": "manual"
  }')

if echo "$RESPONSE" | grep -q "demo"; then
    echo -e "${GREEN}✓ Session 'demo' created successfully${NC}"
    echo "  Legs: AAPL, NVDA, META, ORCL"
    echo "  Basket: [100, 60, 80, 120]"
else
    echo -e "${YELLOW}Session may already exist (this is OK)${NC}"
fi

echo ""
echo -e "${BLUE}Step 3:${NC} Starting Oracle..."
cd "$SCRIPT_DIR/oracle"

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# Install dependencies if needed
if ! pip show httpx > /dev/null 2>&1; then
    echo "Installing oracle dependencies..."
    pip install -q httpx
fi

# Start oracle in background
echo "Starting oracle (sim mode, 1 second intervals)..."
python oracle.py --mode sim --session-id demo --tick-ms 1000 > /tmp/oracle.log 2>&1 &
ORACLE_PID=$!
echo -e "${GREEN}✓ Oracle started (PID: $ORACLE_PID)${NC}"

# Wait a moment for first price tick
sleep 2

# Check if prices are being sent
echo ""
echo -e "${BLUE}Step 4:${NC} Verifying prices..."
PRICES=$(curl -s http://localhost:8000/api/v1/sessions/demo/prices)
if echo "$PRICES" | grep -q "AAPL"; then
    echo -e "${GREEN}✓ Prices are streaming!${NC}"
    echo "$PRICES" | python3 -m json.tool 2>/dev/null || echo "$PRICES"
else
    echo "Prices not yet available, please wait..."
fi

echo ""
echo -e "${BLUE}Step 5:${NC} Starting Frontend..."
cd "$SCRIPT_DIR/frontend"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies (this may take a minute)..."
    npm install
fi

# Start frontend in background
echo "Starting frontend on port 5173..."
npm run dev -- --port 5173 > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}🎉 All services are running!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Access Points:"
echo "   Frontend:     http://localhost:5173"
echo "   Backend API:  http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/health"
echo ""
echo "📊 Session Details:"
echo "   Session ID: demo"
echo "   Legs: AAPL, NVDA, META, ORCL"
echo "   Prices updating every 1 second"
echo ""
echo "📝 Process IDs (for stopping later):"
echo "   Backend: $BACKEND_PID"
echo "   Oracle:  $ORACLE_PID"
echo "   Frontend: $FRONTEND_PID"
echo ""
echo "🛑 To stop all services, run:"
echo "   kill $BACKEND_PID $ORACLE_PID $FRONTEND_PID"
echo "   Or use: pkill -f 'uvicorn|oracle.py|vite'"
echo ""
echo "📋 Logs:"
echo "   Backend:  tail -f /tmp/backend.log"
echo "   Oracle:   tail -f /tmp/oracle.log"
echo "   Frontend: tail -f /tmp/frontend.log"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Opening browser..."
sleep 3
open http://localhost:5173 2>/dev/null || echo "Please manually open: http://localhost:5173"
