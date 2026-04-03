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
Always run in background. `--json` is mandatory — it ensures stdout is a single parseable JSON object.
- `exec command="cd ~/android-automation-agent && python run.py \"<goal>\" --json" background=true` → save the returned `sessionId`
- Tell user: "Started — I'll check back when it's done."
- `notifyOnExit` fires automatically when the process exits — no sleep loop needed
- On notification: `process action=poll sessionId=<id>` → drains final stdout + exit status

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

Goal string rules
- The agent navigates and taps. It cannot read text, extract values, or report data back.
- For info requests ("what's the price", "what's the fare", "is X in my cart"):
    Translate to a navigation goal ending at the target screen. Do not include "show me", "read",
    "confirm", or "return" in the goal string.
    Bad:  "Open Instamart, search diet coke, show me the price"
    Good: "Open Instamart, search for diet coke, wait for search results to load"
    The screenshot OpenClaw receives after the run IS the answer. Read it visually and report.
- For action requests ("add milk to cart", "open settings"):
    Be precise and step-by-step. Include the exact item name, app name, and all intermediate steps.
    Bad:  "buy me milk"
    Good: "Open Blinkit, search for Nandini toned milk 500ml, tap the first result, tap Add to cart"
- If the user's request is ambiguous, ask before constructing the goal.

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
