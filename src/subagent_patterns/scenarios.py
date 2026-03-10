from __future__ import annotations

from subagent_patterns.models import BuildRequest, WorkflowSummary, WorkflowStep


def build_summary(option: str, request: BuildRequest) -> WorkflowSummary:
    if option == "github_control":
        return WorkflowSummary(
            option="github_control",
            title="GitHub Control Plane: repo artifacts coordinate the workflow",
            constraint="Context is carried by issues, PRs, comments, and repo state.",
            steps=[
                WorkflowStep(
                    actor="app_builder",
                    action="opens a missing-connector issue with scoped requirements",
                    produces="connector issue with contract, blocked work, and acceptance criteria",
                ),
                WorkflowStep(
                    actor="connector_builder",
                    action="responds to the issue and opens a PR",
                    produces="connector PR with implementation notes and integration handoff",
                ),
                WorkflowStep(
                    actor="reviewer_or_bot",
                    action="signals readiness via merge or @OpenHands comment",
                    produces="integration trigger",
                ),
                WorkflowStep(
                    actor="integration_tester",
                    action="pulls the PR state into final validation",
                    produces="release-ready app branch and final validation summary",
                ),
            ],
        )

    if option == "oh_conversations":
        return WorkflowSummary(
            option="oh_conversations",
            title="OH Conversations: V1 conversations are the control surface",
            constraint=(
                "The orchestrator coordinates first-class Cloud conversations, polls their "
                "status, and feeds outputs from one conversation into the next."
            ),
            steps=[
                WorkflowStep(
                    actor="conversation_orchestrator",
                    action="creates one V1 conversation for app planning and one for connector building",
                    produces="two Cloud app conversations with independent history",
                ),
                WorkflowStep(
                    actor="app_builder_conversation",
                    action="returns app scaffold, contract expectations, and blocked work",
                    produces="customer-visible app planning output",
                ),
                WorkflowStep(
                    actor="connector_builder_conversation",
                    action="returns connector plan and integration handoff",
                    produces="customer-visible connector output",
                ),
                WorkflowStep(
                    actor="integration_conversation",
                    action="reconciles the two conversation outputs into a final plan",
                    produces="final integration summary in a third Cloud conversation",
                ),
            ],
        )

    if option == "sdk_subagents":
        return WorkflowSummary(
            option="sdk_subagents",
            title="SDK Subagents: code-level orchestration over V1 conversations",
            constraint=(
                "The workflow graph is hardwired in Python, but each worker still runs as a "
                "first-class Cloud conversation."
            ),
            steps=[
                WorkflowStep(
                    actor="sdk_orchestrator",
                    action="defines worker roles, dependencies, and handoff rules in code",
                    produces="repeatable workflow graph",
                ),
                WorkflowStep(
                    actor="app_builder_conversation",
                    action="runs as a V1 Cloud conversation under orchestrator control",
                    produces="app scaffold and blocked-work output",
                ),
                WorkflowStep(
                    actor="connector_builder_conversation",
                    action="runs as a V1 Cloud conversation under orchestrator control",
                    produces="connector plan and handoff output",
                ),
                WorkflowStep(
                    actor="sdk_orchestrator",
                    action="collects conversation outputs and launches integration as the next step",
                    produces="final integration conversation and summary",
                ),
            ],
        )

    if option == "cloud_async":
        return WorkflowSummary(
            option="cloud_async",
            title="Cloud Async: external Python coordinates remote workers",
            constraint="Concurrency is owned by Python orchestration against Cloud sandboxes and runtimes.",
            steps=[
                WorkflowStep(
                    actor="python_orchestrator",
                    action="starts isolated cloud conversations for app and connector work",
                    produces="two active remote conversations with independent progress",
                ),
                WorkflowStep(
                    actor="connector_builder",
                    action="creates the connector artifact independently",
                    produces="connector design package and contract details",
                ),
                WorkflowStep(
                    actor="app_builder",
                    action="continues on connector-independent implementation",
                    produces="application scaffold plus a list of work still blocked on the connector",
                ),
                WorkflowStep(
                    actor="python_orchestrator",
                    action="injects the connector result back into app and test flow",
                    produces="merged integration task and final validation output",
                ),
            ],
        )

    raise ValueError(f"Unsupported workflow option: {option}")
