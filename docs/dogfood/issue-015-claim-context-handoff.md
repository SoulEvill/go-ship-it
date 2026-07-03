# Issue 015: Claim Context And Handoff

## Problem

Parallel issue sessions need deterministic anchors so one agent session does not accidentally continue or mutate the wrong active run.

## Decision

Use issue id as the unit of parallelism, worktree path as physical isolation, and a deterministic `claim_id` as the run anchor.

`claimed_by` remains human-readable. It can be supplied with `--claimed-by`, or GoShipit derives a stable local actor label from the agent/tool environment, user, host, control root, and current working directory.

## Behavior

`start-issue` now records:

- `claimed_by`
- `claim_id`
- `.go-ship-it/context.yaml` inside the managed worktree

The context file records issue id, repo id, control root, run dir, issue file, worktree, branch, claim label, and claim id. It is ignored by Git.

Duplicate starts are idempotent for active issues: GoShipit returns the existing active run details instead of creating a second worktree.

## Handoff

Handoff is explicit. A user or agent can print or write resume context:

```sh
go-ship-it show-run <issue-id> --handoff
go-ship-it handoff <issue-id> --write
```

The written file defaults to:

```text
state/runs/<issue-id>/handoff.md
```

## Verification

Focused validation:

```sh
uv run pytest tests/test_state.py tests/test_cli_smoke.py tests/test_target_e2e_harness.py -q
```

Result: `63 passed`.
