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

eval "$(/Users/atulharshvardhan/miniconda3/bin/conda shell.bash hook)"
conda activate bas_apg_env

PYTHON="/Users/atulharshvardhan/miniconda3/envs/bas_apg_env/bin/python"

lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null
pkill -f "watchdog_runner.py" 2>/dev/null
sleep 1

(cd bas-apg-backend && PYTHONPATH=. $PYTHON scripts/watchdog_runner.py) &
BACKEND_PID=$!

(cd bas-apg-frontend && npm run dev) &
FRONTEND_PID=$!

# Wait for both servers to be fully ready
echo "Waiting for Edge Physics Engine (Port 8000)..."
while ! nc -z localhost 8000; do
  sleep 0.5
done

echo "Waiting for frontend server (Port 5173)..."
while ! nc -z localhost 5173; do   
  sleep 0.5
done
sleep 1

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --app="http://localhost:5173/training" > /dev/null 2>&1 &

wait
