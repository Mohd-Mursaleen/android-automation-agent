---
name: android-automation-agent
description: Use android-automation-agent to run precise Android UI automation tasks via ADB and LLM vision on the same Termux device.
metadata:
  { "clawdbot": { "emoji": "📱", "requires": { "bins": ["adb", "python3"] } } }
---

# android-automation-agent

Automates real Android UI via ADB + LLM vision. One goal string in, one JSON result out.

Quick start

- `cd ~/android-automation-agent && python run.py "Open Settings"`
- `cd ~/android-automation-agent && python run.py "Open Blinkit, add milk to cart" --steps 40`
- `cd ~/android-automation-agent && python run.py --check`

Run pattern — Background Run & Auto-Notify
ALWAYS follow this two-step flow. Never deviate.

Step 1 — Start the monitor loop FIRST (before running the agent):

```
exec yieldMs=500 command='while true; do
  if [ -f ~/storage/shared/android_agent/last_result.json ]; then
    MTIME=$(stat -c %Y ~/storage/shared/android_agent/last_result.json)
    NOW=$(date +%s)
    DIFF=$((NOW - MTIME))
    if [ "$DIFF" -lt 60 ]; then
      sleep 4
      BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
      CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
      CONTENTS=$(cat ~/storage/shared/android_agent/last_result.json)
      curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=${CONTENTS}"
      curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
        -F "chat_id=${CHAT_ID}" \
        -F "document=@/data/data/com.termux/files/home/storage/shared/android_agent/last_screenshot.png"
      break
    fi
  fi
  sleep 30
done'
```

Tell the user: "Monitor started, running your task now..."

Step 2 — Run the automation agent:
`cd ~/android-automation-agent && python run.py '<GOAL>' --steps <N> --json`

Step 3 — Do nothing. The monitor delivers the JSON result + screenshot to Telegram automatically when done. No polling needed. End your turn.

Hard rules

- Never use sessions_yield for automation tasks — models ignore it reliably.
- Never tell the user "I'll notify you when done" unless the monitor loop is already running.
- Never use background=true + notifyOnExit for this — heartbeats fire into dead sessions.
- The full absolute path MUST be used in curl sendDocument — `~/` does not expand inside curl -F flags.

Check current screen (anytime)
When user asks "what's on screen?", "what's happening?", or "show me the phone":

- `adb exec-out screencap -p > /tmp/screen.png`
- `openclaw message send --channel telegram --target <user_id> --media /tmp/screen.png --force-document`
- Analyze what's visible and report it
  Always use a fresh screencap here — `last_screenshot.png` may be from a previous run.

Goal string format
The agent navigates and taps only. It cannot read text, extract values,
or return data. Translate user intent into navigation-only goals.

For info requests ("what's the price", "what's the fare", "is X available"):
End the goal at the target screen. Never include "show me", "tell me",
"read", "confirm", or "return" in the goal string.
Bad: "Tell me the Uber fare to Indiranagar"
Good: "Open Uber, set destination to Indiranagar, wait for ride options to load"
The screenshot IS the answer. Read it visually and report.

For action requests ("add to cart", "book ride", "search for X"):
Be precise. Include exact item name, app, and all steps.
Bad: "buy me milk"
Good: "Open Blinkit, search for Nandini toned milk 500ml, tap first result, tap Add to cart"

If ambiguous, ask before constructing the goal.

Task decomposition

- Break complex workflows into sequential atomic runs — verify each run succeeded before starting the next.

Notes

- Always run screen unlock script before every automation run.
- Simple tasks: 30–120s. Complex tasks: up to 10 minutes.
- Use `--steps 40+` for multi-screen flows or checkout.
- On `success: false`, check the Telegram message the monitor sent for the summary and screenshot.
- Never auto-retry a checkout run — verify manually first.
