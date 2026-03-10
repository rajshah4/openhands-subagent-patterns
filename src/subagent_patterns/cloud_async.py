from __future__ import annotations

import json
import os
import shlex
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openhands.sdk import Conversation, Event
from openhands.workspace import OpenHandsCloudWorkspace

from subagent_patterns.agents import (
    build_app_builder_agent,
    build_connector_builder_agent,
    build_integration_tester_agent,
)
from subagent_patterns.models import BuildRequest


DEFAULT_CLOUD_URL = "https://app.all-hands.dev"
REMOTE_PROJECT_DIR = "/workspace/project"

EXPECTED_ARTIFACTS = {
    "app_builder": [
        f"{REMOTE_PROJECT_DIR}/app_scaffold.md",
        f"{REMOTE_PROJECT_DIR}/connector_contract.md",
        f"{REMOTE_PROJECT_DIR}/app_progress.md",
    ],
    "connector_builder": [
        f"{REMOTE_PROJECT_DIR}/connector_plan.md",
        f"{REMOTE_PROJECT_DIR}/connector_progress.md",
    ],
    "integration_tester": [
        f"{REMOTE_PROJECT_DIR}/integration_summary.md",
    ],
}


@dataclass
class WorkerHandle:
    name: str
    workspace: OpenHandsCloudWorkspace
    conversation: Conversation
    events: list[dict]


@dataclass
class WorkerCompletion:
    status: str
    artifacts_ready: bool
    artifacts: list[str]
    downloaded_artifacts: list[str]


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


def worker_artifacts_ready(worker: WorkerHandle) -> tuple[bool, list[str]]:
    expected = EXPECTED_ARTIFACTS[worker.name]
    present: list[str] = []
    for remote_path in expected:
        result = worker.workspace.execute_command(
            f"test -f {shlex.quote(remote_path)}",
            timeout=10.0,
        )
        if result.exit_code == 0:
            present.append(remote_path)
    return len(present) == len(expected), present


def download_worker_artifacts(
    worker: WorkerHandle,
    remote_paths: list[str],
    *,
    base_dir: Path,
) -> list[str]:
    downloaded: list[str] = []
    worker_dir = base_dir / worker.name
    worker_dir.mkdir(parents=True, exist_ok=True)
    for remote_path in remote_paths:
        local_path = worker_dir / Path(remote_path).name
        worker.workspace.file_download(remote_path, local_path)
        downloaded.append(str(local_path))
    return downloaded


def upload_seed_artifacts(
    workspace: OpenHandsCloudWorkspace,
    artifact_paths: list[str],
) -> list[str]:
    uploaded: list[str] = []
    for local_path in artifact_paths:
        destination_path = f"{REMOTE_PROJECT_DIR}/{Path(local_path).name}"
        workspace.file_upload(local_path, destination_path)
        uploaded.append(destination_path)
    return uploaded


def wait_for_workers(
    workers: list[WorkerHandle],
    *,
    output_dir: Path,
    poll_interval: float = 5.0,
    timeout: float = 1800.0,
) -> dict[str, WorkerCompletion]:
    started = time.monotonic()
    final_statuses: dict[str, WorkerCompletion] = {}
    artifacts_dir = output_dir / "artifacts"

    while len(final_statuses) < len(workers):
        if time.monotonic() - started > timeout:
            raise TimeoutError(f"Timed out waiting for workers: {sorted(final_statuses)}")

        for worker in workers:
            if worker.name in final_statuses:
                continue
            status = worker.conversation.state.execution_status.value
            artifacts_ready, present = worker_artifacts_ready(worker)
            if present:
                print(
                    f"[poll] {worker.name}: status={status}, "
                    f"artifacts={len(present)}/{len(EXPECTED_ARTIFACTS[worker.name])}"
                )
            if artifacts_ready:
                downloaded = download_worker_artifacts(
                    worker,
                    present,
                    base_dir=artifacts_dir,
                )
                final_statuses[worker.name] = WorkerCompletion(
                    status=status,
                    artifacts_ready=True,
                    artifacts=present,
                    downloaded_artifacts=downloaded,
                )
            elif status in {"error", "stuck"}:
                final_statuses[worker.name] = WorkerCompletion(
                    status=status,
                    artifacts_ready=False,
                    artifacts=present,
                    downloaded_artifacts=[],
                )
        if len(final_statuses) < len(workers):
            time.sleep(poll_interval)

    return final_statuses


def run_integration(
    request: BuildRequest,
    source_artifacts: list[str],
    *,
    keep_alive: bool = True,
) -> WorkerHandle:
    events: list[dict] = []
    workspace = create_cloud_workspace(keep_alive=keep_alive)
    uploaded = upload_seed_artifacts(workspace, source_artifacts)
    if uploaded:
        events.append({"type": "SeedArtifactsUploaded", "artifacts": uploaded})
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
    worker_statuses: dict[str, WorkerCompletion],
    integration_status: WorkerCompletion | None,
    workers: list[WorkerHandle],
    integration_worker: WorkerHandle | None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "request": request.model_dump(),
        "workers": {
            worker.name: {
                "conversation_id": str(worker.conversation.id),
                "sandbox_id": get_sandbox_id(worker.workspace),
                "status": worker_statuses[worker.name].status,
                "artifacts_ready": worker_statuses[worker.name].artifacts_ready,
                "artifacts": worker_statuses[worker.name].artifacts,
                "downloaded_artifacts": worker_statuses[worker.name].downloaded_artifacts,
                "event_count": len(worker.events),
            }
            for worker in workers
        },
        "integration": (
            {
                "conversation_id": str(integration_worker.conversation.id),
                "sandbox_id": get_sandbox_id(integration_worker.workspace),
                "status": integration_status.status,
                "artifacts_ready": integration_status.artifacts_ready,
                "artifacts": integration_status.artifacts,
                "downloaded_artifacts": integration_status.downloaded_artifacts,
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
