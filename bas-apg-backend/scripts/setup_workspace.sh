#!/bin/bash

echo "Prompting user for BACKEND folder..."
BACKEND_DIR=$(osascript -e 'POSIX path of (choose folder with prompt "Select your Python BACKEND folder")' 2>/dev/null)
if [ -z "$BACKEND_DIR" ]; then
    echo "Error: Backend folder selection cancelled."
    exit 1
fi

echo "Prompting user for FRONTEND folder..."
FRONTEND_DIR=$(osascript -e 'POSIX path of (choose folder with prompt "Select your React FRONTEND folder")' 2>/dev/null)
if [ -z "$FRONTEND_DIR" ]; then
    echo "Error: Frontend folder selection cancelled."
    exit 1
fi

# Trim trailing slashes
BACKEND_DIR=$(echo "$BACKEND_DIR" | sed 's/\/$//')
FRONTEND_DIR=$(echo "$FRONTEND_DIR" | sed 's/\/$//')

WORKSPACE_DIR="$HOME/Desktop/BAS-APG-Workspace"
echo "Creating workspace at $WORKSPACE_DIR..."
mkdir -p "$WORKSPACE_DIR"

echo "Moving and renaming folders..."
mv "$BACKEND_DIR" "$WORKSPACE_DIR/bas-apg-backend"
mv "$FRONTEND_DIR" "$WORKSPACE_DIR/bas-apg-frontend"

echo "SUCCESS: Workspace secured at $WORKSPACE_DIR"
