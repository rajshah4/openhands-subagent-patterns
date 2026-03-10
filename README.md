# OpenHands Subagent Patterns

This repo shows three ways to structure a
"user description -> generated app -> missing connector built in parallel"
workflow with OpenHands.

The examples are intended as customer-facing patterns, not production
starters. The main value is the orchestration shape and the tradeoffs between
SDK delegation, external async orchestration, and GitHub as a control plane.

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

## Capability Matrix

| Pattern | Uses SDK `Conversation` | Uses Cloud sandbox | UI-visible Cloud conversation | Durable history lives in |
|---|---|---|---|---|
| `sdk_delegate` | Yes, local | No | No | local run artifacts |
| `cloud_async` | Yes, remote | Yes | No, not in this implementation | remote agent-server event history plus local downloaded artifacts |
| `github_control` | Not as the main control plane | Optional, via GitHub-triggered OpenHands runs | depends on how the GitHub integration is configured | GitHub issues, PRs, comments |

## Important Distinction: Cloud Sandbox vs Cloud UI Conversation

OpenHands Cloud has two layers that are easy to conflate:

- Cloud sandbox / agent-server runtime:
  this is what `OpenHandsCloudWorkspace` provisions. The SDK then talks
  directly to the remote agent server running inside that sandbox.
- Cloud UI conversation:
  this is the hosted product conversation you usually browse at
  `https://app.all-hands.dev/conversations/<id>`.

In this repo's `cloud_async` demo, the script creates real OpenHands Cloud
sandboxes and real remote SDK conversations, but those conversations are not
automatically registered as Cloud UI conversations. The event history exists on
the remote agent-server and is also downloaded into `results/`.

Practical consequence:

- `cloud_async` is real cloud execution
- the conversation IDs are real remote conversation IDs
- those IDs should not be expected to appear in the normal Cloud UI history

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

## Demo entrypoints

```bash
uv run python scripts/demo_sdk_delegate.py --dry-run
uv run python scripts/demo_async_cloud.py --dry-run
uv run python scripts/demo_github_control.py --dry-run
```

The async cloud path now also supports a first live orchestration skeleton:

```bash
uv run python scripts/demo_async_cloud.py --run-live --keep-alive
```

That flow starts separate cloud sandboxes and remote SDK conversations for the
app builder and connector builder, runs them with `blocking=False`, polls for
artifact readiness independently, uploads the completed artifacts into a final
integration sandbox, and saves a JSON summary under `results/cloud_async/`.

Current live behavior:

- `sdk_delegate`: validated locally
- `cloud_async`: validated against real OpenHands Cloud sandboxes
- `github_control`: validated against live GitHub issue/PR/comment flow

Current cloud caveat:

- sandbox cleanup currently returns `405 Method Not Allowed` from the Cloud API
  during teardown, so the orchestration logic works but cleanup is not fully
  clean yet

## Recommendation

For a first POC:

- start with `github_control` if you want the simplest operational control plane
- start with `cloud_async` if true overlapping long-running work is required
- use `sdk_delegate` only when the work can be cleanly decomposed up front and
  the parent agent does not need to keep reasoning during child execution
