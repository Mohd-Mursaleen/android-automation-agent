# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**android-ai-agent** is a Python framework for autonomous Android device automation via ADB, using LLMs routed through [OpenRouter](https://openrouter.ai). It runs on Termux (arm64) and requires zero Rust/C++ build dependencies.

## Setup

```bash
# Termux
pkg install python adb
git clone https://github.com/Mohd-Mursaleen/android-ai-agent && cd android-ai-agent
pip install -e .
export OPENROUTER_API_KEY="your-key-here"
python check.py

# macOS / Linux
chmod +x setup.sh && ./setup.sh
```

## Commands

```bash
# Health check
python check.py

# Run a task
python run.py "open Settings and show the Android version" --verbose
python run.py "Open Instamart, add milk to cart" --steps 40 --quiet

# python run.py options:
#   --steps N     hard cap on action count (default 25)
#   --device ID   ADB serial (auto-detected if omitted)
#   --quiet       suppress step-by-step output
#   --check       run health check only, then exit
#   --quality N   screenshot quality (default 100, no compression)
```

**Testing:**

```bash
pytest
pytest tests/test_android.py
```

## Architecture

Three-component pipeline per action cycle:

1. **Executor** (`executor/android.py`) — takes a screenshot via `adb exec-out screencap -p`, compresses it by `image_quality` percent, returns base64. All ADB taps/swipes/types go through here.
2. **Planner** (`graph/nodes/planner.py`) — text-only LLM; breaks the goal into 2–5 ordered subgoals as JSON.
3. **Cortex** (`graph/nodes/cortex.py`) — vision LLM; receives screenshot + UI element list from Contextor, returns one JSON action.

All LLM calls go through `android_agent/openrouter.py` using the OpenAI-compatible SDK pointed at `https://openrouter.ai/api/v1`. Set `OPENROUTER_API_KEY` in the environment.

### Execution loop (`graph/runner.py`)

```
state = planner_node(state)          # build subgoal plan
while True:
    state = orchestrator_node(state) # activate next subgoal
    route = convergence_node(state)  # "end" / "replan" / "continue"
    if route == "end": break
    if route == "replan": state = planner_node(state); continue
    state = contextor_node(state, executor)   # screenshot + uiautomator dump
    state = cortex_node(state)               # decide next action
    state = executor_node.execute(state)     # run ADB command
    state = summarizer_node(state, executor) # verify action worked
```

### Coordinate scaling

Default quality is 100 (no compression, no scaling). If quality is reduced,
`AndroidExecutor.image_scale_factor = 100 / quality`. When screenshots are compressed to N% of original size, coordinates from visual analysis are in that smaller space. `click_at_a_point` multiplies by `image_scale_factor` to hit the correct physical pixels.

**Critical**: `uiautomator dump` returns real screen pixels, not compressed-image pixels. The executor node sets `self.executor.image_scale_factor = 1.0` before every tap to prevent double-scaling.

### Tools available to Cortex

| Tool | Args | Notes |
|------|------|-------|
| tap | x, y | MUST use UI tree coordinates |
| type_text | text, press_enter | press_enter defaults to false. Only true for search submit / message send |
| clear_field | (none) | Clears focused text field via backspaces. Use before type_text on non-empty fields |
| gesture | x1, y1, x2, y2, duration_ms | Scroll, swipe, slider drag |
| long_press | x, y, duration_ms | Context menus, text selection. Default 1000ms |
| press_key | key | "back", "home", "enter", "recent_apps" |
| wait | seconds | Max 5s. Use after loading triggers |
| mark_subgoal_complete | reason | When subgoal is done |
| mark_subgoal_failed | reason | When subgoal is impossible |

### Gesture primitive

All swipe/scroll/slider actions go through `gesture(x1, y1, x2, y2, duration_ms)`:

- Scroll: 150 ms
- Slider drag: 800 ms (slow is required — fast swipes are ignored by Android)

Contextor annotates sliders in the UI hierarchy as `[SLIDER bounds=x1,y1,x2,y2]` with explicit gesture coordinates so Cortex knows to use `duration_ms=800`.

### Module layout

```
android_agent/
├── __init__.py            # loads .env via python-dotenv
├── openrouter.py          # vision_completion() and text_completion() — all LLM I/O
├── executor/
│   ├── __init__.py        # Abstract Executor base class
│   └── android.py         # ADB-based implementation
├── graph/
│   ├── config.py          # Config class (reads from env)
│   ├── state.py           # AgentState + Subgoal dataclasses
│   ├── runner.py          # run_task() main loop
│   └── nodes/
│       ├── planner.py     # text LLM → subgoal JSON array
│       ├── orchestrator.py # activate next pending subgoal
│       ├── contextor.py   # screenshot + uiautomator dump → UI hierarchy string
│       ├── cortex.py      # vision LLM → single action JSON
│       ├── executor.py    # dispatch tool calls to android.py
│       ├── summarizer.py  # verify action succeeded (vision LLM)
│       └── convergence.py # route: end / replan / continue
└── utils/
    └── check.py           # ADB + OpenRouter health check
```

## Constraints

- **No Rust/C++ deps** — pure Python only; no `pyautogui`, `gradio`, `mlx`, `anthropic`, `google-generativeai`, `ollama`
- **OpenRouter only** — all LLM calls use `openai>=1.0.0` SDK with `base_url=https://openrouter.ai/api/v1`
- **Android only** — `executor/android.py` is the only executor
- **executor/android.py** — the stable ADB interface. Modify carefully and test after changes.
