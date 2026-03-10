from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


WorkflowOption = Literal[
    "github_control",
    "oh_conversations",
    "sdk_subagents",
    "cloud_async",
]


class BuildRequest(BaseModel):
    app_name: str = Field(default="subagent-demo-app")
    user_description: str = Field(
        default=(
            "Build a lead-management app with a CRM sync, approval flow, and "
            "a dashboard for sales ops."
        )
    )
    missing_connector: str = Field(default="salesforce")
    connector_independent_scope: list[str] = Field(
        default_factory=lambda: [
            "dashboard and navigation shell",
            "approval workflow screens",
            "lead intake forms",
            "user and role model",
        ]
    )
    connector_dependent_scope: list[str] = Field(
        default_factory=lambda: [
            "CRM contact sync",
            "opportunity writeback",
            "connector-backed smoke tests",
        ]
    )


class WorkflowStep(BaseModel):
    actor: str
    action: str
    produces: str


class WorkflowSummary(BaseModel):
    option: WorkflowOption
    title: str
    constraint: str
    steps: list[WorkflowStep]
