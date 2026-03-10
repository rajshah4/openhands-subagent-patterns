# OpenHands Subagent Patterns

This repo shows three ways to structure a
"user description -> generated app -> missing connector built in parallel"
workflow with OpenHands.

The examples are intended as customer-facing patterns, not production
starters. The main value is the orchestration shape and the tradeoffs between
SDK delegation, external async orchestration, and GitHub as a control plane.

## The patterns

1. `github_control`
   Uses issues, PRs, and `@OpenHands` comments as the coordination surface. The
   repo becomes the durable workflow state. The issue captures blocked work and
   the PR carries the connector handoff back to the app flow.
2. `oh_conversations`
   Uses `V1` Cloud conversations as the control surface. Each worker is its own
   first-class Cloud conversation, and a final integration conversation consumes
   the outputs from the app-builder and connector-builder conversations. In the
   UI this appears as three separate conversation threads: app builder,
   connector builder, and integration tester.
3. `sdk_subagents`
   Uses the OpenHands SDK sub-agent orchestration approach. A top-level
   orchestrator hardwires the workflow graph in code, then launches worker
   tasks as first-class `V1` Cloud conversations with explicit dependency and
   handoff control.
Across the patterns, the shared story is:

- `app_builder` produces an app scaffold plus a clear blocked/unblocked split
- `connector_builder` produces a connector plan plus integration handoff
- `integration_tester` or follow-up workflow reconciles the two
## Setup

```bash
cd /Users/rajiv.shah/Code/openhands-subagent-patterns
uv sync
cp .env.example .env
```

## Dry-run mental model

```bash
uv run python scripts/print_workflow.py --option github_control
uv run python scripts/print_workflow.py --option oh_conversations
uv run python scripts/print_workflow.py --option sdk_subagents
```

## Demo entrypoints

```bash
uv run python scripts/demo_github_control.py --dry-run
uv run python scripts/demo_oh_conversations.py --dry-run
uv run python scripts/demo_sdk_subagents.py --dry-run
```

The conversation-control path now supports a live `V1` flow:

```bash
uv run python scripts/demo_oh_conversations.py --run-live
```

That flow starts separate `V1` app conversations for the app builder and
connector builder, waits for both to finish, extracts their final outputs from
the event stream, starts a third integration conversation, and saves a JSON
summary under `results/oh_conversations/`.

The hybrid SDK + conversations path is available here:

```bash
uv run python scripts/demo_sdk_subagents.py --run-live
```

That flow hardwires the workflow graph in Python, launches the worker steps as
`V1` Cloud conversations, and saves a JSON summary under
`results/sdk_subagents/`.

Representative artifacts now include:

- `app_scaffold.md`
- `connector_contract.md`
- `blocked_work.md`
- `connector_plan.md`
- `connector_handoff.md`
- `integration_summary.md`

Current live behavior:

- `github_control`: validated against live GitHub issue/PR/comment flow
- `oh_conversations`: live `V1` conversation creation and completion are working
- `sdk_subagents`: live `V1` orchestration works when MCP is healthy
Current cloud caveat:

- sandbox cleanup currently returns `405 Method Not Allowed` from the Cloud API
  during teardown, so the orchestration logic works but cleanup is not fully
  clean yet

## Recommendation

For a first POC:

- start with `github_control` if you want the simplest operational control plane
- start with `oh_conversations` if you want Cloud-native conversation history as the control surface
- move to `sdk_subagents` when you want the same Cloud conversation surface but a more explicit workflow graph in code
