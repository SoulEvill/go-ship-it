# Phase: prepare-pr

Write a local, reversible preview of the pull request before anything is pushed.

## Inputs

- A reviewed run: review phase complete, `verify-run --strict` clean.

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
