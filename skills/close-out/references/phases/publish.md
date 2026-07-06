# Phase: publish

Push the branch and open the real pull request.

## Inputs

- The user-reviewed `pr.md` written during prepare-pr.
- A clean `verify-run --strict` (see Prerequisites).

## Prerequisites

Publish is mechanically blocked while `verify-run` reports any finding, and there is no override — the only way through is to make `verify-run --strict` clean. Concretely, before `publish-pr` can run, the run needs ALL of:

- every track-required note section present — `standard`: `Investigation`, `Proposal`, `Implementation`, `Review`; `quick`: `Implementation`, `Review`;
- a PASSING latest `run-check --check test` record when the repo configures a test command (an earlier failed check is fine once the latest run of that check is green);
- a written handoff (`go-ship-it handoff <repo>/<issue-id> --write`);
- a `Review` note whose phrasing echoes each acceptance criterion close to verbatim. The acceptance matcher is literal, so `verify-run --strict` names exactly which criterion still lacks evidence — copy the criterion text into the Review note rather than paraphrasing it.

Run `go-ship-it verify-run <repo>/<issue-id> --strict` and fix every finding before `publish-pr`.

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
