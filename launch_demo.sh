#!/bin/bash
# Source profile so we have access to node and npm
if [ -f ~/.zshrc ]; then source ~/.zshrc 2>/dev/null; fi
if [ -f ~/.bash_profile ]; then source ~/.bash_profile 2>/dev/null; fi
export PATH=$PATH:/opt/homebrew/bin:/usr/local/bin

# ─── THERMAL THROTTLING ───
# Force ML libraries to use fewer cores to keep CPU temps < 90°C
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
export VECLIB_MAXIMUM_THREADS=2
export NUMEXPR_NUM_THREADS=2
# ──────────────────────────

cd "$(dirname "$0")"

# Setup Python Environment
if [ -d "bas-apg-backend/venv" ]; then
    PYTHON="$(pwd)/bas-apg-backend/venv/bin/python"
elif command -v conda &> /dev/null && conda env list | grep -q "bas_apg_env"; then
    eval "$(conda shell.bash hook)"
    conda activate bas_apg_env
    PYTHON="python"
elif [ -d "$HOME/miniconda3/envs/bas_apg_env" ]; then
    eval "$($HOME/miniconda3/bin/conda shell.bash hook)"
    conda activate bas_apg_env
    PYTHON="python"
else
    PYTHON="python3"
fi
echo "🚀 IGNITING CYBER-PHYSICAL PIPELINE..."
echo "   Using Python: $($PYTHON --version)"

# ─── EXCLUSIVE LOCK: Kill ALL A.T.L.A.S processes ───
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
lsof -ti:5174 | xargs kill -9 2>/dev/null
pkill -f "watchdog_runner.py" 2>/dev/null
sleep 1

echo "-> Starting Edge Physics Engine (Port 8000)"
(cd bas-apg-backend && PYTHONPATH=. $PYTHON scripts/watchdog_runner.py) &
BACKEND_PID=$!

echo "-> Starting React Glass UI (Port 5173)"
(cd bas-apg-frontend && npm run dev) &
FRONTEND_PID=$!

# Wait for both servers to be fully ready
echo "Waiting for Edge Physics Engine (Port 8000)..."
while ! nc -z localhost 8000; do
  sleep 0.5
done

echo "Waiting for React Glass UI (Port 5173)..."
while ! nc -z localhost 5173; do   
  sleep 0.5
done
sleep 2

open http://localhost:5173/setup
open http://localhost:5173/station

echo "[SYSTEM ONLINE] Press CTRL+C to shutdown"
wait
