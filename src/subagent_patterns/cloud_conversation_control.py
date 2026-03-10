from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from subagent_patterns.cloud_conversations import (
    create_app_conversation,
    extract_latest_assistant_text,
    get_app_conversations,
    wait_for_app_conversation_id,
    wait_for_conversation_terminal,
)
from subagent_patterns.models import BuildRequest


@dataclass
class ConversationRun:
    role: str
    start_task_id: str
    app_conversation_id: str
    sandbox_id: str | None
    execution_status: str
    output_text: str


def _timestamp_run_dir(output_dir: Path) -> Path:
    run_dir = output_dir / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def build_app_conversation_prompt(request: BuildRequest) -> str:
    return f"""
You are the app-builder conversation for this workflow.

Application request:
{request.user_description}

Missing connector:
{request.missing_connector}

Return concise markdown with exactly these sections:
## App Scaffold
## Connector Contract
## Work That Can Continue Now
## Work Blocked On The Connector

Use this connector-independent scope:
- {"\n- ".join(request.connector_independent_scope)}

Use this connector-dependent scope:
- {"\n- ".join(request.connector_dependent_scope)}

Do not write code. Do not use tools unless necessary. End with a short readiness note.
""".strip()


def build_connector_conversation_prompt(request: BuildRequest) -> str:
    return f"""
You are the connector-builder conversation for this workflow.

Application request:
{request.user_description}

Missing connector:
{request.missing_connector}

Return concise markdown with exactly these sections:
## Connector Plan
## Auth And Operations
## Integration Handoff
## Validation Notes

Make the handoff concrete enough that the app team can resume:
- {"\n- ".join(request.connector_dependent_scope)}

Do not write code. Do not use tools unless necessary. End with a short readiness note.
""".strip()


def build_integration_conversation_prompt(
    request: BuildRequest,
    *,
    app_output: str,
    connector_output: str,
) -> str:
    return f"""
You are the integration conversation for this workflow.

Application request:
{request.user_description}

Missing connector:
{request.missing_connector}

App conversation output:
---
{app_output}
---

Connector conversation output:
---
{connector_output}
---

Return concise markdown with exactly these sections:
## Integration Plan
## Work Now Unblocked
## Remaining Risks
## Final Recommendation

Do not write code. Keep the response concise and specific.
""".strip()


def _start_and_finish_conversation(
    *,
    role: str,
    prompt: str,
    title: str,
) -> ConversationRun:
    created = create_app_conversation(initial_message=prompt, title=title)
    start_task_id = created["id"]
    task = wait_for_app_conversation_id(start_task_id)
    app_conversation_id = task.get("app_conversation_id")
    if not app_conversation_id:
        raise RuntimeError(f"{role} did not return an app conversation id: {task}")

    terminal = wait_for_conversation_terminal(app_conversation_id)
    output_text = extract_latest_assistant_text(app_conversation_id)
    return ConversationRun(
        role=role,
        start_task_id=start_task_id,
        app_conversation_id=app_conversation_id,
        sandbox_id=task.get("sandbox_id"),
        execution_status=str(terminal.get("execution_status")),
        output_text=output_text,
    )


def run_cloud_conversations_demo(
    *,
    output_dir: Path,
    request: BuildRequest | None = None,
) -> Path:
    request = request or BuildRequest()
    run_dir = _timestamp_run_dir(output_dir)

    app_run = _start_and_finish_conversation(
        role="app_builder",
        prompt=build_app_conversation_prompt(request),
        title=f"{request.app_name} app builder",
    )
    connector_run = _start_and_finish_conversation(
        role="connector_builder",
        prompt=build_connector_conversation_prompt(request),
        title=f"{request.app_name} connector builder",
    )
    integration_run = _start_and_finish_conversation(
        role="integration_tester",
        prompt=build_integration_conversation_prompt(
            request,
            app_output=app_run.output_text,
            connector_output=connector_run.output_text,
        ),
        title=f"{request.app_name} integration",
    )

    summary = {
        "request": request.model_dump(),
        "runs": {
            "app_builder": app_run.__dict__,
            "connector_builder": connector_run.__dict__,
            "integration_tester": integration_run.__dict__,
        },
        "urls": {
            name: get_app_conversations([run.app_conversation_id])[0].get("conversation_url")
            for name, run in {
                "app_builder": app_run,
                "connector_builder": connector_run,
                "integration_tester": integration_run,
            }.items()
        },
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary_path
