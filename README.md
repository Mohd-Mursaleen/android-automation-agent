# android-ai-agent

> AI agent that automates any task on a real Android device.
> Works on Termux — no PC, no desktop, no ADB over USB required.

android-ai-agent is an open-source AI agent for Android automation.
It uses a multi-agent state machine to plan, execute, and verify tasks
on a real Android device using ADB — with no app-specific code, no
brittle selectors, and no desktop required.

Give it a goal in plain English. It figures out the rest.

```bash
python run.py "Open Instamart, search for Greek yogurt, add to cart"
python run.py "Book a Rapido auto to MG Road"
python run.py "Open Settings and find the Android version"
```

---

## How it works

android-ai-agent uses a 6-node state machine:

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

The key insight: by combining screenshots with `uiautomator dump`,
the Cortex agent gets exact pixel coordinates for every element.
No visual coordinate guessing. This is why taps are reliable.

---

## Requirements

- Android device with Developer Options + Wireless Debugging enabled
- Termux (from F-Droid) **or** any Linux/macOS with ADB installed
- Python 3.10+
- OpenRouter API key (free at [openrouter.ai/keys](https://openrouter.ai/keys))

---

## Setup

### On Termux (Android — no PC needed)

```bash
# Install dependencies
pkg install python android-tools git

# Clone
git clone https://github.com/Mohd-Mursaleen/android-ai-agent
cd android-ai-agent

# Setup (creates venv + installs deps + creates .env)
chmod +x setup.sh && ./setup.sh

# Add your OpenRouter API key
nano .env
# Set: OPENROUTER_API_KEY=your_key_here

# Connect ADB to the device itself
adb connect 127.0.0.1:5555

# Verify everything
python check.py
```

### On Linux / macOS

```bash
git clone https://github.com/Mohd-Mursaleen/android-ai-agent
cd android-ai-agent
chmod +x setup.sh && ./setup.sh
nano .env   # add OPENROUTER_API_KEY
python check.py
```

---

## Usage

```bash
# Activate venv (once per terminal session)
source .venv/bin/activate

# Run any task
python run.py "Open the Settings app"
python run.py "Open Chrome and search for weather in Bengaluru"
python run.py "Open Instamart, add milk and eggs to cart"
python run.py "Book a Rapido auto to MG Road" --steps 40
python run.py "Open Settings" --quiet

# Health check
python check.py
```

---

## Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

```env
# Required
OPENROUTER_API_KEY=your_key_here

# Optional — override default models
PLANNER_MODEL=google/gemini-3-flash-preview
CORTEX_MODEL=google/gemini-3-flash-preview
SUMMARIZER_MODEL=google/gemini-3.1-flash-lite-preview

# Optional
LOG_LEVEL=INFO
MAX_STEPS=25
```

---

## Models

| Agent      | Default                                | Role                     |
| ---------- | -------------------------------------- | ------------------------ |
| Planner    | `google/gemini-3-flash-preview`        | Task decomposition       |
| Cortex     | `google/gemini-3-flash-preview`        | Vision + decision making |
| Summarizer | `google/gemini-3.1-flash-lite-preview` | Action verification      |

All calls go through [OpenRouter](https://openrouter.ai) — one API key,
swap any model by setting an env variable.

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
android-ai-agent/
├── android_agent/
│   ├── openrouter.py          # LLM client (vision + text) via OpenRouter
│   ├── executor/
│   │   └── android.py         # ADB executor (tap, gesture, type, key) — do not modify
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
