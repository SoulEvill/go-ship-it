# Phase: prepare-pr

Write a local, reversible preview of the pull request before anything is pushed.

## Inputs

- A reviewed run: review phase complete, `verify-run --strict` clean. A clean `verify-run` concretely requires all of: every track-required note section (`standard`: Investigation/Proposal/Implementation/Review; `quick`: Implementation/Review); a PASSING latest `run-check --check test` record when the repo configures a test command; a written handoff (`handoff --write`); and a `Review` note that echoes each acceptance criterion close to verbatim (the matcher is literal, so `verify-run --strict` names exactly which criterion lacks evidence). Fix every finding before moving on to `publish-pr`.

## Outputs

- A local `pr.md` file beside the run files, previewing the PR title and body.

```sh
go-ship-it prepare-pr <repo>/<issue-id> --branch <team-branch-name>
```

The first `prepare-pr` needs `--branch`; reruns reuse the recorded branch. This is THIS doc's phase — it is the single place to change PR shape or template; edit `pr.md` generation, not the publish or archive phases, if the PR content needs to change.

## Evidence

- The `pull_request` record in `run.yaml` (branch, title).
- The run's phase set to `prepare-pr`.

## Gate

- None. This step is local and reversible — nothing is pushed and no PR is opened. Show the user `pr.md` and `evidence.md` and let them review before moving to publish.
