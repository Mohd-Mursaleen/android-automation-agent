#!/bin/bash

# Force load permanent environment variables for non-interactive shells
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Live progress monitor for android-automation agent
# Depends on BOT_TOKEN and CHAT_ID being exported

STEP_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/last_step.json"
RESULT_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/last_result.json"
PID_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/progress.pid"
LOG_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/monitor.log"

echo $$ > "$PID_FILE"
echo "[$(date)] Progress monitor started (PID: $$)" >> "$LOG_FILE"

while true; do
  sleep 15
  # Exit if result file is fresh (task ended)
  if [ -f "$RESULT_FILE" ]; then
    MTIME=$(stat -c %Y "$RESULT_FILE")
    NOW=$(date +%s)
    if [ $((NOW - MTIME)) -lt 90 ]; then
      echo "[$(date)] Result file updated, stopping progress monitor." >> "$LOG_FILE"
      break
    fi
  fi

  if [ -f "$STEP_FILE" ]; then
    STEP=$(python3 - <<PYEOF
import json
try:
    d = json.load(open("$STEP_FILE"))
    print("Step " + str(d["step"]) + " - " + str(d["last_action"]) + " (" + str(d["elapsed_seconds"]) + "s elapsed)")
except:
    pass
PYEOF
)
    if [ -n "$STEP" ]; then
      echo "[$(date)] Sending update: $STEP" >> "$LOG_FILE"
      curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        --data-urlencode "text=⏳ ${STEP}"
    fi
  fi
done

rm -f "$PID_FILE"
