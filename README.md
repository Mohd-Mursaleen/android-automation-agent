# android-automation-agent

> Automate any task on an Android device using plain English.
> Powered by LLMs. Controlled via ADB. Works everywhere.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![OpenRouter](https://img.shields.io/badge/powered%20by-OpenRouter-orange.svg)](https://openrouter.ai)

android-automation-agent is an open-source AI agent for Android automation.
It uses a multi-agent state machine to plan, execute, and verify tasks
on any Android device using ADB — with no app-specific code, no
brittle selectors, and no manual scripting.

Give it a goal in plain English. It figures out the rest.

```bash
python run.py "Open Settings and find the Android version"
python run.py "Search for headphones on Amazon and add the first result to cart"
python run.py "Open YouTube and play the first trending video"
python run.py "Open Instamart, search for Greek yogurt, add to cart"
```

---

## How it works

android-automation-agent uses a 6-node state machine:

```
PLANNER → ORCHESTRATOR → CONTEXTOR → CORTEX → EXECUTOR → SUMMARIZER
                              ↑__________________________|
```

| Node             | What it does                                                                                                      |
| ---------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Planner**      | Breaks your goal into 2–5 ordered, verifiable subgoals                                                            |
| **Orchestrator** | Picks the next pending subgoal and activates it                                                                   |
| **Contextor**    | Takes a screenshot AND dumps the full UI accessibility tree with exact element coordinates via `uiautomator dump` |
| **Cortex**       | The brain — decides the next action using exact coordinates from the UI tree, never guesses visually              |
| **Executor**     | Runs ADB commands on the device (tap, gesture, type, key press)                                                   |
| **Summarizer**   | Takes a new screenshot and verifies the action worked before moving on                                            |

**The key insight:** by combining screenshots with `uiautomator dump`,
the Cortex agent gets exact pixel coordinates for every UI element.
No visual coordinate guessing. This is why taps are reliable.

---

## Requirements

- Android device with Developer Options + ADB Debugging enabled
- ADB installed on your host machine (or on the device via Termux)
- Python 3.10+
- OpenRouter API key — free at [openrouter.ai/keys](https://openrouter.ai/keys)

---

## Setup

### Linux / macOS

```bash
# Install ADB if you don't have it
# macOS:  brew install android-platform-tools
# Ubuntu: sudo apt install adb

git clone https://github.com/Mohd-Mursaleen/android-automation-agent
cd android-automation-agent

# One-command setup (creates venv, installs deps, creates .env)
chmod +x setup.sh && ./setup.sh

# Add your OpenRouter API key
nano .env   # set OPENROUTER_API_KEY=your_key_here

# Connect your device via USB or WiFi ADB
adb devices   # confirm device is listed

# Verify everything works
python check.py
```

### Windows (WSL or native)

```bash
# Option A — WSL (recommended)
wsl --install   # if not already set up
# then follow the Linux steps above inside WSL

# Option B — native Windows with ADB
# Install Python 3.10+ from python.org
# Install ADB: https://developer.android.com/studio/releases/platform-tools
git clone https://github.com/Mohd-Mursaleen/android-automation-agent
cd android-automation-agent
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
python check.py
```

### Termux (run directly on your Android device — no PC needed)

```bash
pkg install python android-tools git
git clone https://github.com/Mohd-Mursaleen/android-automation-agent
cd android-automation-agent
chmod +x setup.sh && ./setup.sh
nano .env   # add OPENROUTER_API_KEY
adb connect 127.0.0.1:5555   # connect ADB to device itself
python check.py
```

> **Termux-friendly:** This project works natively on Termux (arm64) with
> zero compiled dependencies — no Rust, no C++, pure Python only.
> You can run the entire agent on your Android phone with no PC at all.

---

## Usage

```bash
# Activate venv (once per terminal session)
source .venv/bin/activate   # Linux/macOS/Termux
# or: .venv\Scripts\activate   (Windows)

# Run any task
python run.py "Open the Settings app"
python run.py "Open Chrome and search for the weather"
python run.py "Open YouTube and play the first trending video"
python run.py "Open Instamart, add milk and eggs to cart"

# Long task — increase step budget
python run.py "Book a cab to the airport" --steps 40

# Suppress step-by-step output
python run.py "Open Settings" --quiet

# Target a specific device (from: adb devices)
python run.py "Open Settings" --device emulator-5554

# Health check
python check.py
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
# Required
OPENROUTER_API_KEY=your_key_here

# Optional — override default models (any model on openrouter.ai works)
# PLANNER_MODEL=anthropic/claude-sonnet-4-5
# CORTEX_MODEL=google/gemini-2.5-flash-preview
# SUMMARIZER_MODEL=google/gemini-flash-1.5

# Optional
# LOG_LEVEL=INFO
# MAX_STEPS=25
```

---

## Models

| Agent      | Default                           | Role                     |
| ---------- | --------------------------------- | ------------------------ |
| Planner    | `anthropic/claude-sonnet-4-5`     | Task decomposition       |
| Cortex     | `google/gemini-2.5-flash-preview` | Vision + decision making |
| Summarizer | `google/gemini-flash-1.5`         | Action verification      |

All calls go through [OpenRouter](https://openrouter.ai) — one API key,
swap any model by editing your `.env`.

---

## Use as a Python library

```python
from android_agent.graph.runner import run_task

state = run_task(
    goal="Open Settings and find the Android version",
    max_steps=25,
    verbose=True,
)

print("Success:", state.task_complete)
print("History:", state.action_history)
```

---

## Project structure

```
android-automation-agent/
├── android_agent/
│   ├── openrouter.py          # LLM client (vision + text) via OpenRouter
│   ├── executor/
│   │   └── android.py         # ADB executor (tap, gesture, type, key)
│   ├── graph/
│   │   ├── config.py          # Model + env config
│   │   ├── state.py           # AgentState dataclass
│   │   ├── runner.py          # Main loop
│   │   └── nodes/
│   │       ├── planner.py
│   │       ├── orchestrator.py
│   │       ├── contextor.py
│   │       ├── cortex.py
│   │       ├── executor.py
│   │       ├── summarizer.py
│   │       └── convergence.py
│   └── utils/
│       └── check.py
├── run.py                     # Entry point
├── check.py                   # Health check
├── setup.sh                   # One-command setup
├── requirements.txt
├── .env.example
└── pyproject.toml
```

---

## Contributing

PRs welcome. Please open an issue first for major changes.

---

## License

MIT — free to use, modify, and distribute.

<!-- GitHub Topics to add on this repo for SEO:
android, android-automation, ai-agent, adb, termux, llm,
mobile-automation, android-testing, openrouter, gemini,
claude, computer-use, mobile-agent, python, automation
-->
