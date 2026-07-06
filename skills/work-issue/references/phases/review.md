# Phase: review

Check the implemented change is correct, complete, and ready to hand off for shipping.

## Inputs

- The implemented change: code driving the acceptance-level test green, plus its supporting notes.

## Outputs

- A Review note with findings classified as `auto-fix` (apply directly), `no-op` (not worth acting on), or `ask-user` (only these stop the human) — only `ask-user` findings block progress.

```sh
go-ship-it set-phase <repo>/<issue-id> review --note "<ready for review>"
go-ship-it set-phase <repo>/<issue-id> review --review-pipeline plugin:code-review --note "<ready for review>"
go-ship-it run-check <repo>/<issue-id> --check test
go-ship-it append-note <repo>/<issue-id> --section "Review" --for-phase review --note "<review findings and readiness>"
```

## Evidence

- The `## Review` note: commands run, results, acceptance criteria matched to evidence, independent checker verdict/caveats, remaining gaps, cleanup recommendation.
- `run-check` command records under `logs/commands/`.
- The `review_pipeline` recorded in `run.yaml` via `set-phase --review-pipeline`. Allowed values are `self`, `clean-room`, or a plugin-provided pipeline named `plugin:<name>` (for example `plugin:code-review`) — the review methodology, like the implement inner loop, is pluggable and may be supplied by the platform.

Before claiming the issue is done, use the agent platform's native sub-agent, reviewer, or checker mechanism when available and record its verdict — this is the semantic done/not-done judgment that complements the deterministic evidence-structure gate below.

## Gate

- `go-ship-it verify-run <repo>/<issue-id> --strict` must be clean, and the independent checker verdict must be recorded in the Review note. Once both are true, hand off to the close-out skill for prepare-pr, publish, and archive — review does not do any of those itself.
