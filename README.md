# OpenHands Subagent Patterns

This folder is a stubbed POC workspace for three ways to structure a
"user description -> generated app -> missing connector built in parallel"
workflow with OpenHands.

It is intentionally lightweight tonight:

- the code is scaffolded but not wired to production credentials
- the demos focus on orchestration shape, not full execution
- the skills are placeholders you can swap with real project skills later

## The three demos

1. `sdk_delegate`
   Uses the OpenHands SDK delegate pattern. The parent orchestrator blocks while
   sub-agents run, so the main flow is modeled as plan -> delegate in parallel ->
   integrate.
2. `cloud_async`
   Uses OpenHands Cloud conversations as separate long-running workers. An
   external orchestrator starts both flows, polls them independently, and
   injects connector results back into the app flow.
3. `github_control`
   Uses issues, PRs, and `@OpenHands` comments as the coordination surface. The
   repo becomes the durable workflow state.

## Setup

```bash
cd /Users/rajiv.shah/Code/openhands-subagent-patterns
uv sync
cp .env.example .env
```

## Dry-run mental model

```bash
uv run python scripts/print_workflow.py --option sdk_delegate
uv run python scripts/print_workflow.py --option cloud_async
uv run python scripts/print_workflow.py --option github_control
```

## Stub demo entrypoints

```bash
uv run python scripts/demo_sdk_delegate.py --dry-run
uv run python scripts/demo_async_cloud.py --dry-run
uv run python scripts/demo_github_control.py --dry-run
```

Tomorrow, the same scripts can be extended to execute real workspaces and real
conversations.

## Recommendation

For a first POC:

- start with `github_control` if you want the simplest operational control plane
- start with `cloud_async` if true overlapping long-running work is required
- use `sdk_delegate` only when the work can be cleanly decomposed up front and
  the parent agent does not need to keep reasoning during child execution
