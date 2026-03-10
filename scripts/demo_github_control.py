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
    parser = argparse.ArgumentParser(description="Stub GitHub control-plane demo.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only.")
    return parser.parse_args()


def main() -> int:
    parse_args()
    print(preview("github_control"))
    print("")
    print("Stub repo events:")
    print("1. Main workflow opens issue: missing salesforce connector")
    print("2. @OpenHands comment triggers connector builder skill set")
    print("3. Connector branch becomes a PR")
    print("4. Merge or @OpenHands on PR triggers integration")
    print("5. Final validation comments summarize release readiness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
