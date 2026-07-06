# Phase: investigate

Understand the problem well enough to propose a fix.

## Inputs

- A started run: `start-issue` has already created the isolated worktree and run state.
- `issue.md`: the problem statement, context, and acceptance criteria the rest of the run must satisfy.

## Outputs

- An Investigation note that pins the problem, the relevant files, reproduction/observed behavior, constraints, and the validation boundary (the behavior that later needs a test).

```sh
go-ship-it set-phase <repo>/<issue-id> investigate --note "<why investigation started or resumed>"
go-ship-it append-note <repo>/<issue-id> --section "Investigation" --for-phase investigate --note "<findings>"
```

## Evidence

- The `## Investigation` note section in `notes.md`, following `references/workflow-notes-template.md` (problem restated, relevant files, reproduction or observed behavior, constraints, open questions).

## Gate

- None. Investigation self-transitions to propose once the findings and validation boundary are recorded — no human approval is required to leave this phase.
