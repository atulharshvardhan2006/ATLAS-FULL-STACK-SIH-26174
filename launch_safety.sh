#!/bin/bash
if [ -f ~/.zshrc ]; then source ~/.zshrc 2>/dev/null; fi
if [ -f ~/.bash_profile ]; then source ~/.bash_profile 2>/dev/null; fi
export PATH=$PATH:/opt/homebrew/bin:/usr/local/bin

export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
export VECLIB_MAXIMUM_THREADS=2
export NUMEXPR_NUM_THREADS=2

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

# ─── EXCLUSIVE LOCK: Kill ALL A.T.L.A.S processes ───
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
lsof -ti:5174 | xargs kill -9 2>/dev/null
pkill -f "watchdog_runner.py" 2>/dev/null
sleep 1

# Start the backend (shared with main frontend)
(cd bas-apg-backend && PYTHONPATH=. $PYTHON scripts/watchdog_runner.py) &
BACKEND_PID=$!

# Start the Safety Dashboard frontend on port 5174
(cd bas-apg-safety && npm run dev) &
FRONTEND_PID=$!

# Wait for both servers to be fully ready
echo "Waiting for Edge Physics Engine (Port 8000)..."
while ! nc -z localhost 8000; do
  sleep 0.5
done

echo "Waiting for Safety Dashboard (Port 5174)..."
while ! nc -z localhost 5174; do   
  sleep 0.5
done
sleep 1

# Open in a chromeless Chrome window
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --app="http://localhost:5174" > /dev/null 2>&1 &

wait
