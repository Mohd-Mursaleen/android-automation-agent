"""
Graph runner — drives the multi-node state machine as a pure Python while loop.
No langgraph, no asyncio, no compiled dependencies.

Loop structure:
  planner → [orchestrator → convergence → contextor → cortex → executor → summarizer] × N
"""

import datetime
import json
import logging
import os
import time

from android_agent.executor.android import AndroidExecutor
from android_agent.graph.nodes.contextor import contextor_node
from android_agent.graph.nodes.convergence import convergence_node
from android_agent.graph.nodes.cortex import cortex_node
from android_agent.graph.nodes.executor import ExecutorNode
from android_agent.graph.nodes.orchestrator import orchestrator_node
from android_agent.graph.nodes.planner import planner_node
from android_agent.graph.nodes.summarizer import summarizer_node
from android_agent.graph.state import AgentState

logger = logging.getLogger(__name__)

_LOCK_PATH = os.path.expanduser("~/storage/shared/android_agent/agent.lock")


def _acquire_lock(goal: str) -> bool:
    """
    Write a lock file with current PID and task details.

    Args:
        goal: The automation task goal string (stored in lock for diagnostics).

    Returns:
        True if lock acquired (safe to proceed), False if another task is running.
    """
    lock_dir = os.path.dirname(_LOCK_PATH)
    os.makedirs(lock_dir, exist_ok=True)

    if os.path.exists(_LOCK_PATH):
        try:
            with open(_LOCK_PATH, "r") as f:
                lock_data = json.load(f)
            pid = lock_data.get("pid")
            if pid:
                try:
                    os.kill(pid, 0)  # Signal 0 = existence check, does not kill
                    return False     # Process alive — lock is valid, we are busy
                except (OSError, ProcessLookupError):
                    logger.info(f"Cleaning stale lock (PID {pid} is dead)")
        except (json.JSONDecodeError, IOError):
            logger.warning("Corrupt lock file, removing")

    lock_data = {
        "pid": os.getpid(),
        "goal": goal,
        "started_at": datetime.datetime.now().isoformat(),
    }
    try:
        with open(_LOCK_PATH, "w") as f:
            json.dump(lock_data, f, indent=2)
        return True
    except IOError:
        logger.error("Failed to write lock file — proceeding anyway")
        return True  # Don't block on I/O failure


def _release_lock() -> None:
    """
    Remove the lock file if it belongs to this process. Best-effort — never raises.
    """
    try:
        if os.path.exists(_LOCK_PATH):
            with open(_LOCK_PATH, "r") as f:
                lock_data = json.load(f)
            if lock_data.get("pid") == os.getpid():
                os.remove(_LOCK_PATH)
    except Exception:
        pass


def run_task(
    goal: str,
    max_steps: int = 25,
    quality: int = 100,
    verbose: bool = True,
    device_id: str = None,
) -> AgentState:
    """
    Run a full Android automation task from start to finish.

    Args:
        goal: Natural language task description.
        max_steps: Hard cap on total ADB actions before giving up.
        quality: Screenshot quality percent (50–100). Higher = sharper but
                 slower and more expensive per step.
        verbose: Print live step-by-step progress.
        device_id: ADB device serial (optional; uses default device if None).

    Returns:
        Final AgentState — check state.task_complete and state.task_failed.
    """
    android_executor = AndroidExecutor()
    android_executor.image_quality = quality
    android_executor.screenshot_as_base64 = True

    executor_node = ExecutorNode(android_executor, device_id=device_id)

    state = AgentState(initial_goal=goal, max_steps=max_steps)
    _run_start = time.time()

    if verbose:
        print(f"\nGoal: {goal}")
        print(f"Max steps: {max_steps}  Quality: {quality}%\n")

    # Acquire lock — prevent concurrent automation on the same screen
    if not _acquire_lock(goal):
        state.task_failed = True
        try:
            with open(_LOCK_PATH, "r") as f:
                existing = json.load(f)
            state.failure_reason = (
                f"Another automation is already running: {existing.get('goal', 'unknown')} "
                f"(PID {existing.get('pid')}, started {existing.get('started_at', '?')})"
            )
        except Exception:
            state.failure_reason = "Another automation is already running"
        logger.error(state.failure_reason)
        if verbose:
            print(f"\n{state.failure_reason}")
        return state

    try:
        # Initial plan
        state = planner_node(state)
        if verbose:
            print("Plan:")
            for sg in state.subgoal_plan:
                print(f"  {sg.id}: {sg.description}")
            print()

        # Main loop
        while True:
            state = orchestrator_node(state)

            route = convergence_node(state)
            if route == "end":
                break
            if route == "replan":
                if verbose:
                    print("  [replan] Revising plan after failure...")
                state = planner_node(state)
                continue

            # route == "continue" — run one full action cycle
            state = contextor_node(state, android_executor)

            state = cortex_node(state)

            decision = state.structured_decision or {}
            if verbose:
                tool = decision.get("tool", "?")
                reason = decision.get("reason", "")[:80]
                print(f"  [Step {state.step_count + 1}] {tool} — {reason}")

            state = executor_node.execute(state)

            # Best-effort step progress write for external monitoring
            try:
                _step_path = os.path.expanduser("~/storage/shared/android_agent/last_step.json")
                os.makedirs(os.path.dirname(_step_path), exist_ok=True)
                with open(_step_path, "w") as _f:
                    json.dump({
                        "step": state.step_count,
                        "last_action": state.action_history[-1] if state.action_history else "",
                        "elapsed_seconds": int(time.time() - _run_start),
                        "goal": state.initial_goal,
                    }, _f)
            except Exception:
                pass

            state = summarizer_node(state, android_executor)

            # Check again after summarizer (it may have marked a subgoal failed)
            route = convergence_node(state)
            if route == "end":
                break
            if route == "replan":
                if verbose:
                    print("  [replan] Revising plan after failure...")
                state = planner_node(state)

        # Final status
        if verbose:
            if state.task_complete:
                print(f"\nTask complete in {state.step_count} steps.")
            else:
                print(f"\nTask failed: {state.failure_reason}")

    finally:
        _release_lock()

    return state
