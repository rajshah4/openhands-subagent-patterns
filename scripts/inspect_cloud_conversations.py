from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openhands.sdk import Conversation, RemoteWorkspace

from subagent_patterns.agents import build_app_builder_agent
from subagent_patterns.cloud_conversations import (
    create_app_conversation,
    create_app_conversation_shell,
    get_app_conversations,
    get_v1_conversation_events,
    list_app_conversations,
    summarize_run_summary,
    wait_for_app_conversation_id,
)
from subagent_patterns.env import load_project_env


load_project_env()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect OpenHands Cloud conversations.")
    parser.add_argument("--limit", type=int, default=10, help="Number of conversations to list.")
    parser.add_argument(
        "--conversation-id",
        help="If set, fetch V1 events for this conversation.",
    )
    parser.add_argument(
        "--events-limit",
        type=int,
        default=20,
        help="Number of events to fetch when --conversation-id is set.",
    )
    parser.add_argument(
        "--run-summary",
        help="Optional run_summary.json path to compare sandbox/runtime IDs.",
    )
    parser.add_argument(
        "--create-v1-test",
        action="store_true",
        help="Create a small V1 app conversation through /api/v1/app-conversations.",
    )
    parser.add_argument(
        "--create-v1-shell",
        action="store_true",
        help="Create a minimal V1 app conversation using the empty {'request': {}} contract.",
    )
    parser.add_argument(
        "--shell-then-message",
        action="store_true",
        help="Create a V1 shell conversation, wait, then send the first message through the SDK.",
    )
    parser.add_argument(
        "--prompt",
        default="Read the repository root and reply with a one-sentence summary. Do not modify any files.",
        help="Prompt to use with --create-v1-test.",
    )
    parser.add_argument(
        "--repo",
        default="rajshah4/openhands-subagent-patterns",
        help="Repository to use with --create-v1-test.",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=15.0,
        help="Seconds to wait before sending the first message in --shell-then-message mode.",
    )
    return parser.parse_args()


def print_conversations(limit: int) -> None:
    print("V1 app conversations:")
    for item in list_app_conversations(limit=limit):
        print(
            f"- id={item.app_conversation_id} "
            f"version={item.conversation_version} "
            f"sandbox_id={item.sandbox_id} "
            f"repo={item.selected_repository} "
            f"title={item.title}"
        )


def print_events(conversation_id: str, events_limit: int) -> None:
    payload = get_v1_conversation_events(conversation_id, limit=events_limit)
    print("")
    print(f"Events for {conversation_id}:")
    print(json.dumps(payload, indent=2)[:4000])


def print_run_summary(path: Path) -> None:
    print("")
    print(f"Runtime summary from {path}:")
    print(json.dumps(summarize_run_summary(path), indent=2))


def create_v1_test(prompt: str, repo: str) -> None:
    print("")
    print("Creating V1 app conversation...")
    created = create_app_conversation(
        initial_message=prompt,
        selected_repository=repo,
    )
    print(json.dumps(created, indent=2))

    start_task_id = created.get("id")
    app_conversation_id = created.get("app_conversation_id")
    if start_task_id and not app_conversation_id:
        print("")
        print(f"Polling start task {start_task_id}...")
        task = wait_for_app_conversation_id(start_task_id)
        print(json.dumps(task, indent=2))
        app_conversation_id = task.get("app_conversation_id")

    if app_conversation_id:
        print("")
        print(f"Fetching app conversation {app_conversation_id}...")
        print(json.dumps(get_app_conversations([app_conversation_id]), indent=2))


def create_v1_shell() -> None:
    print("")
    print("Creating V1 app conversation shell...")
    created = create_app_conversation_shell()
    print(json.dumps(created, indent=2))

    start_task_id = created.get("id")
    app_conversation_id = created.get("app_conversation_id")
    if start_task_id and not app_conversation_id:
        print("")
        print(f"Polling start task {start_task_id}...")
        task = wait_for_app_conversation_id(start_task_id)
        print(json.dumps(task, indent=2))
        app_conversation_id = task.get("app_conversation_id")

    if app_conversation_id:
        print("")
        print(f"Fetching app conversation {app_conversation_id}...")
        print(json.dumps(get_app_conversations([app_conversation_id]), indent=2))


def shell_then_message(prompt: str, wait_seconds: float) -> None:
    print("")
    print("Creating V1 app conversation shell...")
    created = create_app_conversation_shell()
    print(json.dumps(created, indent=2))

    start_task_id = created.get("id")
    app_conversation_id = created.get("app_conversation_id")
    if start_task_id and not app_conversation_id:
        print("")
        print(f"Polling start task {start_task_id}...")
        task = wait_for_app_conversation_id(start_task_id)
        print(json.dumps(task, indent=2))
        app_conversation_id = task.get("app_conversation_id")

    if not app_conversation_id:
        print("")
        print("No app_conversation_id returned.")
        return

    record = get_app_conversations([app_conversation_id])[0]
    print("")
    print(f"Fetched app conversation {app_conversation_id}...")
    print(json.dumps(record, indent=2))

    print("")
    print(f"Waiting {wait_seconds:.1f}s before sending first message...")
    time.sleep(wait_seconds)

    workspace = RemoteWorkspace(
        host=record["conversation_url"].split("/api/conversations/")[0],
        api_key=record["session_api_key"],
        working_dir="/workspace/project",
    )
    conversation = Conversation(
        agent=build_app_builder_agent(),
        workspace=workspace,
        conversation_id=app_conversation_id,
        delete_on_close=False,
    )
    conversation.send_message(prompt)
    conversation.run(blocking=True, timeout=300.0)

    print("")
    print("Post-run conversation record:")
    print(json.dumps(get_app_conversations([app_conversation_id]), indent=2))

    print("")
    print("Recent V1 events:")
    print(json.dumps(get_v1_conversation_events(app_conversation_id, limit=10), indent=2)[:4000])


def main() -> int:
    args = parse_args()
    print_conversations(args.limit)
    if args.conversation_id:
        print_events(args.conversation_id, args.events_limit)
    if args.run_summary:
        print_run_summary(Path(args.run_summary))
    if args.create_v1_test:
        create_v1_test(args.prompt, args.repo)
    if args.create_v1_shell:
        create_v1_shell()
    if args.shell_then_message:
        shell_then_message(args.prompt, args.wait_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
