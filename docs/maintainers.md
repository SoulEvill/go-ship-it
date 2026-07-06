# GoShipit Maintainer Notes

This project should stay small at the surface and explicit underneath.

## Command Surface

Keep the agent-facing skill surface lean:

- `using-go-ship-it` for orientation
- `manage-issues` for lifecycle state movement
- `work-issue` for active issue work and evidence
- `close-out` for shipping a reviewed issue

Add a CLI command when the behavior is plumbing. Add a skill only when the user needs a distinct mental model or workflow entry point.

`close-out` earned its slot on exactly that bar: `prepare-pr` (reversible), `publish` (irreversible), and `archive` (terminal) are a genuinely distinct mental model from investigate/propose/implement/review — a "gate" a human crosses deliberately, not another `work-issue` phase to click through. See `docs/design/lifecycle-phase-separation.md` for the full reasoning behind splitting close-out into its own skill.

## State Shape

State should stay visible on disk and easy to inspect:

```text
state/repos/<repo>/repo.yaml
state/repos/<repo>/context.md
state/repos/<repo>/issues/todo/<issue-id>/issue.md
state/repos/<repo>/issues/execution/<issue-id>/issue.md
state/repos/<repo>/issues/execution/<issue-id>/run.yaml
state/repos/<repo>/issues/execution/<issue-id>/notes.md
state/repos/<repo>/issues/execution/<issue-id>/logs/
state/repos/<repo>/issues/archive/<issue-id>/issue.md
worktrees/<repo>/<issue-id>/
```

Do not add flat repo files such as `state/repos/<repo>.yaml`. Repo folders give each target a clear home for machine config and human context.

Do not add global issue or run folders. Issue ids are repo-local, and explicit CLI references should use `<repo>/<issue-id>`.

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

## Skill Change Gate

Treat skills as product behavior, not loose prose.

Before changing an existing skill, cite at least one pressure scenario, dogfood note, or failing test that explains the friction. Good pressure scenarios include: starting in the wrong directory, stale `.go-ship-it/context.yaml`, duplicate active issue, implementation before proposal, failing `run-check`, unclear cleanup destination, missing repo context, or missing acceptance criteria evidence.

Before adding new skills, prove that the new skill gives users a distinct mental model. Do not add new skills for a CLI verb, a reference note, or a one-off workflow detail that can live under `using-go-ship-it`, `manage-issues`, or `work-issue`.

When changing command examples in docs or skills, add or update a test so example drift is caught by `uv run pytest`.
