# Phase: propose

Turn investigation findings into an approved plan and an executable definition of done.

## Inputs

- The Investigation note: findings, relevant files, and the validation boundary identified during investigate.

## Outputs

- A Proposal note: recommended approach, alternatives considered, risks, and acceptance checks.
- **The acceptance-level failing test**, authored in the worktree. This is the executable definition of done for the issue — propose pre-approves it before any implementation code is written. Per-task unit tests are a separate concern that stay inside implement's inner loop; this is the higher-level test that proves the issue's acceptance criteria are met.

```sh
go-ship-it set-phase <repo>/<issue-id> propose --note "<investigation summary>"
go-ship-it append-note <repo>/<issue-id> --section "Proposal" --for-phase propose --note "<proposal and acceptance-level failing test>"
```

## Evidence

- The `## Proposal` note section naming the acceptance-level failing test's file/command and recording its RED output (the test fails before implementation, proving it actually exercises the missing behavior).

## Gate

- HUMAN. The user must approve both the proposal and the acceptance-level failing test before `set-phase <repo>/<issue-id> implement`. Do not move to implement on an unapproved proposal or an untested acceptance boundary.
