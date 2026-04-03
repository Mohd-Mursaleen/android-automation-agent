---
name: android-automation-agent
description: Use android-automation-agent to run precise Android UI automation tasks via ADB and LLM vision on the same Termux device.
metadata: {"clawdbot":{"emoji":"📱","requires":{"bins":["adb","python3"]}}}
---

# android-automation-agent

Automates real Android UI via ADB + LLM vision. One goal string in, one JSON result out.

Quick start
- `cd ~/android-automation-agent && python run.py "Open Settings" --json`
- `cd ~/android-automation-agent && python run.py "Open Blinkit, add milk to cart" --steps 40 --json`
- `cd ~/android-automation-agent && python run.py --check`

Run pattern
Always run in background. Save the sessionId returned by exec.
1. exec command="cd ~/android-automation-agent && python run.py '<goal>' --json --steps <N>" background=true
   → save the returned sessionId
2. Tell user: "Started — I'll update you as soon as it's done."
3. notifyOnExit fires automatically when the process exits — no sleep loop, no polling
4. Immediately on the heartbeat: run process action=poll sessionId=<id>
   → this returns the final stdout which contains the JSON result
5. Parse the JSON from the poll output — do NOT run cat or any file read
6. Follow "On completion" steps below immediately

On completion (run immediately on heartbeat, no user input needed)
1. Get result: process action=poll sessionId=<id> — parse the JSON from stdout
2. Send screenshot via CLI (no exec call, no curl):
   openclaw message send --channel telegram --target <user_id> \
     --message "<summary from JSON>" \
     --media ~/storage/shared/android_agent/last_screenshot.png \
     --force-document
3. Read the screenshot visually — identify exact prices, status, text on screen
4. Reply in 3 sentences max: (1) task outcome, (2) exact data you see on screen,
   (3) ask what to do next
5. CRITICAL: Do not run cat, do not read any file, do not make any exec call
   in this heartbeat turn. All data comes from process poll stdout only.

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
  Bad:  "Tell me the Uber fare to Indiranagar"
  Good: "Open Uber, set destination to Indiranagar, wait for ride options to load"
  The screenshot IS the answer. Read it visually and report.

For action requests ("add to cart", "book ride", "search for X"):
  Be precise. Include exact item name, app, and all steps.
  Bad:  "buy me milk"
  Good: "Open Blinkit, search for Nandini toned milk 500ml, tap first result, tap Add to cart"

If ambiguous, ask before constructing the goal.

Task decomposition
- Break complex workflows into sequential atomic runs — verify each run succeeded before starting the next.

Notes
- Always run screen unlock script before every automation run.
- Always pass `--json` when calling from OpenClaw or any automated context.
- Run in background (`background: true`) and poll until exit — never kill early.
- Simple tasks: 30–120s. Complex tasks: up to 10 minutes.
- Use `--steps 40+` for multi-screen flows or checkout.
- On `success: false`, read `summary` to understand what happened; attach screenshot to see current state.
- Never auto-retry a checkout run — verify manually first.
- On completion: get all data from process poll stdout JSON only.
  Never run cat or any file read in a heartbeat turn — it triggers approval loops.
- After reading screenshot via process poll result, reply in 3 sentences max:
  task outcome, exact visible data (prices/text/status), next action options.
