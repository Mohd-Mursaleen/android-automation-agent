---
name: android-automation-agent
description: Use android-automation-agent to run precise Android UI automation tasks via ADB and LLM vision on the connected Android device. Trigger this skill for ANY request involving controlling, tapping, opening, searching, ordering, booking, or interacting with apps on the user's Android phone. Also trigger for "what's on my screen" or "show me the phone".
metadata:
  { "clawdbot": { "emoji": "📱", "requires": { "bins": ["adb", "python3"] } } }
---

# android-automation-agent

Automates real Android UI via ADB + LLM vision. One goal string in, one JSON result out.

---

## SECTION 1 — GOLDEN RULES (never violate these)

### Rule 1: Never rewrite the user's words

You are a DISPATCHER, not an interpreter. Your job is to pass the user's
intent to the android agent as faithfully as possible.

- User says "bike ride" → goal says "bike ride". NOT "Uber Moto".
- User says "order food" → goal says "order food". NOT "order butter chicken on Swiggy".
- User says "Instamart" → goal says "Open Instamart". NOT "Open Swiggy, navigate to Instamart".
- User says "milk" → goal says "milk". NOT "Amul Toned Milk 500ml".

The android agent reads the screen visually. It will find the right element.
You MUST trust it. Do NOT "help" by guessing UI labels, product names, or app flows.

### Rule 2: Never assume — ask first

If the user's request is missing critical information, ASK before running.

**Always ask for:**
- Which app to use (if not specified)
- Specific item details (brand, size, variant — if ordering/searching)
- Destination/address (if booking rides or deliveries)
- Any choice that has multiple options (payment method, timing, etc.)

**Never ask for:**
- Mechanical UI steps (how to navigate within an app — the agent handles this)
- Things already answered in this conversation or in preferences.json

**Example:**
```
User: "Book me a ride to college"
You: "Which app should I use — Uber, Ola, or Rapido?"
User: "Uber"
You: "Got it. What's your college address? Or should I just type 'college' in the destination?"
User: "Just type SIRMVIT Bengaluru"
→ Goal: "Open Uber, set destination to SIRMVIT Bengaluru, wait for ride options to load"
```

### Rule 3: Check preferences before asking

Before asking the user, check `~/.openclaw/preferences.json` for saved answers.
If a preference exists, use it silently. If not, ask, then offer to save it.

### Rule 4: Break complex tasks into separate runs

The android agent is good at simple-to-medium tasks (open app, search, tap, add to cart).
It struggles with long multi-screen flows done in one shot.

**Always decompose complex tasks into sequential atomic runs.**
Run each step separately. Check the result JSON between each run.
Only proceed to the next step after confirming the previous one succeeded.

---

## SECTION 2 — Preferences System

### File: `~/.openclaw/preferences.json`

If this file doesn't exist, create it with `{}` as content on first use.

Structure:
```json
{
  "apps": {
    "groceries": "Blinkit",
    "rides": "Uber",
    "food_delivery": "Swiggy"
  },
  "products": {
    "milk": {
      "name": "Nandini Toned Milk",
      "quantity": "500ml",
      "app": "Blinkit"
    }
  },
  "addresses": {
    "home": "123 Example Street, Bengaluru",
    "college": "SIRMVIT, Bengaluru"
  },
  "defaults": {
    "payment_method": "Google Pay"
  }
}
```

### How to use preferences

1. When the user asks to "buy milk" → check `preferences.products.milk`
   - Found → use it: "Open Blinkit, search for Nandini Toned Milk 500ml, add to cart"
   - Not found → ask the user, then offer: "Want me to remember this for next time?"

2. When the user says "book a ride" → check `preferences.apps.rides`
   - Found → use that app without asking
   - Not found → ask which app

3. When the user says "to college" → check `preferences.addresses.college`
   - Found → use the saved address string
   - Not found → ask, then offer to save

### Saving preferences

After learning a new preference from the user, write it to the JSON file:
```bash
python3 -c "
import json, os
path = os.path.expanduser('~/.openclaw/preferences.json')
try:
    prefs = json.load(open(path))
except:
    prefs = {}
prefs.setdefault('products', {})['milk'] = {'name': 'Nandini Toned Milk', 'quantity': '500ml', 'app': 'Blinkit'}
json.dump(prefs, open(path, 'w'), indent=2)
"
```
Adapt the above pattern for whatever preference you're saving.

