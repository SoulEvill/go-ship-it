# Phase: implement

Drive the approved acceptance-level failing test to green.

## Inputs

- On the STANDARD track: the approved proposal and the acceptance-level failing test authored and pre-approved during propose.
- On the QUICK track: propose is skipped, so there is no pre-approved propose artifact to consume. Author the acceptance-level failing test here at implement-entry instead — it is the executable definition of done for the change. `inner_loop` still defaults to `tdd` for code changes, and `none` still requires a recorded `--inner-loop-reason` (docs/config-only changes may use `none`). If the change warrants a formal pre-approved acceptance gate, promote to `standard` with `set-track` first.

## Outputs

- Code changes that make the acceptance-level test pass, plus any supporting unit tests written along the way.

```sh
go-ship-it set-phase <repo>/<issue-id> implement --inner-loop tdd --note "<proposal accepted>"
go-ship-it append-note <repo>/<issue-id> --section "Implementation" --for-phase implement --note "<changed files and decisions>"
```

The acceptance-level failing test is the entry ticket into this phase. On the standard track it was authored and approved during propose — do not start implement without it. On the quick track propose's approval gate does not apply, so author that failing test here at implement-entry (or fold the acceptance evidence into the Implementation and Review notes); do not stall looking for a propose artifact that a quick run never produced.

## Evidence

- The `## Implementation` note: files changed, key decisions, decision record, scope changes, follow-up risks.
- The `inner_loop` recorded in `run.yaml` via `set-phase --inner-loop`. Allowed values are `tdd`, `debug`, `spike`, and `none`. `--inner-loop none` requires `--inner-loop-reason` explaining why no test loop was used.

The coding methodology itself is pluggable and does not have to come from GoShipit: use a Superpowers-style TDD skill, a systematic-debugging skill, or an equivalent platform capability for the inner loop, then record the choice and its evidence back into the run.

## Gate

- The acceptance-level test must be green before `set-phase <repo>/<issue-id> review`. GoShipit does not silently accept an implement phase that leaves the acceptance test red.
