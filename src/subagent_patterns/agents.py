from __future__ import annotations

import os

from pydantic import SecretStr

from openhands.sdk import Agent, AgentContext, LLM, Tool
from openhands.sdk.subagent.registry import register_agent_if_absent
from openhands.tools.delegate import DelegateTool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool

from subagent_patterns.skills import load_skill


def build_llm(usage_id: str) -> LLM:
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OH_API_KEY")
    model = os.getenv("LLM_MODEL", "openhands/claude-sonnet-4-5-20250929")
    if not model.startswith("openhands/"):
        model = "openhands/claude-sonnet-4-5-20250929"
    return LLM(
        usage_id=usage_id,
        model=model,
        api_key=SecretStr(api_key) if api_key else None,
        base_url=None,
    )


def build_agent(
    *,
    usage_id: str,
    tools: list[Tool],
    skill_names: list[str],
    system_message_suffix: str,
) -> Agent:
    context = AgentContext(
        system_message_suffix=system_message_suffix,
        skills=[load_skill(name) for name in skill_names],
    )
    return Agent(
        llm=build_llm(usage_id),
        tools=tools,
        agent_context=context,
    )


def build_orchestrator_agent() -> Agent:
    return build_agent(
        usage_id="subagent-patterns-orchestrator",
        tools=[
            Tool(name=DelegateTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
        skill_names=["app_builder"],
        system_message_suffix=(
            "You are the top-level orchestrator. Split work into "
            "connector-independent and connector-dependent branches."
        ),
    )


def build_app_builder_agent() -> Agent:
    return build_agent(
        usage_id="subagent-patterns-app-builder",
        tools=[
            Tool(
                name=TerminalTool.name,
                params={"terminal_type": "subprocess", "shell_path": "/bin/bash"},
            ),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
        skill_names=["app_builder"],
        system_message_suffix="Focus on application scaffolding and integration boundaries.",
    )


def build_connector_builder_agent() -> Agent:
    return build_agent(
        usage_id="subagent-patterns-connector-builder",
        tools=[
            Tool(
                name=TerminalTool.name,
                params={"terminal_type": "subprocess", "shell_path": "/bin/bash"},
            ),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
        skill_names=["connector_builder"],
        system_message_suffix="Build missing connectors with clean contracts and tests.",
    )


def build_integration_tester_agent() -> Agent:
    return build_agent(
        usage_id="subagent-patterns-integration-tester",
        tools=[
            Tool(
                name=TerminalTool.name,
                params={"terminal_type": "subprocess", "shell_path": "/bin/bash"},
            ),
            Tool(name=FileEditorTool.name),
            Tool(name=TaskTrackerTool.name),
        ],
        skill_names=["integration_tester"],
        system_message_suffix="Integrate completed artifacts and validate end-to-end behavior.",
    )


def register_demo_subagents() -> list[str]:
    registered: list[str] = []

    if register_agent_if_absent(
        "subagent_patterns_app_builder",
        lambda llm: build_app_builder_agent().model_copy(update={"llm": llm}),
        "Builds the app sections that do not depend on the missing connector.",
    ):
        registered.append("subagent_patterns_app_builder")

    if register_agent_if_absent(
        "subagent_patterns_connector_builder",
        lambda llm: build_connector_builder_agent().model_copy(update={"llm": llm}),
        "Builds a missing connector and returns integration notes.",
    ):
        registered.append("subagent_patterns_connector_builder")

    if register_agent_if_absent(
        "subagent_patterns_integration_tester",
        lambda llm: build_integration_tester_agent().model_copy(update={"llm": llm}),
        "Integrates finished artifacts and validates the final app flow.",
    ):
        registered.append("subagent_patterns_integration_tester")

    return registered