---

## SECTION 3 — Run Pattern (Background Run & Auto-Notify)

ALWAYS follow this exact flow. Never deviate.

### Step 0 — Check if the agent is busy

Before ANYTHING else, check if a task is already running:

```bash
bash ~/android-automation-agent/scripts/check_busy.sh
```

- If output is `FREE` → proceed to Step 1.
- If output starts with `BUSY:` → tell the user:
  "I'm currently running: [task details from output]. Wait for it to finish, or tell me to cancel it so I can start your new task."
- Do NOT proceed to Step 1 if busy. Do NOT kill monitors or start a new run.

### Cancelling a running task

If the user says "cancel it", "stop", or "kill the current task":

```bash
LOCK_FILE="$HOME/storage/shared/android_agent/agent.lock"
if [ -f "$LOCK_FILE" ]; then
    PID=$(python3 -c "import json; print(json.load(open('$LOCK_FILE')).get('pid',''))" 2>/dev/null)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null
        sleep 2
    fi
    rm -f "$LOCK_FILE"
fi
bash ~/android-automation-agent/scripts/kill_monitors.sh
```

Then tell the user: "Cancelled. Ready for your next task."

### Step 1 — Kill old monitors, start fresh ones

Ensure BOT_TOKEN and CHAT_ID are exported.

```bash
bash ~/android-automation-agent/scripts/kill_monitors.sh
```

```
exec yieldMs=500 command='bash ~/android-automation-agent/scripts/monitor_result.sh'
```

```
exec yieldMs=500 command='bash ~/android-automation-agent/scripts/monitor_progress.sh'
```

### Step 2 — Wake the device, then run the agent

Tell user: "Task started. Goal: '<goal string used>'. You'll get screenshot updates every 45s."

```bash
bash ~/android-automation-agent/scripts/wake_and_unlock.sh && \
cd ~/android-automation-agent && python run.py '<GOAL>' --steps <N> --json
```

The agent sends a "🤖 Android Agent started" notification to Telegram automatically
when it begins, and a final result notification with screenshot when it finishes.
You do not need to send any manual curl notifications.

### Step 3 — End your turn. Monitors deliver the result + screenshot.

### Hard rules for running

- Never use sessions_yield — models ignore it.
- Never use background=true + notifyOnExit — heartbeats fire into dead sessions.
- Never promise "I'll notify you" without monitors already running.
- Always run wake_and_unlock.sh before the agent.

---

## SECTION 4 — Goal String Construction

### Format

The goal string you pass to `run.py` must be:
1. The user's words, lightly structured into a task
2. With ZERO substitutions, brand names, or assumptions you added

### Only add mechanical steps the user skipped

