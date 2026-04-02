#!/usr/bin/env python3
"""
android-ai-agent — run this file to start an automation task.

Usage:
    python run.py "Open Settings"
    python run.py "Open Instamart and search for milk" --steps 30
    python run.py --check
"""
import argparse
import sys

# Load .env before any other import so API keys are available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def main():
    parser = argparse.ArgumentParser(
        description="android-ai-agent: AI-powered Android automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py "Open Settings"
  python run.py "Open Instamart and add milk to cart" --steps 40
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

    from android_agent.graph.runner import run_task

    state = run_task(
        goal=args.goal,
        max_steps=args.steps,
        verbose=not args.quiet,
        device_id=args.device,
    )

    sys.exit(0 if state.task_complete else 1)


if __name__ == "__main__":
    main()
