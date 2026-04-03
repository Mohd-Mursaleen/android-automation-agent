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
Always run in background. Stay responsive to the user while automation is running.
1. Run with `background: true`
2. Tell user: "Started — I'll check back when it's done."
3. Poll until process exits
4. Read JSON from stdout (`summary` describes actions taken, not screen content — ignore it for data)
5. Send the final screenshot and report visually (see below)

After every run
The agent writes the final screenshot to `~/storage/shared/android_agent/last_screenshot.png` on exit. Send it immediately — it is the ground truth of what the screen shows:
`curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument" -F "chat_id=${TELEGRAM_CHAT_ID}" -F "document=@${HOME}/storage/shared/android_agent/last_screenshot.png" -F "caption=<summary from JSON>"`
Then analyze the image visually, report what you see (prices, status, results), and ask if the user wants to take any action.

Check current screen (anytime)
When user asks "what's on screen?", "what's happening?", or "show me the phone" — take a fresh screencap and send it:
`adb exec-out screencap -p > /tmp/screen.png && curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendDocument" -F "chat_id=${TELEGRAM_CHAT_ID}" -F "document=@/tmp/screen.png" -F "caption=Current screen"`
Then analyze what's visible and report it.
Always use a fresh screencap here — `last_screenshot.png` may be from a previous run.

Goal string format
- Bad: `"buy me milk"`
- Good: `"Open Blinkit, search for Nandini toned milk 500ml, tap first result, tap Add to cart, verify cart badge shows 1 item"`

Task decomposition
- Break complex workflows into sequential atomic runs — verify each run succeeded before starting the next.

Notes
- Always run screen unlock script before every automation run.
- Always pass `--json` when calling from OpenClaw or any automated context.
- Run in background (`background: true`) and poll until exit — never kill early.
- Simple tasks: 30–120s. Complex tasks: up to 10 minutes.
- Use `--steps 40+` for multi-screen flows or checkout.
- On `success: false`, read `summary` to understand what happened; send screenshot to see current state.
- Never auto-retry a checkout run — verify manually first.
