from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from subagent_patterns.demo_runner import preview
from subagent_patterns.github_control import run_github_control_demo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GitHub control-plane demo.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only.")
    parser.add_argument("--run-live", action="store_true", help="Execute the GitHub issue/PR flow.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "results" / "github_control"),
        help="Directory for run outputs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(preview("github_control"))
    print("")
    print("Workflow shape:")
    print("1. App workflow opens an issue for the missing connector and blocked work")
    print("2. @OpenHands comment triggers the connector builder branch")
    print("3. Connector branch becomes a PR with a handoff artifact")
    print("4. Merge or @OpenHands on PR triggers integration")
    print("5. Final validation comments summarize what unblocked app work can ship")

    if args.dry_run or not args.run_live:
        return 0

    result = run_github_control_demo(output_dir=Path(args.output_dir))
    print("")
    print(f"Issue: {result.issue_url}")
    print(f"PR: {result.pr_url}")
    print(f"Branch: {result.branch_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
