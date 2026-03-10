from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from openhands.sdk.conversation.impl.local_conversation import LocalConversation
from openhands.tools.delegate.definition import DelegateAction
from openhands.tools.delegate.impl import DelegateExecutor

from subagent_patterns.agents import (
    build_integration_tester_agent,
    build_orchestrator_agent,
    register_demo_subagents,
)
from subagent_patterns.models import BuildRequest


@dataclass
class DelegateRunResult:
    run_dir: Path
    workspace_dir: Path
    spawn_result: str
    delegate_result: str
    integration_spawn_result: str
    integration_result: str
    artifacts: dict[str, str]
    duration_seconds: float


def _timestamp_run_dir(output_dir: Path) -> Path:
    run_dir = output_dir / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _read_if_exists(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def run_sdk_delegate_demo(
    *,
    output_dir: Path,
    request: BuildRequest | None = None,
    keep_workspace: bool = True,
) -> DelegateRunResult:
    started = time.perf_counter()
    request = request or BuildRequest()
    run_dir = _timestamp_run_dir(output_dir)
    workspace_dir = run_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    fake_home = run_dir / "home"
    fake_home.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(fake_home)

    register_demo_subagents()
    conversation = LocalConversation(
        agent=build_orchestrator_agent(),
        workspace=str(workspace_dir),
    )
    delegate_executor = DelegateExecutor(max_children=5)

    spawn_obs = delegate_executor(
        DelegateAction(
            command="spawn",
            ids=["app_builder", "connector_builder"],
            agent_types=[
                "subagent_patterns_app_builder",
                "subagent_patterns_connector_builder",
            ],
        ),
        conversation,
    )

    delegate_obs = delegate_executor(
        DelegateAction(
            command="delegate",
            tasks={
                "app_builder": (
                    "Create app_scaffold.md and connector_contract.md in the workspace. "
                    f"Base them on this request: {request.user_description}. "
                    f"State that the missing connector is {request.missing_connector}. "
                    "Keep the files concise and specific."
                ),
                "connector_builder": (
                    "Create connector_plan.md in the workspace. "
                    f"Design a missing {request.missing_connector} connector for this request: "
                    f"{request.user_description}. Include auth, core operations, and test notes."
                ),
            },
        ),
        conversation,
    )

    integration_spawn_obs = delegate_executor(
        DelegateAction(
            command="spawn",
            ids=["integration_tester"],
            agent_types=["subagent_patterns_integration_tester"],
        ),
        conversation,
    )

    integration_obs = delegate_executor(
        DelegateAction(
            command="delegate",
            tasks={
                "integration_tester": (
                    "Read app_scaffold.md, connector_contract.md, and connector_plan.md from the "
                    "workspace. Create integration_summary.md that explains how the connector "
                    "would be integrated and lists any remaining blockers."
                )
            },
        ),
        conversation,
    )

    artifact_paths = {
        "app_scaffold": workspace_dir / "app_scaffold.md",
        "connector_contract": workspace_dir / "connector_contract.md",
        "connector_plan": workspace_dir / "connector_plan.md",
        "integration_summary": workspace_dir / "integration_summary.md",
    }
    artifacts = {name: _read_if_exists(path) for name, path in artifact_paths.items()}
    missing = [name for name, content in artifacts.items() if not content.strip()]
    if missing:
        raise RuntimeError(f"SDK delegate run did not produce expected artifacts: {missing}")

    summary = {
        "request": request.model_dump(),
        "spawn_result": spawn_obs.content[0].text,
        "delegate_result": delegate_obs.content[0].text,
        "integration_spawn_result": integration_spawn_obs.content[0].text,
        "integration_result": integration_obs.content[0].text,
        "artifacts": {name: str(path) for name, path in artifact_paths.items()},
        "duration_seconds": round(time.perf_counter() - started, 2),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )

    if not keep_workspace:
        snapshot_dir = run_dir / "workspace_snapshot"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        for name, path in artifact_paths.items():
            shutil.copy2(path, snapshot_dir / path.name)
        shutil.rmtree(workspace_dir)

    return DelegateRunResult(
        run_dir=run_dir,
        workspace_dir=workspace_dir,
        spawn_result=spawn_obs.content[0].text,
        delegate_result=delegate_obs.content[0].text,
        integration_spawn_result=integration_spawn_obs.content[0].text,
        integration_result=integration_obs.content[0].text,
        artifacts=artifacts,
        duration_seconds=round(time.perf_counter() - started, 2),
    )
