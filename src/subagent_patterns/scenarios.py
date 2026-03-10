from __future__ import annotations

from subagent_patterns.models import BuildRequest, WorkflowSummary, WorkflowStep


def build_summary(option: str, request: BuildRequest) -> WorkflowSummary:
    if option == "sdk_delegate":
        return WorkflowSummary(
            option="sdk_delegate",
            title="SDK Delegate: parent blocks while children run",
            constraint="The orchestrator can only plan, delegate, then resume.",
            steps=[
                WorkflowStep(
                    actor="orchestrator",
                    action="analyzes app request and identifies missing connector",
                    produces=f"work split for {request.missing_connector}",
                ),
                WorkflowStep(
                    actor="connector_builder",
                    action="builds the missing connector in a delegated branch",
                    produces="connector code and usage notes",
                ),
                WorkflowStep(
                    actor="app_builder",
                    action="builds connector-independent app scaffolding in parallel",
                    produces="partial application skeleton",
                ),
                WorkflowStep(
                    actor="integration_tester",
                    action="integrates connector and runs validation",
                    produces="integration report",
                ),
            ],
        )

    if option == "cloud_async":
        return WorkflowSummary(
            option="cloud_async",
            title="Cloud Async: external orchestrator manages multiple conversations",
            constraint="Concurrency is owned by Python orchestration, not a single agent loop.",
            steps=[
                WorkflowStep(
                    actor="python_orchestrator",
                    action="starts isolated cloud conversations for app and connector work",
                    produces="two active remote conversations",
                ),
                WorkflowStep(
                    actor="connector_builder",
                    action="creates the connector artifact independently",
                    produces="connector package and test evidence",
                ),
                WorkflowStep(
                    actor="app_builder",
                    action="continues on connector-independent implementation",
                    produces="application branch ready for integration",
                ),
                WorkflowStep(
                    actor="python_orchestrator",
                    action="injects the connector result back into app and test flow",
                    produces="merged integration task",
                ),
            ],
        )

    if option == "github_control":
        return WorkflowSummary(
            option="github_control",
            title="GitHub Control Plane: repo artifacts coordinate the workflow",
            constraint="Context is carried by issues, PRs, comments, and repo state.",
            steps=[
                WorkflowStep(
                    actor="app_builder",
                    action="opens a missing-connector issue with scoped requirements",
                    produces="connector issue",
                ),
                WorkflowStep(
                    actor="connector_builder",
                    action="responds to the issue and opens a PR",
                    produces="connector PR",
                ),
                WorkflowStep(
                    actor="reviewer_or_bot",
                    action="signals readiness via merge or @OpenHands comment",
                    produces="integration trigger",
                ),
                WorkflowStep(
                    actor="integration_tester",
                    action="pulls the PR state into final validation",
                    produces="release-ready app branch",
                ),
            ],
        )

    raise ValueError(f"Unsupported workflow option: {option}")
