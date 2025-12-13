#!/bin/bash
# Stop all Session Contracts services

echo "🛑 Stopping Session Contracts services..."

# Kill by process name
pkill -f "uvicorn app.main:app" 2>/dev/null && echo "✓ Backend stopped"
pkill -f "oracle.py" 2>/dev/null && echo "✓ Oracle stopped"
pkill -f "vite" 2>/dev/null && echo "✓ Frontend stopped"

# Clean up log files
rm -f /tmp/backend.log /tmp/oracle.log /tmp/frontend.log 2>/dev/null && echo "✓ Logs cleaned"

echo ""
echo "✅ All services stopped!"
