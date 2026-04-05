"""
Planner node — breaks the overall task into 2–5 ordered, verifiable subgoals.
LLM: google/gemini-3-flash-preview .
"""

import json
import logging
from typing import Optional

from android_agent.graph.config import config
from android_agent.graph.state import AgentState, Subgoal
from android_agent.openrouter import text_completion

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a mobile automation planner. Given a high-level task to perform on an
Android device, break it into 2-5 ordered, concrete subgoals.

CRITICAL RULES:
- Use the EXACT words from the task. Do NOT rephrase, rename, or substitute
  anything the user said. If the task says "bike ride", the subgoal says
  "bike ride" — not "Uber Moto", not "motorcycle taxi".
- Do NOT assume which app to use unless the task explicitly names one.
- Do NOT add product names, brand names, ride types, or specific options
  that are not in the original task.
- Each subgoal must be a single verifiable UI action or navigation step.
- Subgoals must be ordered — N cannot start before N-1 is complete.
- NEVER create subgoals that read, extract, or report data. The agent taps
  and navigates — the final screenshot IS the output. Mark complete when
  the target screen is reached.

Example:
  Task: "Open Blinkit, search for milk, add to cart"
  Good: [
    {"id":"sg1","description":"Open the Blinkit app"},
    {"id":"sg2","description":"Tap the search bar and type milk"},
    {"id":"sg3","description":"Tap the first milk result to open it"},
    {"id":"sg4","description":"Tap Add to Cart button"}
  ]
  Bad: [
    {"id":"sg1","description":"Open Blinkit grocery delivery app"},
    {"id":"sg2","description":"Search for Amul Toned Milk 500ml"},
  ]
  The bad example added "grocery delivery" and invented "Amul Toned Milk 500ml"
  which were NOT in the original task.

Return ONLY a JSON array, no other text:
[
  {"id": "sg1", "description": "..."},
  {"id": "sg2", "description": "..."}
]"""


def planner_node(state: AgentState) -> AgentState:
    """
    Create or revise the subgoal plan based on the current task and any failures.

    Args:
        state: Current agent state; reads initial_goal and any failed subgoals.

    Returns:
        Updated state with a fresh subgoal_plan (all statuses reset to pending).
    """
    failed = [sg for sg in state.subgoal_plan if sg.status == "failed"]

    user_text = f"Task: {state.initial_goal}"
    if failed:
        user_text += (
            f"\n\nPrevious plan failed at subgoal: '{failed[0].description}'"
            f"\nFailure reason: {failed[0].failure_reason or 'unknown'}"
            "\n\nCreate a new plan that avoids this failure with a different approach."
        )

    subgoals = _call_with_retry(user_text)
    if subgoals is None:
        # Fallback: single subgoal = the original task
        subgoals = [{"id": "sg1", "description": state.initial_goal}]

    state.subgoal_plan = [
        Subgoal(id=sg["id"], description=sg["description"]) for sg in subgoals
    ]
    thought = f"[planner] Plan with {len(state.subgoal_plan)} subgoals: " + " → ".join(
        sg.description for sg in state.subgoal_plan
    )
    state.agents_thoughts.append(thought)
    logger.info(thought)
    return state


def _call_with_retry(user_text: str, retries: int = 2) -> Optional[list]:
    """
    Call the planner LLM and parse its JSON response, with retries on parse failure.

    Args:
        user_text: Prompt for the model.
        retries: How many times to retry on bad JSON.

    Returns:
        List of {id, description} dicts, or None on total failure.
    """
    for attempt in range(retries + 1):
        try:
            raw = text_completion(
                model=config.PLANNER_MODEL,
                system_prompt=_SYSTEM_PROMPT,
                user_text=user_text,
                max_tokens=512,
            )
            stripped = raw.strip()
            if stripped.startswith("```"):
                lines = stripped.split("\n")
                inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                stripped = "\n".join(inner).strip()
            return json.loads(stripped)
        except Exception as exc:
            logger.warning(f"Planner attempt {attempt + 1} failed: {exc}")
    return None
