#!/bin/bash

# Move to the workspace directory
cd "$(dirname "$0")"
WORKSPACE_DIR=$(pwd)

echo "Starting Apollo BAS Demo..."

# Tell macOS Terminal to open a new window/tab and start the frontend
osascript -e 'tell app "Terminal" to do script "cd '\'''$WORKSPACE_DIR'/bas-apg-frontend'\'' && npm run dev"'

# Start the backend in the current window
echo "Starting AI Backend Engine..."
cd bas-apg-backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
