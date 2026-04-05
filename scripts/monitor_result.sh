#!/bin/bash

# Force load permanent environment variables for non-interactive shells
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Load global variables from common environment file or standard paths
# These should be exported in the shell before calling these scripts.
# BOT_TOKEN="<REDACTED>"
# CHAT_ID="1347554961"

RESULT_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/last_result.json"
SCREENSHOT="/data/data/com.termux/files/home/storage/shared/android_agent/last_screenshot.png"
LOG_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/monitor.log"

echo "[$(date)] Result monitor started" >> "$LOG_FILE"

while true; do
  if [ -f "$RESULT_FILE" ]; then
    MTIME=$(stat -c %Y "$RESULT_FILE")
    NOW=$(date +%s)
    if [ $((NOW - MTIME)) -lt 60 ]; then
      sleep 4
      GOAL=$(python3 - <<PYEOF
import json
try:
    d = json.load(open("$RESULT_FILE"))
    print(d.get("goal", ""))
except:
    pass
PYEOF
)
      SUCCESS=$(python3 - <<PYEOF
import json
try:
    d = json.load(open("$RESULT_FILE"))
    print("✅" if d["success"] else "❌")
except:
    pass
PYEOF
)
      SUMMARY=$(python3 - <<PYEOF
import json
try:
    d = json.load(open("$RESULT_FILE"))
    print(d.get("summary", "") + "\nSteps: " + str(d.get("steps", "?")))
except:
    pass
PYEOF
)
      
      echo "[$(date)] Task completed: $GOAL" >> "$LOG_FILE"
      
      curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        --data-urlencode "text=${SUCCESS} Task done: ${GOAL}
${SUMMARY}"
      curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
        -F "chat_id=${CHAT_ID}" \
        -F "document=@${SCREENSHOT}"
      break
    fi
  fi
  sleep 15
done
