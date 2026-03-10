from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from subagent_patterns.cloud_conversation_control import (
    ConversationRun,
    build_app_conversation_prompt,
    build_connector_conversation_prompt,
    build_integration_conversation_prompt,
)
from subagent_patterns.cloud_conversations import (
    create_app_conversation,
    extract_latest_assistant_text,
    get_app_conversations,
    wait_for_app_conversation_id,
    wait_for_conversation_terminal,
)
from subagent_patterns.models import BuildRequest


@dataclass
class ConversationTask:
    name: str
    title: str
    prompt: str
    depends_on: list[str] = field(default_factory=list)


def _timestamp_run_dir(output_dir: Path) -> Path:
    run_dir = output_dir / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


class SDKConversationOrchestrator:
    def __init__(self, request: BuildRequest):
        self.request = request
        self.completed: dict[str, ConversationRun] = {}

    def build_task_graph(self) -> list[ConversationTask]:
        request = self.request
        return [
            ConversationTask(
                name="app_builder",
                title=f"{request.app_name} sdk app builder",
                prompt=build_app_conversation_prompt(request),
            ),
            ConversationTask(
                name="connector_builder",
                title=f"{request.app_name} sdk connector builder",
                prompt=build_connector_conversation_prompt(request),
            ),
            ConversationTask(
                name="integration_tester",
                title=f"{request.app_name} sdk integration",
                prompt="__DEFERRED__",
                depends_on=["app_builder", "connector_builder"],
            ),
        ]

    def _materialize_prompt(self, task: ConversationTask) -> str:
        if task.name != "integration_tester":
            return task.prompt
        app_output = self.completed["app_builder"].output_text
        connector_output = self.completed["connector_builder"].output_text
        return build_integration_conversation_prompt(
            self.request,
            app_output=app_output,
            connector_output=connector_output,
        )

    def _run_task(self, task: ConversationTask) -> ConversationRun:
        prompt = self._materialize_prompt(task)
        created = create_app_conversation(initial_message=prompt, title=task.title)
        start_task_id = created["id"]
        task_status = wait_for_app_conversation_id(start_task_id)
        app_conversation_id = task_status.get("app_conversation_id")
        if not app_conversation_id:
            raise RuntimeError(f"{task.name} failed to create conversation: {task_status}")
        terminal = wait_for_conversation_terminal(app_conversation_id)
        return ConversationRun(
            role=task.name,
            start_task_id=start_task_id,
            app_conversation_id=app_conversation_id,
            sandbox_id=task_status.get("sandbox_id"),
            execution_status=str(terminal.get("execution_status")),
            output_text=extract_latest_assistant_text(app_conversation_id),
        )

    def run(self) -> dict[str, ConversationRun]:
        for task in self.build_task_graph():
            missing = [name for name in task.depends_on if name not in self.completed]
            if missing:
                raise RuntimeError(f"Task {task.name} missing dependencies: {missing}")
            self.completed[task.name] = self._run_task(task)
        return self.completed


def run_sdk_conversations_demo(
    *,
    output_dir: Path,
    request: BuildRequest | None = None,
) -> Path:
    request = request or BuildRequest()
    run_dir = _timestamp_run_dir(output_dir)
    orchestrator = SDKConversationOrchestrator(request)
    completed = orchestrator.run()

    summary = {
        "request": request.model_dump(),
        "pattern": "sdk_conversations",
        "runs": {name: run.__dict__ for name, run in completed.items()},
        "urls": {
            name: get_app_conversations([run.app_conversation_id])[0].get("conversation_url")
            for name, run in completed.items()
        },
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary_path
