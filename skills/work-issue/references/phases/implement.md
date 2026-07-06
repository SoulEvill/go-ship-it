# Phase: implement

Drive the approved acceptance-level failing test to green.

## Inputs

- The approved proposal and the acceptance-level failing test authored during propose.

## Outputs

- Code changes that make the acceptance-level test pass, plus any supporting unit tests written along the way.

```sh
go-ship-it set-phase <repo>/<issue-id> implement --inner-loop tdd --note "<proposal accepted>"
go-ship-it append-note <repo>/<issue-id> --section "Implementation" --for-phase implement --note "<changed files and decisions>"
```

The acceptance-level failing test approved during propose is the entry ticket into this phase — do not start implement without it.

## Evidence

- The `## Implementation` note: files changed, key decisions, decision record, scope changes, follow-up risks.
- The `inner_loop` recorded in `run.yaml` via `set-phase --inner-loop`. Allowed values are `tdd`, `debug`, `spike`, and `none`. `--inner-loop none` requires `--inner-loop-reason` explaining why no test loop was used.

The coding methodology itself is pluggable and does not have to come from GoShipit: use a Superpowers-style TDD skill, a systematic-debugging skill, or an equivalent platform capability for the inner loop, then record the choice and its evidence back into the run.

## Gate

- The acceptance-level test must be green before `set-phase <repo>/<issue-id> review`. GoShipit does not silently accept an implement phase that leaves the acceptance test red.
