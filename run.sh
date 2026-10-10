#!/bin/bash
echo "Starting Busy Agent..."
python3 busy_agent.py > agent.log 2>&1 &
echo $! > busy_agent.pid
echo "Busy Agent started with PID $(cat busy_agent.pid)"
