from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


WorkflowOption = Literal["sdk_delegate", "cloud_async", "github_control"]


class BuildRequest(BaseModel):
    app_name: str = Field(default="subagent-demo-app")
    user_description: str = Field(
        default=(
            "Build a lead-management app with a CRM sync, approval flow, and "
            "a dashboard for sales ops."
        )
    )
    missing_connector: str = Field(default="salesforce")


class WorkflowStep(BaseModel):
    actor: str
    action: str
    produces: str


class WorkflowSummary(BaseModel):
    option: WorkflowOption
    title: str
    constraint: str
    steps: list[WorkflowStep]
