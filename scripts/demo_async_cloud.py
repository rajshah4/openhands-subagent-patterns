from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from subagent_patterns.demo_runner import preview
from subagent_patterns.cloud_async import (
    cleanup_workers,
    run_integration,
    save_run_summary,
    start_worker,
    wait_for_workers,
)
from subagent_patterns.env import load_project_env
from subagent_patterns.models import BuildRequest


load_project_env()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stub async cloud orchestration demo.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only.")
    parser.add_argument("--run-live", action="store_true", help="Execute real cloud conversations.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "results" / "cloud_async"),
        help="Directory for summary artifacts.",
    )
    parser.add_argument("--keep-alive", action="store_true", help="Keep sandboxes alive after the run.")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Polling interval in seconds.")
    parser.add_argument("--timeout", type=float, default=1800.0, help="Timeout in seconds.")
    return parser.parse_args()


def build_stub_run_sequence() -> list[str]:
    return [
        "Create OpenHandsCloudWorkspace",
        "Create remote app conversation",
        "Create remote connector conversation",
        "Send scoped task to each conversation",
        "Run both conversations with blocking=False",
        "Poll every few seconds for status and required artifacts",
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

    if args.dry_run or not args.run_live:
        return 0

    request = BuildRequest()
    workers = []
    integration_worker = None
    try:
        workers = [
            start_worker("app_builder", request, keep_alive=args.keep_alive),
            start_worker("connector_builder", request, keep_alive=args.keep_alive),
        ]
        statuses = wait_for_workers(
            workers,
            output_dir=Path(args.output_dir),
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
        print("")
        print("Worker statuses:")
        for name, completion in statuses.items():
            print(f"- {name}: status={completion.status}, artifacts_ready={completion.artifacts_ready}")

        integration_inputs: list[str] = []
        for completion in statuses.values():
            integration_inputs.extend(completion.downloaded_artifacts)

        time.sleep(1)
        integration_worker = run_integration(
            request,
            integration_inputs,
            keep_alive=args.keep_alive,
        )
        integration_statuses = wait_for_workers(
            [integration_worker],
            output_dir=Path(args.output_dir),
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
        integration_status = integration_statuses["integration_tester"]
        print(
            "- integration_tester: "
            f"status={integration_status.status}, artifacts_ready={integration_status.artifacts_ready}"
        )

        summary_path = save_run_summary(
            output_dir=Path(args.output_dir),
            request=request,
            worker_statuses=statuses,
            integration_status=integration_status,
            workers=workers,
            integration_worker=integration_worker,
        )
        print("")
        print(f"Saved run summary to {summary_path}")
    finally:
        if not args.keep_alive:
            cleanup_workers(workers + ([integration_worker] if integration_worker else []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
