from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from subagent_patterns.demo_runner import preview
from subagent_patterns.env import load_project_env
from subagent_patterns.sdk_conversation_orchestrator import run_sdk_conversations_demo


load_project_env()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SDK subagents over OH conversations demo.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only.")
    parser.add_argument("--run-live", action="store_true", help="Execute the V1 conversation workflow graph.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "results" / "sdk_subagents"),
        help="Directory for run outputs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(preview("sdk_subagents"))
    print("")
    print("Workflow shape:")
    print("1. The Python orchestrator defines app, connector, and integration tasks in code")
    print("2. App and connector tasks each run as V1 Cloud conversations")
    print("3. The orchestrator waits for both worker conversations to finish")
    print("4. The orchestrator materializes the integration prompt from prior outputs")
    print("5. The integration task runs as a final V1 Cloud conversation")

    if args.dry_run or not args.run_live:
        return 0

    summary_path = run_sdk_conversations_demo(output_dir=Path(args.output_dir))
    print("")
    print(f"Saved run summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
