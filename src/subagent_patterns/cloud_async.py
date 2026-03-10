from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from openhands.sdk import Conversation, Event
from openhands.workspace import OpenHandsCloudWorkspace

from subagent_patterns.agents import (
    build_app_builder_agent,
    build_connector_builder_agent,
    build_integration_tester_agent,
)
from subagent_patterns.models import BuildRequest


DEFAULT_CLOUD_URL = "https://app.all-hands.dev"


@dataclass
class WorkerHandle:
    name: str
    workspace: OpenHandsCloudWorkspace
    conversation: Conversation
    events: list[dict]


def get_sandbox_id(workspace: OpenHandsCloudWorkspace) -> str | None:
    return getattr(workspace, "_sandbox_id", None) or workspace.sandbox_id


def ensure_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _serialize_event(event: Event) -> dict:
    payload = {"type": event.__class__.__name__}
    if hasattr(event, "source"):
        payload["source"] = getattr(event, "source")
    if hasattr(event, "message"):
        payload["message"] = getattr(event, "message")
    return payload


def _callback_collector(target: list[dict]):
    def callback(event: Event) -> None:
        target.append(_serialize_event(event))

    return callback


def create_cloud_workspace(*, keep_alive: bool = True) -> OpenHandsCloudWorkspace:
    return OpenHandsCloudWorkspace(
        cloud_api_url=os.getenv("OPENHANDS_CLOUD_API_URL", DEFAULT_CLOUD_URL),
        cloud_api_key=ensure_env("OPENHANDS_CLOUD_API_KEY"),
        keep_alive=keep_alive,
    )


def build_app_prompt(request: BuildRequest) -> str:
    return f"""
Create only these files and then stop:
- /workspace/project/app_scaffold.md
- /workspace/project/connector_contract.md
- /workspace/project/app_progress.md

Do not create source code, folders, or extra files.

User request:

{request.user_description}

A required connector may be missing: {request.missing_connector}.

Requirements:
1. `app_scaffold.md`: concise module map and app phases
2. `connector_contract.md`: exact connector methods and payload expectations
3. `app_progress.md`: list what can proceed now vs what is blocked on the connector

When those three files are written, finish immediately.
""".strip()


def build_connector_prompt(request: BuildRequest) -> str:
    return f"""
Create only these files and then stop:
- /workspace/project/connector_plan.md
- /workspace/project/connector_progress.md

Do not create source code, folders, or extra files.

Build a missing {request.missing_connector} connector for this application request:

{request.user_description}

Requirements:
1. `connector_plan.md`: concise connector design, auth, operations, and tests
2. `connector_progress.md`: what is done, assumptions, and open questions

Include an integration contract section inside `connector_plan.md`.
When both files are written, finish immediately.
""".strip()


def build_integration_prompt(request: BuildRequest) -> str:
    return f"""
Create only this file and then stop:
- /workspace/project/integration_summary.md

Read the following files if they exist:
- /workspace/project/app_scaffold.md
- /workspace/project/connector_contract.md
- /workspace/project/connector_plan.md
- /workspace/project/app_progress.md
- /workspace/project/connector_progress.md

In `integration_summary.md`, validate:
1. contract compatibility
2. expected integration points
3. remaining blockers before end-to-end testing

Do not create code or extra files. Finish immediately after writing the summary.
""".strip()


def start_worker(name: str, request: BuildRequest, *, keep_alive: bool = True) -> WorkerHandle:
    events: list[dict] = []
    workspace = create_cloud_workspace(keep_alive=keep_alive)

    if name == "app_builder":
        agent = build_app_builder_agent()
        prompt = build_app_prompt(request)
    elif name == "connector_builder":
        agent = build_connector_builder_agent()
        prompt = build_connector_prompt(request)
    else:
        raise ValueError(f"Unsupported worker: {name}")

    conversation = Conversation(
        agent=agent,
        workspace=workspace,
        callbacks=[_callback_collector(events)],
    )
    conversation.send_message(prompt)
    conversation.run(blocking=False)
    return WorkerHandle(
        name=name,
        workspace=workspace,
        conversation=conversation,
        events=events,
    )


def wait_for_workers(
    workers: list[WorkerHandle],
    *,
    poll_interval: float = 5.0,
    timeout: float = 1800.0,
) -> dict[str, str]:
    started = time.monotonic()
    final_statuses: dict[str, str] = {}

    while len(final_statuses) < len(workers):
        if time.monotonic() - started > timeout:
            raise TimeoutError(f"Timed out waiting for workers: {sorted(final_statuses)}")

        for worker in workers:
            if worker.name in final_statuses:
                continue
            status = worker.conversation.state.execution_status.value
            if status != "running":
                final_statuses[worker.name] = status
        if len(final_statuses) < len(workers):
            time.sleep(poll_interval)

    return final_statuses


def run_integration(
    request: BuildRequest,
    *,
    keep_alive: bool = True,
) -> WorkerHandle:
    events: list[dict] = []
    workspace = create_cloud_workspace(keep_alive=keep_alive)
    conversation = Conversation(
        agent=build_integration_tester_agent(),
        workspace=workspace,
        callbacks=[_callback_collector(events)],
    )
    conversation.send_message(build_integration_prompt(request))
    conversation.run(blocking=False)
    return WorkerHandle(
        name="integration_tester",
        workspace=workspace,
        conversation=conversation,
        events=events,
    )


def save_run_summary(
    *,
    output_dir: Path,
    request: BuildRequest,
    worker_statuses: dict[str, str],
    integration_status: str | None,
    workers: list[WorkerHandle],
    integration_worker: WorkerHandle | None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "request": request.model_dump(),
        "workers": {
            worker.name: {
                "conversation_id": str(worker.conversation.id),
                "sandbox_id": get_sandbox_id(worker.workspace),
                "status": worker_statuses.get(worker.name),
                "event_count": len(worker.events),
            }
            for worker in workers
        },
        "integration": (
            {
                "conversation_id": str(integration_worker.conversation.id),
                "sandbox_id": get_sandbox_id(integration_worker.workspace),
                "status": integration_status,
                "event_count": len(integration_worker.events),
            }
            if integration_worker
            else None
        ),
    }
    summary_path = output_dir / "run_summary.json"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return summary_path


def cleanup_workers(workers: list[WorkerHandle]) -> None:
    for worker in workers:
        try:
            worker.workspace.cleanup()
        except Exception:
            pass
