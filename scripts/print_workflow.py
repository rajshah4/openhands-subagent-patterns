from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from subagent_patterns.demo_runner import preview


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print the workflow mental model.")
    parser.add_argument(
        "--option",
        choices=["sdk_delegate", "cloud_async", "github_control"],
        required=True,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(preview(args.option))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
