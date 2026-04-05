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

Step 1 — Start the monitors FIRST (before running the agent):

Ensure BOT_TOKEN and CHAT_ID are already exported.

```
exec yieldMs=500 command='bash ~/android-automation-agent/scripts/monitor_result.sh'
```

Step 1b — Kill any previous progress loop, then start a new one:

```
bash ~/android-automation-agent/scripts/kill_monitors.sh && \
exec yieldMs=500 command='bash ~/android-automation-agent/scripts/monitor_progress.sh'
```

Step 2 — Tell the user and run the agent:

Tell user: "Task started. Goal: '<goal string used>'. Sending live updates every 15s."

```
bash /data/data/com.termux/files/home/wake_and_unlock.sh && \
cd ~/android-automation-agent && python run.py '<GOAL>' --steps <N> --json
```

Then immediately send this Telegram message (before ending your turn):

```
curl -s -X POST "https://api.telegram.org/bot8761136163:AAFNPOCGsPXzMPoc0uYlwT1yrUSedtE-pKo/sendMessage" \
  -d "chat_id=1347554961" \
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
curl -s -X POST "https://api.telegram.org/bot8761136163:AAFNPOCGsPXzMPoc0uYlwT1yrUSedtE-pKo/sendDocument" \
  -F "chat_id=1347554961" \
  -F "document=@/tmp/screen.png"
```

Then analyze what's visible and report. Always take a fresh screencap — `last_screenshot.png` may be from a previous run.

---

Goal string format

The android agent reads the screen pixel by pixel and finds UI elements
visually. Your job is to pass intent clearly — not to interpret, translate,
or improve the user's words.

Rules (never break these):

1. Never substitute the user's words for what you think the UI says.
   - User says "bike ride" → goal says "bike ride". Not "Uber Moto", not "motorcycle".
   - User says "Instamart" → goal says "Open Instamart". Not "Open Swiggy, go to Instamart".
   - The agent will find the right element on screen. Trust it.

2. Never assume how an app is accessed. If the user names an app directly,
   open it directly. Never route through a parent app unless the user says so.
   - Wrong: "Open Swiggy, tap Instamart"
   - Right: "Open Instamart"

3. Only add steps the user skipped that are purely mechanical:
   - Acceptable: "open the app first", "tap the search bar"
   - Not acceptable: renaming anything the user said

4. For info requests ("what's the price", "what's the fare"):
   - End the goal at the target screen. Never say "show me", "tell me", "read", "return".
   - Bad: "Tell me the Uber fare to Indiranagar"
   - Good: "Open Uber, set destination to Indiranagar, wait for ride options to load"
   - The screenshot is the answer. Read it visually after the agent finishes.

5. For context-aware follow-ups ("order it", "complete checkout", "confirm it"):
   - Read last_result.json to confirm what the previous task did
   - Add that context at the start of the goal string
   - Keep the user's current words unchanged after the context
   - Wrong: "order greek yogurt"
   - Right: "Greek yogurt is already in the Instamart cart. Open Instamart, go to cart, complete checkout."

If ambiguous, ask before constructing the goal.

---

Task decomposition

- Break complex workflows into sequential atomic runs — verify each succeeded before starting the next.

Notes

- Simple tasks: 30–120s. Complex tasks: up to 10 minutes.
- Use `--steps 40+` for multi-screen flows or checkout.
- On `success: false`, check the Telegram message the monitor sent for summary and screenshot.
- Never auto-retry a checkout run — verify manually first.
