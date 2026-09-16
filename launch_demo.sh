#!/bin/bash
# Source profile so we have access to node and npm
if [ -f ~/.zshrc ]; then source ~/.zshrc 2>/dev/null; fi
if [ -f ~/.bash_profile ]; then source ~/.bash_profile 2>/dev/null; fi
export PATH=$PATH:/opt/homebrew/bin:/usr/local/bin
cd "$(dirname "$0")"

PYTHON="/Users/atulharshvardhan/miniconda3/envs/bas_apg_env/bin/python"
echo "🚀 IGNITING CYBER-PHYSICAL PIPELINE..."
echo "   Using Python: $($PYTHON --version)"

# Nuke ghost ports
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
sleep 1

echo "-> Starting Edge Physics Engine (Port 8000)"
(cd bas-apg-backend && PYTHONPATH=. $PYTHON scripts/watchdog_runner.py) &
BACKEND_PID=$!

echo "-> Starting React Glass UI (Port 5173)"
(cd bas-apg-frontend && npm run dev) &
FRONTEND_PID=$!

echo "-> Waiting for WebSockets to stabilize..."
sleep 4
open http://localhost:5173/setup

echo "✅ SYSTEM ONLINE. (Press CTRL+C here to safely shutdown both servers)"
wait
