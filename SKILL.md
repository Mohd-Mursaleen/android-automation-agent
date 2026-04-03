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

Background execution pattern
Run every automation in background. Stay responsive to the user while it runs.
1. Start: run the command with `background: true`
2. Immediately tell the user: "Started — I'll check back when it's done."
3. Poll until process exits
4. On exit: read result JSON, take a fresh screencap, report to user

Read results
- Stdout: one JSON object on exit — `{"success":bool,"goal":"...","steps":N,"summary":"...","screenshot_path":"...","result_path":"..."}`
- `summary` describes actions taken and exit state — use it to understand what happened, not as a source of screen data
- Last result: `cat ~/storage/shared/android_agent/last_result.json`
- Last screenshot: `~/storage/shared/android_agent/last_screenshot.png`

Read screen data (prices, listings, text, availability)
- The `summary` field does NOT contain screen content — never report prices, item names, or any values from it
- After automation exits, always take a fresh screencap and read it directly:
  `adb exec-out screencap -p > /tmp/screen_check.png`
- Report only what you can see in that image

Check current screen (anytime)
- `adb exec-out screencap -p > /tmp/screen.png`

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
- On `success: false`, read `summary` to understand what happened; take a fresh screencap to see current state.
- Never auto-retry a checkout run — verify manually first.
