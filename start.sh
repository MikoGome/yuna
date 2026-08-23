#!/bin/bash

# Track background processes
NODE_PID=""
PYTHON_PID=""

# Cleanup function to kill all active services
cleanup() {
  echo ""
  echo "Stopping all services..."
  
  if [ -n "$NODE_PID" ] && kill -0 "$NODE_PID" 2>/dev/null; then
    kill "$NODE_PID" 2>/dev/null
  fi
  
  if [ -n "$PYTHON_PID" ] && kill -0 "$PYTHON_PID" 2>/dev/null; then
    kill "$PYTHON_PID" 2>/dev/null
  fi

  # Fallback to kill any child processes tied to this script's process group
  pkill -P $$ 2>/dev/null
  
  echo "All services stopped."
  exit 0
}

# Trap Ctrl+C (INT) and termination (TERM) signals
trap cleanup INT TERM

# 1. Start the Node.js server in the background
(node vrm/server.js 2>&1 | sed 's/^/[Node] /') &
NODE_PID=$!

# Wait a couple of seconds for the Node server to spin up
sleep 2

# 2. Locate and activate the virtual environment
if [ -d "env" ]; then
  source env/bin/activate
elif [ -d ".venv" ]; then
  source .venv/bin/activate
else
  echo "Error: Virtual environment directory 'env' or '.venv' not found!"
  cleanup
  exit 1
fi

# Run Python in the foreground and track its PID
(python3 main.py 2>&1 | sed 's/^/[Python] /') &
PYTHON_PID=$!

# Wait for the foreground python process to finish or get interrupted
wait "$PYTHON_PID"

# Run cleanup on normal exit
cleanup
