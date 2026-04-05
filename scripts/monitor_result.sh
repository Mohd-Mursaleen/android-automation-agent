#!/bin/bash

# Force load environment variables
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

RESULT_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/last_result.json"
SCREENSHOT="/data/data/com.termux/files/home/storage/shared/android_agent/last_screenshot.png"
LOG_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/monitor.log"
PID_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/result.pid"

# Kill any previous result monitor instance
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if [ "$OLD_PID" != "$$" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[$(date)] Killing old result monitor (PID: $OLD_PID)" >> "$LOG_FILE"
        kill "$OLD_PID" 2>/dev/null
        sleep 1
    fi
fi

# Register our PID
echo $$ > "$PID_FILE"
echo "[$(date)] Result monitor started (PID: $$)" >> "$LOG_FILE"

while true; do
    if [ -f "$RESULT_FILE" ]; then
        MTIME=$(stat -c %Y "$RESULT_FILE")
        NOW=$(date +%s)
        if [ $((NOW - MTIME)) -lt 60 ]; then
            sleep 4
            GOAL=$(python3 -c "
import json
try:
    d = json.load(open('$RESULT_FILE'))
    print(d.get('goal', ''))
except:
    pass
" 2>/dev/null)
            SUCCESS=$(python3 -c "
import json
try:
    d = json.load(open('$RESULT_FILE'))
    print('✅' if d['success'] else '❌')
except:
    pass
" 2>/dev/null)
            SUMMARY=$(python3 -c "
import json
try:
    d = json.load(open('$RESULT_FILE'))
    print(d.get('summary', '') + '\nSteps: ' + str(d.get('steps', '?')))
except:
    pass
" 2>/dev/null)

            echo "[$(date)] Task completed: $GOAL" >> "$LOG_FILE"

            curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
                -d "chat_id=${CHAT_ID}" \
                --data-urlencode "text=${SUCCESS} Task done: ${GOAL}
${SUMMARY}"

            if [ -f "$SCREENSHOT" ]; then
                curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
                    -F "chat_id=${CHAT_ID}" \
                    -F "document=@${SCREENSHOT}"
            fi

            break
        fi
    fi
    sleep 15
done

# Cleanup our PID file
rm -f "$PID_FILE"
echo "[$(date)] Result monitor exited (PID: $$)" >> "$LOG_FILE"
