from __future__ import annotations

from subagent_patterns.models import BuildRequest, WorkflowSummary
from subagent_patterns.scenarios import build_summary


def render_summary(summary: WorkflowSummary) -> str:
    lines = [
        f"Option: {summary.option}",
        f"Title: {summary.title}",
        f"Constraint: {summary.constraint}",
        "Steps:",
    ]
    for index, step in enumerate(summary.steps, start=1):
        lines.append(
            f"{index}. {step.actor}: {step.action} -> {step.produces}"
        )
    return "\n".join(lines)


def preview(option: str, request: BuildRequest | None = None) -> str:
    summary = build_summary(option, request or BuildRequest())
    return render_summary(summary)
