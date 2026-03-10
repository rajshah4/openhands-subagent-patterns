from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from subagent_patterns.env import require_env


DEFAULT_CLOUD_URL = "https://app.all-hands.dev"


@dataclass
class AppConversationRecord:
    app_conversation_id: str
    title: str
    status: str | None
    conversation_version: str | None
    selected_repository: str | None
    selected_branch: str | None
    sandbox_id: str | None
    trigger: str | None
    raw: dict[str, Any]


def _conversation_api_key() -> str:
    for name in ("OPENHANDS_API_KEY", "OH_API_KEY"):
        value = require_env(name) if _has_env(name) else None
        if value:
            return value
    raise RuntimeError("Missing required environment variable: OPENHANDS_API_KEY or OH_API_KEY")


def _has_env(name: str) -> bool:
    try:
        return bool(require_env(name))
    except RuntimeError:
        return False


def _cloud_request(
    path: str,
    *,
    method: str = "GET",
    params: dict[str, str | int] | None = None,
    payload: dict[str, Any] | None = None,
    cloud_api_url: str = DEFAULT_CLOUD_URL,
) -> Any:
    api_key = _conversation_api_key()
    base = cloud_api_url.rstrip("/")
    url = f"{base}{path}"
    if params:
        url = f"{url}?{urlencode(params, doseq=True)}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        method=method,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30.0) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloud API request failed: {exc.code} {detail}") from exc


def list_app_conversations(
    *,
    limit: int = 20,
    cloud_api_url: str = DEFAULT_CLOUD_URL,
) -> list[AppConversationRecord]:
    payload = _cloud_request(
        "/api/v1/app-conversations/search",
        params={"limit": limit},
        cloud_api_url=cloud_api_url,
    )
    results = payload.get("results", payload if isinstance(payload, list) else [])
    conversations: list[AppConversationRecord] = []
    for item in results:
        conversation_id = item.get("app_conversation_id") or item.get("id")
        if not conversation_id:
            continue
        conversations.append(
            AppConversationRecord(
                app_conversation_id=conversation_id,
                title=item.get("title") or "",
                status=item.get("status"),
                conversation_version=item.get("conversation_version"),
                selected_repository=item.get("selected_repository"),
                selected_branch=item.get("selected_branch"),
                sandbox_id=item.get("sandbox_id"),
                trigger=item.get("trigger"),
                raw=item,
            )
        )
    return conversations


def get_app_conversations(
    ids: list[str],
    *,
    cloud_api_url: str = DEFAULT_CLOUD_URL,
) -> list[dict[str, Any]]:
    if not ids:
        return []
    return _cloud_request(
        "/api/v1/app-conversations",
        params={"ids": ids},
        cloud_api_url=cloud_api_url,
    )


def get_start_tasks(
    ids: list[str],
    *,
    cloud_api_url: str = DEFAULT_CLOUD_URL,
) -> list[dict[str, Any]]:
    if not ids:
        return []
    return _cloud_request(
        "/api/v1/app-conversations/start-tasks",
        params={"ids": ids},
        cloud_api_url=cloud_api_url,
    )


def create_app_conversation(
    *,
    initial_message: str,
    selected_repository: str | None = None,
    selected_branch: str | None = None,
    title: str | None = None,
    run: bool = True,
    cloud_api_url: str = DEFAULT_CLOUD_URL,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "initial_message": {
            "role": "user",
            "content": [{"type": "text", "text": initial_message}],
            "run": run,
        }
    }
    if selected_repository:
        payload["selected_repository"] = selected_repository
    if selected_branch:
        payload["selected_branch"] = selected_branch
    if title:
        payload["title"] = title
    return _cloud_request(
        "/api/v1/app-conversations",
        method="POST",
        payload=payload,
        cloud_api_url=cloud_api_url,
    )


def create_app_conversation_shell(
    *,
    cloud_api_url: str = DEFAULT_CLOUD_URL,
) -> dict[str, Any]:
    return _cloud_request(
        "/api/v1/app-conversations",
        method="POST",
        payload={"request": {}},
        cloud_api_url=cloud_api_url,
    )


def wait_for_app_conversation_id(
    start_task_id: str,
    *,
    timeout: float = 120.0,
    poll_interval: float = 3.0,
    cloud_api_url: str = DEFAULT_CLOUD_URL,
) -> dict[str, Any]:
    started = time.monotonic()
    while time.monotonic() - started <= timeout:
        tasks = get_start_tasks([start_task_id], cloud_api_url=cloud_api_url)
        task = tasks[0] if tasks else {}
        app_conversation_id = task.get("app_conversation_id")
        status = str(task.get("status", "")).upper()
        if app_conversation_id or status in {"READY", "FAILED", "ERROR", "STOPPED"}:
            return task
        time.sleep(poll_interval)
    raise TimeoutError(f"Timed out waiting for start task {start_task_id}")


def get_v1_conversation_events(
    app_conversation_id: str,
    *,
    limit: int = 100,
    page_id: str | None = None,
    cloud_api_url: str = DEFAULT_CLOUD_URL,
) -> dict[str, Any]:
    params: dict[str, str | int] = {"limit": limit}
    if page_id:
        params["page_id"] = page_id
    return _cloud_request(
        f"/api/v1/conversation/{app_conversation_id}/events/search",
        params=params,
        cloud_api_url=cloud_api_url,
    )


def wait_for_conversation_terminal(
    app_conversation_id: str,
    *,
    timeout: float = 600.0,
    poll_interval: float = 5.0,
    cloud_api_url: str = DEFAULT_CLOUD_URL,
) -> dict[str, Any]:
    started = time.monotonic()
    while time.monotonic() - started <= timeout:
        items = get_app_conversations([app_conversation_id], cloud_api_url=cloud_api_url)
        item = items[0] if items else {}
        status = str(item.get("execution_status", "")).lower()
        if status in {"finished", "error", "stuck", "stopped"}:
            return item
        time.sleep(poll_interval)
    raise TimeoutError(f"Timed out waiting for conversation {app_conversation_id}")


def extract_latest_assistant_text(
    app_conversation_id: str,
    *,
    limit: int = 100,
    cloud_api_url: str = DEFAULT_CLOUD_URL,
) -> str:
    payload = get_v1_conversation_events(
        app_conversation_id,
        limit=limit,
        cloud_api_url=cloud_api_url,
    )
    items = payload.get("items", [])
    for item in reversed(items):
        llm_message = item.get("llm_message") or {}
        if item.get("source") != "agent":
            continue
        if llm_message.get("role") != "assistant":
            continue
        texts = [
            block.get("text", "")
            for block in llm_message.get("content", [])
            if block.get("type") == "text"
        ]
        if texts:
            return "\n".join(texts).strip()
    return ""


def summarize_run_summary(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    workers = payload.get("workers", {})
    summary = {
        "workers": {
            name: {
                "conversation_id": item.get("conversation_id"),
                "sandbox_id": item.get("sandbox_id"),
                "status": item.get("status"),
            }
            for name, item in workers.items()
        },
        "integration": payload.get("integration"),
    }
    return summary
