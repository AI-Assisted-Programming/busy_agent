#!/bin/bash
if [ -f busy_agent.pid ]; then
    PID=$(cat busy_agent.pid)
    echo "Stopping Busy Agent (PID $PID)..."
    kill $PID
    rm busy_agent.pid
    echo "Busy Agent stopped."
else
    echo "busy_agent.pid not found. Is the agent running?"
    # Fallback: try to find the process by name
    PIDS=$(pgrep -f "python3 busy_agent.py")
    if [ -n "$PIDS" ]; then
        echo "Found processes with pgrep: $PIDS. Killing..."
        kill $PIDS
        echo "Done."
    fi
fi
