#!/bin/bash
echo "🚀 Launching Punisher Mission Control..."

# Ensure we are in the root
cd "$(dirname "$0")"

# Check if backend is running
if ! pgrep -f "punisher-server" > /dev/null; then
    echo "Starting Backend..."
    uv run punisher-server > backend.log 2>&1 &
    PID_BACKEND=$!
    echo "Backend PID: $PID_BACKEND"
else
    echo "Backend already running."
fi

# Start Web UI
echo "Starting Frontend..."
cd punisher-web
bun run dev --host

# Cleanup on exit
trap "kill $PID_BACKEND" EXIT
