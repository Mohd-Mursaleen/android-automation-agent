"""
Cortex node — the decision brain.

Receives screenshot + exact UI element coordinates (from Contextor) + the
current subgoal + history, and returns exactly ONE tool call with precise
coordinates. Critically: it MUST use coordinates from the UI tree, never
guess visually.

LLM: google/gemini-3-flash-preview via OpenRouter (vision).
"""

import json
import logging
from typing import Optional

from android_agent.graph.config import config
from android_agent.graph.state import AgentState
from android_agent.openrouter import vision_completion

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are the Cortex — the decision brain of an Android automation agent.

You receive:
1. A screenshot of the current Android screen
2. ALL UI elements with their EXACT pixel center coordinates (from the accessibility tree)
3. The current subgoal you must complete
4. Recent action history

Your job: decide the single next action to take.

CRITICAL RULES:
- When tapping, you MUST use the exact [x, y] center coordinates from the UI elements list.
  NEVER estimate or guess coordinates from the screenshot.
- If the target element is not in the UI list, scroll to reveal it first.
- If a text field already has text and you need to type something different,
  use clear_field FIRST, then type_text.

Available tools:

  tap(x, y)
    Tap using exact coordinates from the UI list.

  type_text(text, press_enter)
    Type into the focused field.
    press_enter: true = send Enter/submit after typing. false = just type, don't submit.
    DEFAULT to press_enter=false. Only set true when you explicitly need to submit
    (e.g. search bar that requires Enter to search, sending a chat message).

  clear_field()
    Clear all text in the currently focused input field.
    Use BEFORE type_text when the field already contains text you want to replace.

  gesture(x1, y1, x2, y2, duration_ms)
    Universal gesture primitive for scrolling, swiping, and slider dragging.
    SCROLL DOWN:  gesture(540, 1400, 540, 600,  duration_ms=150)  — fast
    SCROLL UP:    gesture(540, 600,  540, 1400, duration_ms=150)
    SWIPE LEFT:   gesture(900, 1000, 100, 1000, duration_ms=150)
    SWIPE RIGHT:  gesture(100, 1000, 900, 1000, duration_ms=150)
    SLIDER DRAG:  Use bounds from [SLIDER] annotation in UI list.
                  gesture(slider_x1, slider_cy, slider_x2, slider_cy, duration_ms=800)
                  Slow duration (700-900ms) is REQUIRED for sliders.

  long_press(x, y, duration_ms)
    Long press at coordinates. Use for context menus, text selection, drag-and-drop.
    Default duration_ms=1000. Use coordinates from the UI list.

  press_key(key)
    Send a key event. Options: "back", "home", "enter", "recent_apps"

  wait(seconds)
    Wait for the UI to settle (max 5s). Use after actions that trigger loading.

  mark_subgoal_complete(reason)
    Call when the current subgoal is achieved and visible on screen.

  mark_subgoal_failed(reason)
    Call ONLY when the subgoal is truly impossible (app crashed, element doesn't exist
    after scrolling everywhere, etc.)

IMPORTANT for text fields:
- If you see a search bar or text field WITH existing text and you need to change it:
  Step 1: tap the field → Step 2: clear_field → Step 3: type_text with your new text
- If the field is empty, just tap and type_text directly.
- Only use press_enter=true when submitting search queries or sending messages.

Return ONLY this JSON, no markdown, no explanation:
{
  "tool": "tap",
  "args": {"x": 540, "y": 1200},
  "reason": "Tapping the Settings icon at exact coordinates from UI tree",
  "thought": "I can see Settings in the UI elements list at [540,1200]"
}"""


def cortex_node(state: AgentState) -> AgentState:
    """
    Decide the next action using the current screenshot and UI element list.

    Args:
        state: Must have latest_screenshot_b64, latest_ui_hierarchy,
               and a running subgoal in subgoal_plan.

    Returns:
        Updated state with structured_decision populated.
    """
    current_sg = _get_running_subgoal(state)
    if current_sg is None:
        logger.warning("Cortex called but no running subgoal found")
        state.structured_decision = {"tool": "wait", "args": {"seconds": 1}}
        return state

    user_text = _build_prompt(state, current_sg.description)

    decision = _call_llm(user_text, state.latest_screenshot_b64)
    if decision is None:
        # Safe fallback: wait and retry next iteration
        decision = {
            "tool": "wait",
            "args": {"seconds": 2},
            "reason": "LLM call failed, waiting",
            "thought": "",
        }

    state.structured_decision = decision
    state.agents_thoughts.append(
        f"[cortex] {decision.get('tool')} — {decision.get('reason', '')}"
    )
    return state


def _get_running_subgoal(state: AgentState):
    """Return the first subgoal with status 'running', or None."""
    for sg in state.subgoal_plan:
        if sg.status == "running":
            return sg
    return None


def _build_prompt(state: AgentState, subgoal: str) -> str:
    """Build the user message for Cortex, including UI elements and history."""
    history = "\n".join(state.action_history[-5:]) or "(none yet)"
    thoughts = "\n".join(state.agents_thoughts[-3:]) or "(none)"
    ui = state.latest_ui_hierarchy or "(UI tree unavailable)"
    focused = state.focused_app or "unknown"

    return (
        f"Current subgoal: {subgoal}\n\n"
        f"UI Elements (USE THESE EXACT COORDINATES — do not guess):\n{ui}\n\n"
        f"Focused app: {focused}\n\n"
        f"Recent actions (last 5):\n{history}\n\n"
        f"Recent thoughts:\n{thoughts}\n\n"
        "Look at the screenshot and the UI elements above. Return the next action as JSON."
    )


def _call_llm(user_text: str, screenshot_b64: Optional[str]) -> Optional[dict]:
    """
    Call the Cortex LLM and parse the JSON response.

    Args:
        user_text: Assembled prompt text.
        screenshot_b64: Base64 PNG screenshot.

    Returns:
        Parsed decision dict, or None on failure.
    """
    if not screenshot_b64:
        logger.error("Cortex: no screenshot available")
        return None
    try:
        raw = vision_completion(
            model=config.CORTEX_MODEL,
            system_prompt=_SYSTEM_PROMPT,
            user_text=user_text,
            image_base64=screenshot_b64,
            max_tokens=512,
        )
        return _parse_json(raw)
    except Exception:
        logger.exception("Cortex LLM call failed")
        return None


def _parse_json(text: str) -> Optional[dict]:
    """Strip markdown fences and parse JSON."""
    s = text.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        s = "\n".join(inner).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        logger.error(f"Cortex JSON parse failed: {text[:300]}")
        return None
