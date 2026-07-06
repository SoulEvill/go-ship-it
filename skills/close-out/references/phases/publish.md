# Phase: publish

Push the branch and open the real pull request.

## Inputs

- The user-reviewed `pr.md` written during prepare-pr.

## Outputs

- A pushed branch and a created PR, recorded as `published_url`.

```sh
go-ship-it publish-pr <repo>/<issue-id> --approved
```

## Evidence

- The run's phase set to `publish`.
- `pull_request.published_url` recorded in `run.yaml`.

## Gate

- HUMAN. Run only after the user approves publishing via `--approved`, or when the repo has `pull_request.auto_publish: true`. Publish is mechanically blocked while `verify-run` reports ANY finding — there is no override; fix the evidence instead of forcing publish. Repos with `pull_request.provider: none` skip this phase entirely — the reviewed local `pr.md` from prepare-pr is their final gate, and cleanup proceeds straight from prepare-pr to archive.
