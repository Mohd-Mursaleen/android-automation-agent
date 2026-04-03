#!/usr/bin/env python3
"""
android-ai-agent — run this file to start an automation task.

Usage:
    python run.py "Open Settings"
    python run.py "Open Instamart and search for milk" --steps 30
    python run.py "Open Settings" --json
    python run.py --check
"""
import argparse
import base64
import json
import logging
import os
import sys

# Load .env before any other import so API keys are available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Artifact paths written after every run (best-effort, for OpenClaw)
_ARTIFACT_DIR = os.path.expanduser("~/storage/shared/android_agent")
_RESULT_PATH = os.path.join(_ARTIFACT_DIR, "last_result.json")
_SCREENSHOT_PATH = os.path.join(_ARTIFACT_DIR, "last_screenshot.png")


def _build_summary(state) -> str:
    """
    Build a human-readable summary from final agent state.

    Combines subgoal completion status, last action, and failure reason
    so OpenClaw can answer the user without inspecting the screenshot first.

    Args:
        state: Final AgentState from run_task().

    Returns:
        Single-paragraph summary string.
    """
    parts = []

    complete = [sg.description for sg in state.subgoal_plan if sg.status == "complete"]
    failed_sgs = [sg.description for sg in state.subgoal_plan if sg.status == "failed"]

    if complete:
        parts.append("Completed: " + "; ".join(complete) + ".")
    if failed_sgs:
        parts.append("Did not complete: " + "; ".join(failed_sgs) + ".")

    if state.action_history:
        parts.append(f"Last action: {state.action_history[-1]}.")

    if not state.task_complete and state.failure_reason:
        parts.append(f"Failure reason: {state.failure_reason}.")

    if not parts:
        return "Task completed successfully." if state.task_complete else "Task did not complete."

    return " ".join(parts)


def _write_artifacts(state, result: dict) -> None:
    """
    Write last_result.json and last_screenshot.png to shared storage.

    Best-effort: any I/O failure is silently swallowed so it never
    crashes or corrupts the main run result.

    Args:
        state: Final AgentState from run_task().
        result: The result dict that will also be printed in JSON mode.
    """
    try:
        os.makedirs(_ARTIFACT_DIR, exist_ok=True)

        with open(_RESULT_PATH, "w") as f:
            json.dump(result, f, indent=2)

        if state.latest_screenshot_b64:
            img_bytes = base64.b64decode(state.latest_screenshot_b64)
            with open(_SCREENSHOT_PATH, "wb") as f:
                f.write(img_bytes)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="android-ai-agent: AI-powered Android automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py "Open Settings"
  python run.py "Open Instamart and add milk to cart" --steps 40
  python run.py "Open Settings" --json
  python run.py --check
        """,
    )
    parser.add_argument(
        "goal",
        nargs="?",
        help="The task to perform on your Android device",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=25,
        metavar="N",
        help="Maximum number of steps (default: 25)",
    )
    parser.add_argument(
        "--device",
        default=None,
        metavar="SERIAL",
        help="ADB device serial (from: adb devices). Auto-detected if omitted.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress step-by-step output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="Print one final JSON result to stdout; suppress all other output",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify ADB connection and OpenRouter API key, then exit",
    )

    args = parser.parse_args()

    if args.check:
        from android_agent.utils.check import run_check

        ok = run_check()
        sys.exit(0 if ok else 1)

    if not args.goal:
        parser.print_help()
        sys.exit(1)

    # Suppress all logging in JSON mode so stdout carries only the result object
    if args.json_mode:
        logging.disable(logging.CRITICAL)

    from android_agent.graph.runner import run_task

    state = run_task(
        goal=args.goal,
        max_steps=args.steps,
        verbose=(not args.quiet and not args.json_mode),
        device_id=args.device,
    )

    # --- Determine error type (only set on failure) ---
    error = None
    if not state.task_complete:
        if state.step_count >= state.max_steps:
            error = "max_steps_reached"
        elif state.task_failed:
            error = state.failure_reason or "task_failed"
        else:
            error = "unknown"

    # --- Build result dict (field order matches documented JSON format) ---
    result = {
        "success": state.task_complete,
        "goal": args.goal,
        "steps": state.step_count,
    }
    if error:
        result["error"] = error
    result["summary"] = _build_summary(state)
    result["screenshot_path"] = _SCREENSHOT_PATH if state.latest_screenshot_b64 else None
    result["result_path"] = _RESULT_PATH

    # Write artifacts after every run — always, not just in JSON mode
    _write_artifacts(state, result)

    if args.json_mode:
        print(json.dumps(result))
        sys.stdout.flush()

    sys.exit(0 if state.task_complete else 1)


if __name__ == "__main__":
    main()
