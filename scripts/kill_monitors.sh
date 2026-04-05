#!/bin/bash

# Utility to cleanup any existing progress monitor and clear state
PID_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/progress.pid"
STEP_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/last_step.json"
RESULT_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/last_result.json"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "Stopping existing progress monitor (PID: $PID)..."
    kill "$PID" 2>/dev/null
    rm -f "$PID_FILE"
else
    echo "No existing progress monitor found."
fi

# Clear last state files so the next run starts fresh
echo "Clearing old state files..."
rm -f "$STEP_FILE"
rm -f "$RESULT_FILE"
# Optional: Clear the log file if you want it fresh per-session
# > /data/data/com.termux/files/home/storage/shared/android_agent/monitor.log

echo "Ready for fresh run."
