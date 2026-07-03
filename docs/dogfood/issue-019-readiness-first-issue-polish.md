# Issue 019: Readiness And First-Issue Polish

## Results

Implemented the next user-readiness pass after comparing GoShipit with Superpowers, No Mistakes, and GSD Core.

Added:

- `verify-run` warnings for acceptance criteria that lack explicit evidence.
- `verify-run` warnings for active runs that do not have `state/runs/<issue-id>/handoff.md`.
- `status --json`, `doctor --json`, and `verify-run --json`.
- Phase-aware active issue next commands in `status`.
- A stricter readiness sequence: handoff, export, `verify-run --strict`, then cleanup.
- First-issue “What Gets Created” docs.
- Skill/doc pressure tests for readiness, JSON, artifact docs, and skill-change discipline.
- A fuller packaged-install acceptance flow that installs the wheel, creates a disposable target repo, registers it, adds and starts an issue, records evidence, runs checks, writes handoff, exports evidence, runs `verify-run --strict`, archives with `--remove-worktree`, and runs final `doctor`.

Verification:

- `uv run pytest -q`: 170 passed
- `uv run go-ship-it doctor`: 0 errors, 0 warnings
- `just release-check`: passed tests, doctor, wheel build, expanded packaged install validation, and agent CLI validation

Release-check evidence included:

- `flow.handoff`: passed
- `flow.export`: passed
- `flow.verify_strict`: passed
- `flow.cleanup_archive`: passed
- `flow.final_doctor`: passed

## Rough Edges Observed

- `verify-run --strict` now depends on agents writing acceptance criteria phrasing into review evidence. This is useful, but intentionally simple; it is not semantic matching.
- The packaged-install flow is much stronger now, but still not a live Claude/Cursor conversation. It validates package mechanics and CLI behavior, not skill invocation behavior inside a real user session.
- `status` is more useful as a command center, but the command list can grow. Keep using status hints before adding new skills or lifecycle states.

## Lessons To Promote

- Update skills: `work-issue` should treat `verify-run --strict` as the local readiness gate before archive cleanup.
- Update docs: first-user docs should show what files are created, not only command names.
- Add verifier check: acceptance criteria must be explicitly tied to evidence.
- Add verifier check: active runs should have a handoff before they are considered ready.
- Defer as product question: semantic acceptance matching, remote PR checks, and live marketplace install testing should wait until local dogfood remains stable.
