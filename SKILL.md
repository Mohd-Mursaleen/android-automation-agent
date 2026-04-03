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
1. `exec command="python run.py '<goal>' --json --steps <N>" workdir="~/android-automation-agent" background=true` → save sessionId
2. Tell user: "Started — I'll update you automatically when it's done."
3. Wait for notifyOnExit heartbeat — do NOT poll in a loop, do NOT use sleep
4. On heartbeat: run `process action=poll sessionId=<id>` to get final JSON from stdout
5. Parse the JSON, then follow "On process exit" steps below

On process exit (run these steps immediately, without waiting for user input)
1. Read `~/storage/shared/android_agent/last_result.json` for the result
2. Send `~/storage/shared/android_agent/last_screenshot.png` as a file attachment
3. Look at the screenshot visually — read prices, status, text, anything relevant
4. Reply in exactly 3 sentences: (1) task outcome, (2) what you see on screen
   including exact prices/values/status, (3) ask what to do next
5. Never skip step 4. Never say "No response generated." If context is full,
   send the screenshot first, then send the 3-sentence reply as a separate message.

After every run
After `process poll` returns, stdout contains the JSON result and the screenshot is written to `~/storage/shared/android_agent/last_screenshot.png`.
- Parse the JSON from the poll output
- Attach `~/storage/shared/android_agent/last_screenshot.png` as a media file in your response
- Analyze the screenshot visually — report what you see (prices, status, results)
- Ask the user if they want to take any action
Note: `summary` in the JSON describes actions taken, not screen content — read data from the screenshot, not from `summary`.

Check current screen (anytime)
When user asks "what's on screen?", "what's happening?", or "show me the phone":
- `adb exec-out screencap -p > /tmp/screen.png`
- Attach `/tmp/screen.png` as a media file in your response
- Analyze what's visible and report it
Always use a fresh screencap here — `last_screenshot.png` may be from a previous run.

Goal string format
The agent navigates and taps. It CANNOT read text, extract values, or report
data back to you. You must translate user intent into navigation-only goals.

For info requests ("what's the price", "what's the fare", "is X available"):
  Translate to a goal that ends at the target screen. Never include "show me",
  "tell me", "read", "confirm", or "return" in the goal string.
  Bad:  "Tell me the Uber fare to Indiranagar"
  Good: "Open Uber, set destination to Indiranagar, wait for ride options to load"
  The screenshot you receive IS the answer. Read it and report prices/info yourself.

For action requests ("add to cart", "open settings", "search for X"):
  Be precise and step-by-step. Include exact item name, app name, all steps.
  Bad:  "buy me milk"
  Good: "Open Blinkit, search for Nandini toned milk 500ml, tap first result, tap Add to cart"

If the user's request is ambiguous, ask before constructing the goal.

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
- After sending the screenshot, always reply with what you see in 3 sentences max — task outcome, exact data visible (prices/values/text), next action options.
