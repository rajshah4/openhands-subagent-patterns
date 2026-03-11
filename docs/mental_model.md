# Mental Model

This repo currently centers on three active patterns:

1. `github_control`
2. `oh_conversations`
3. `sdk_subagents`

They all tell the same customer story:

- `app_builder` produces an app scaffold plus blocked and unblocked work
- `connector_builder` produces the connector plan and integration handoff
- `integration_tester` or a follow-up integration step reconciles the two

## 1. GitHub Control

Use this when you want the repository to be the workflow state.

Flow:

1. `app_builder` opens a missing-connector issue with scoped requirements.
2. `connector_builder` responds in the repo and opens a PR.
3. A reviewer or bot signals readiness with a merge or `@OpenHands` comment.
4. `integration_tester` pulls the PR state into final validation.

Key property:

- issues, PRs, comments, and repo state carry the workflow context
- orchestration is durable and review-friendly, but higher latency is normal

## 2. OH Conversations

Use this when you want Cloud-native conversation history to be the control
surface.

Flow:

1. A conversation orchestrator creates one `V1` conversation for app planning.
2. It creates a second `V1` conversation for connector building.
3. The app conversation returns scaffold output, contract expectations, and
   blocked work.
4. The connector conversation returns the connector plan and integration
   handoff.
5. The orchestrator starts a third integration conversation that reconciles the
   two outputs into a final plan.

Key property:

- each worker is a first-class Cloud conversation with independent history
- the orchestrator owns polling, sequencing, and output routing between
  conversations

## 3. SDK Subagents

Use this when you want the workflow graph to live in code while still using
`V1` Cloud conversations for the worker runs.

Flow:

1. An SDK orchestrator defines worker roles, dependencies, and handoff rules in
   Python.
2. It launches the app-builder step as a `V1` Cloud conversation.
3. It launches the connector-builder step as a `V1` Cloud conversation.
4. After those steps complete, it launches the integration step as the next
   stage in the graph.

Key property:

- workflow structure is explicit and repeatable in code
- workers still run as first-class Cloud conversations rather than hidden local
  subtasks

## Recommendation

For a first POC:

- start with `github_control` for the simplest operational control plane
- start with `oh_conversations` if conversation history should be the visible
  control surface
- move to `sdk_subagents` when you want stronger code-level control over
  dependencies and handoffs
