# GoShipit Maintainer Notes

This project should stay small at the surface and explicit underneath.

## Command Surface

Keep the agent-facing skill surface lean:

- `using-go-ship-it` for orientation
- `manage-issues` for lifecycle state movement
- `work-issue` for active issue work and evidence

Add a CLI command when the behavior is plumbing. Add a skill only when the user needs a distinct mental model or workflow entry point.

## State Shape

State should stay visible on disk and easy to inspect:

```text
state/repos/<repo>/repo.yaml
state/repos/<repo>/context.md
state/issues/todo/<issue-id>.md
state/issues/execution/<issue-id>.md
state/issues/archive/<issue-id>.md
state/runs/<issue-id>/
worktrees/<repo>/<issue-id>/
```

Do not add flat repo files such as `state/repos/<repo>.yaml`. Repo folders give each target a clear home for machine config and human context.

## Status vs Doctor

Use `status` as the command center. It should help users answer:

- Where am I?
- What issues exist?
- What is active?
- What can I do next?

Use `doctor` as a consistency and readiness check. It should report health, not become a general workflow guide.

## Adding Workflow Detail

Prefer one of these before adding new lifecycle states or new skills:

- a clearer `status` hint
- a focused verifier check
- a local reference file under an existing skill
- a dogfood note that captures the rough edge first

New abstractions should come from repeated dogfood friction, not from guessing too early.
