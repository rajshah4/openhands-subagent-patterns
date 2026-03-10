# Mental Model

## 1. SDK Delegate

Use this when the parent can stop while children work.

Flow:

1. Orchestrator agent reads the product request.
2. It identifies connector-dependent and connector-independent work.
3. It spawns:
   - `connector_builder`
   - `app_builder`
4. It delegates both tasks in one blocking call.
5. When both complete, the orchestrator resumes.
6. It hands artifacts to `integration_tester`.
7. It integrates, tests, and finishes.

Key property:

- concurrency exists among child workers
- the parent conversation is blocked until all delegated work returns

## 2. Cloud Async

Use this when two conversations truly need to run independently.

Flow:

1. External Python orchestrator receives the request.
2. It creates separate cloud conversations for:
   - `connector_builder`
   - `app_builder`
3. It sends each a scoped task.
4. It calls `run(blocking=False)` on each remote conversation.
5. It polls status or watches callbacks independently.
6. If the connector finishes first, it writes the connector artifact somewhere
   durable and sends an update message to the app conversation.
7. When both converge, it starts an integration conversation or final run.

Key property:

- the concurrency lives outside the agent's single reasoning loop
- the orchestrator owns state, retries, and artifact routing

Important distinction:

- this pattern uses real OpenHands Cloud sandboxes and remote SDK conversations
- those remote conversation IDs are not necessarily the same thing as the
  Cloud UI conversations visible at `app.all-hands.dev/conversations/...`
- in this repo, history is durable at the remote agent-server layer and in the
  downloaded local artifacts under `results/`

## 3. GitHub Control Surface

Use this when you want durable state, review checkpoints, and minimal custom
infrastructure.

Flow:

1. Main workflow opens a repo issue for a missing connector.
2. `@OpenHands` on the issue triggers the connector skill set.
3. Connector work lands in a PR.
4. The main app flow continues on independent work or pauses at a dependency
   gate.
5. A PR comment or merge event triggers integration and testing.
6. The repo timeline becomes the audit log.

Key property:

- orchestration is event-driven and durable
- latency is higher, but human intervention is natural

## POC Guidance

For a team evaluating these patterns:

- `sdk_delegate` is the cleanest demo of "sub-agents" but not the cleanest demo
  of "main agent keeps working"
- `cloud_async` matches that requirement most directly
- `github_control` is the easiest path to a business-friendly demo with visible
  checkpoints
