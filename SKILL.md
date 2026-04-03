---
name: android-automation-agent
description: Use android-automation-agent to run precise Android UI automation tasks via ADB and LLM vision on the same Termux device.
metadata:
  { "clawdbot": { "emoji": "📱", "requires": { "bins": ["adb", "python3"] } } }
---

# android-automation-agent

Automates real Android UI via ADB + LLM vision. One goal string in, one JSON result out.

Quick start

- `cd ~/android-automation-agent && python run.py "Open Settings" --json`
- `cd ~/android-automation-agent && python run.py "Open Blinkit, add milk to cart" --steps 30 --json`
- `cd ~/android-automation-agent && python run.py --check`

---

Run pattern — Background Run & Auto-Notify
ALWAYS follow this flow. Never deviate.

Step 1 — Start the result monitor FIRST (before running the agent):

```
exec yieldMs=500 command='BOT_TOKEN="YOUR_BOT_TOKEN"
CHAT_ID="YOUR_CHAT_ID"
RESULT_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/last_result.json"
SCREENSHOT="/data/data/com.termux/files/home/storage/shared/android_agent/last_screenshot.png"
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
done'
```

Step 1b — Start the progress reporter (runs independently, never stops):

```
exec yieldMs=500 command='BOT_TOKEN="YOUR_BOT_TOKEN"
CHAT_ID="YOUR_CHAT_ID"
STEP_FILE="/data/data/com.termux/files/home/storage/shared/android_agent/last_step.json"
while true; do
  sleep 15
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
      curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        --data-urlencode "text=⏳ ${STEP}"
    fi
  fi
done'
```

Step 2 — Tell the user and run the agent:

Tell user: "Monitor started, running your task now..."

```
cd ~/android-automation-agent && python run.py '<GOAL>' --steps <N> --json
```

Then immediately send this Telegram message (before ending your turn):

```
curl -s -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/sendMessage" \
  -d "chat_id=YOUR_CHAT_ID" \
  --data-urlencode "text=🤖 Agent started: <exact goal string>"
```

Step 3 — End your turn. The monitor delivers the result + screenshot automatically.

---

Hard rules

- Never use sessions_yield — models ignore it.
- Never use background=true + notifyOnExit — heartbeats fire into dead sessions.
- Never promise "I'll notify you" without the monitor already running.
- Always run the screen unlock script before the agent.

---

Check current screen (anytime)
When user asks "what's on screen?", "what's happening?", or "show me the phone":

```
adb exec-out screencap -p > /tmp/screen.png
curl -s -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/sendDocument" \
  -F "chat_id=YOUR_CHAT_ID" \
  -F "document=@/tmp/screen.png"
```

Then analyze what's visible and report. Always take a fresh screencap — `last_screenshot.png` may be from a previous run.

---

Goal string format
The agent navigates and taps only. It cannot read text, extract values, or return data.
Translate user intent into navigation-only goals.

For info requests ("what's the price", "what's the fare", "is X available"):
- End the goal at the target screen
- Never include "show me", "tell me", "read", "confirm", or "return"
- Bad:  "Tell me the Uber fare to Indiranagar"
- Good: "Open Uber, set destination to Indiranagar, wait for ride options to load"
- The screenshot IS the answer — read it visually and report

For action requests ("add to cart", "book ride", "search for X"):
- Be precise: exact item name, exact app, all steps
- Bad:  "buy me milk"
- Good: "Open Blinkit, search for Nandini toned milk 500ml, tap first result, tap Add to cart"

Use the user's exact words — never paraphrase, rename, or interpret.
- If user says "bike ride" → goal says "bike ride", not "Uber Moto"
- If user says "the red button" → goal says "the red button"
- Only add mechanical prerequisites the user skipped (e.g. "open the app first")
- The agent reads the screen pixel by pixel — over-translating causes failures

Context-aware goals (when user references a prior run):
If user says "now order it", "complete checkout", "confirm it" — before building the goal:
1. Read `last_result.json` to confirm what the previous task did and whether it succeeded
2. Embed that context explicitly in the goal string — the agent has no memory
- Wrong: "order greek yogurt"
- Right:  "Greek yogurt is already in the Instamart cart. Open Instamart, go to cart, complete checkout."

If ambiguous, ask before constructing the goal.

---

Task decomposition

- Break complex workflows into sequential atomic runs — verify each succeeded before starting the next.

Notes

- Simple tasks: 30–120s. Complex tasks: up to 10 minutes.
- Use `--steps 40+` for multi-screen flows or checkout.
- On `success: false`, check the Telegram message the monitor sent for summary and screenshot.
- Never auto-retry a checkout run — verify manually first.