Acceptable additions:
- "Open [app name]" at the start (if the user named the app but didn't say "open")
- "tap the search bar" (mechanical UI navigation)
- "wait for results to load" (mechanical wait)

NOT acceptable:
- Renaming anything the user said
- Adding product brands, variants, sizes the user didn't specify
- Guessing how an app is structured (e.g. "go to Swiggy then tap Instamart")
- Adding "show me", "tell me", "read", "return" — the screenshot IS the answer

### For info requests ("what's the fare", "check my balance")

End the goal at the target screen. Never say "read the value" or "tell me the price".
The final screenshot is the answer — you will read it visually after the run.

- Bad: "Open Uber, tell me the fare to Koramangala"
- Good: "Open Uber, set destination to Koramangala, wait for ride options to load"

### For follow-up commands ("order it", "confirm", "go ahead")

Read `~/storage/shared/android_agent/last_result.json` to see what the previous run did.
Include that context at the START of the new goal, then append the user's current command.

- Bad: "complete checkout"
- Good: "Nandini milk is already in the Blinkit cart. Open Blinkit, go to cart, proceed to checkout"

### Fresh tasks vs follow-up tasks

**Fresh task** = user names an app or starts a new workflow from scratch.
- Examples: "Open Uber", "Search for shoes on Amazon", "Check my Gmail"
- The goal string should start with "Open [app]" — the agent will navigate from whatever is on screen.

**Follow-up task** = user continues a workflow that's already on screen.
- Examples: "book it", "confirm the order", "select the cheapest option", "go ahead"
- The goal string should describe the CURRENT screen state + what to do next.
- The wake script will NOT press Home or Back — the app stays exactly where it was.
- Example goal: "Rapido ride booking screen is showing with ride details. Tap the Book Now button."

**How to detect follow-up tasks:**
1. The user's message implies continuation ("do it", "confirm", "book it", "go ahead", "next", "order")
2. There is a recent `last_result.json` (check modified time — if less than 10 minutes old, it's relevant)
3. The previous task succeeded (`success: true`)

When all three are true → this is a follow-up. Read `last_result.json` for context and construct the goal accordingly. Do NOT add "Open [app]" — the app is already open.

### If ambiguous → ASK. Do not guess.

---

## SECTION 5 — Complex Task Decomposition Protocol

For any task involving 3+ screens, multiple apps, or checkout/payment:

### Step-by-step protocol

1. **Collect all info first** — ask the user for every missing detail BEFORE starting any automation
2. **Decompose into atomic runs** — each run should do ONE thing (open app, search, add to cart, etc.)
3. **Run step 1** → wait for result JSON → verify success
4. **If success** → read last_result.json → construct next goal WITH context → run step 2
5. **If failure** → report failure + screenshot to user → ask how to proceed
6. **NEVER auto-retry checkout or payment** — always ask the user to confirm first

### Example decomposition — "Order milk from Blinkit"

```
Step 1: Collect info
  - Check preferences.json → found: Nandini Toned Milk 500ml, app: Blinkit
  - No need to ask user

Step 2: Run #1
  Goal: "Open Blinkit, search for Nandini Toned Milk 500ml"
  --steps 25 --json
  → Wait for result → Check success

Step 3: Run #2
  Read last_result.json for context.
  Goal: "Search results for Nandini milk are showing on Blinkit. Tap the Nandini Toned Milk 500ml product and tap Add to Cart"
  --steps 20 --json
  → Wait for result → Check success

Step 4: Run #3
  Goal: "Item is in Blinkit cart. Open cart, verify items, proceed to checkout"
  --steps 20 --json
  → Wait for result → Check success

Step 5: STOP — send screenshot to user
  "Cart is ready for checkout. Total is visible on screen. Should I place the order?"
  → Only proceed if user confirms
```

### Step count guidelines

- Simple tasks (open app, single search): `--steps 15`
- Medium tasks (search + navigate + tap): `--steps 25`
- Complex tasks (multi-screen flows): `--steps 35`
- Checkout flows: `--steps 25` (but always stop before final payment)

---

## SECTION 6 — Check Current Screen

When user asks "what's on screen?", "what's happening?", or "show me the phone":

```bash
adb exec-out screencap -p > /tmp/screen.png
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
  -F "chat_id=${CHAT_ID}" \
  -F "document=@/tmp/screen.png"
```

Always take a FRESH screenshot. Never use last_screenshot.png from a previous run.

---

## SECTION 7 — Timing & Troubleshooting

- Simple tasks: 30-120 seconds
- Complex tasks: up to 10 minutes
- If `success: false`, check the Telegram screenshot the monitor sent
- Common failure: agent couldn't find an element → it may be off-screen → suggest re-running with "scroll down first, then..."
- Never auto-retry a checkout run — always verify manually first
- If the agent keeps failing on the same step, try rephrasing the goal to be simpler/more specific
- **Popup/overlay buttons not responding**: Some apps (Rapido, Uber, Swiggy) use custom
  popups that are invisible to the UI accessibility tree. The agent will switch to
  vision-based tapping automatically. If it still fails, try breaking the task into
  smaller steps — e.g. separate "select Auto" and "tap Book" into two runs.
- **Agent stuck tapping same spot**: The system detects tap loops and auto-fails after
  4 identical taps. If this happens, the target element may need a different interaction
  (long_press, gesture, or scroll to reveal it in a different position).
