from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from subagent_patterns.cloud_conversation_control import run_cloud_conversations_demo
from subagent_patterns.demo_runner import preview
from subagent_patterns.env import load_project_env


load_project_env()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OH conversations control-surface demo.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only.")
    parser.add_argument("--run-live", action="store_true", help="Execute real V1 app conversations.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "results" / "oh_conversations"),
        help="Directory for run outputs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(preview("oh_conversations"))
    print("")
    print("Workflow shape:")
    print("1. Start an app-builder V1 conversation")
    print("2. Start a connector-builder V1 conversation")
    print("3. Poll both Cloud conversations to terminal state")
    print("4. Extract the final assistant output from each conversation")
    print("5. Start a third integration conversation with those outputs")

    if args.dry_run or not args.run_live:
        return 0

    summary_path = run_cloud_conversations_demo(output_dir=Path(args.output_dir))
    print("")
    print(f"Saved run summary to {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
