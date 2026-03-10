from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

load_dotenv(ROOT / ".env")

from subagent_patterns.agents import (
    build_app_builder_agent,
    build_connector_builder_agent,
)
from subagent_patterns.demo_runner import preview


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stub async cloud orchestration demo.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only.")
    return parser.parse_args()


def build_stub_run_sequence() -> list[str]:
    return [
        "Create OpenHandsCloudWorkspace",
        "Create remote app conversation",
        "Create remote connector conversation",
        "Send scoped task to each conversation",
        "Run both conversations with blocking=False",
        "Poll execution_status until both are terminal",
        "Send connector completion update into app flow",
        "Start final integration or validation conversation",
    ]


def main() -> int:
    args = parse_args()
    print(preview("cloud_async"))
    print("")
    print("Stub run sequence:")
    for index, item in enumerate(build_stub_run_sequence(), start=1):
        print(f"{index}. {item}")

    if args.dry_run:
        return 0

    missing = [name for name in ("OPENHANDS_CLOUD_API_KEY", "LLM_API_KEY") if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    build_app_builder_agent()
    build_connector_builder_agent()
    print("")
    print("Cloud worker agents built successfully. Conversation execution is intentionally deferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
