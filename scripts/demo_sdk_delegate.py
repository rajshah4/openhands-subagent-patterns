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
from subagent_patterns.sdk_delegate import run_sdk_delegate_demo


load_project_env()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SDK delegate demo.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only.")
    parser.add_argument("--run-live", action="store_true", help="Execute the delegate workflow locally.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "results" / "sdk_delegate"),
        help="Directory for run outputs.",
    )
    parser.add_argument("--keep-workspace", action="store_true", help="Keep the local workspace directory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(preview("sdk_delegate"))
    print("")
    print("Stub wiring:")
    print("- orchestrator agent includes DelegateTool")
    print("- connector_builder and app_builder are registered as sub-agents")
    print("- integration_tester runs after delegate returns")

    if args.dry_run or not args.run_live:
        return 0

    result = run_sdk_delegate_demo(
        output_dir=Path(args.output_dir),
        keep_workspace=args.keep_workspace,
    )
    print("")
    print(f"Run directory: {result.run_dir}")
    print(f"Duration: {result.duration_seconds}s")
    print("Artifacts:")
    for name in sorted(result.artifacts):
        print(f"- {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
