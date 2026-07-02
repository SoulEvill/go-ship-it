# Trace And Verify Loop Foundation Dogfood

Date: 2026-06-30

Verification rerun: 2026-07-01

## Results

- `uv run go-ship-it show-run issue-003 --trace` produced a chronological trace with `issue.created`, `run.started`, phase and evidence journal events, `check.setup`, `check.test`, and `run.cleanup`.
- Before re-export, `uv run go-ship-it verify-run issue-003` reported `0 errors, 2 warnings, 12 ok`.
- The pre-re-export warnings were `run.export_stale` and `worktree.preserved_after_archive`.
- `run.export_stale` appeared because the existing legacy export lacked structured export metadata and was visibly stale: it sourced `state/issues/execution/issue-003.md` and showed run phase `test`, while the current run had already been archived and cleaned up.
- `uv run go-ship-it export-run issue-003 --output docs/dogfood/issue-006-parawave-real-enhancement-export.md` succeeded and rewrote the evidence snapshot.
- After re-export, `uv run go-ship-it verify-run issue-003` reported `0 errors, 1 warnings, 13 ok`.
- The refreshed export includes `state/issues/archive/issue-003.md`, issue status `archive`, run phase `cleanup`, cleanup metadata, and an `exports` entry for `docs/dogfood/issue-006-parawave-real-enhancement-export.md`.
- After re-export, `show-run --trace` included `export.written docs/dogfood/issue-006-parawave-real-enhancement-export.md` at `2026-07-01T00:58:10-07:00`.

## Rough Edges Observed

- Existing exports created before this milestone cannot be classified as stale from structured metadata alone; the verifier now falls back to matching dogfood export documents for the issue and reports `run.export_stale`.
- The trace is useful immediately, but command checks appear both as journal entries and command records. That duplication is accurate, but readers need to understand that journal entries preserve narrative while `check.*` events are structured command records.
- `worktree.preserved_after_archive` remained after re-export. This is expected for dogfood review, but the verifier output should make the human decision explicit: preserve for review or remove when no longer needed.
- The old issue-006 dogfood report already documented that export happened before cleanup. The new verifier makes that consequence visible for legacy exports and clears it once a cleanup-phase export is recorded.

## Lessons To Promote

- update a skill: `cleanup-issue` should continue recommending a final export after archive cleanup when the user needs archived-state evidence.
- update a skill: `test-and-review` should require acceptance criteria to be matched to command records or review notes before declaring readiness.
- update docs: dogfood reports should record both the pre-export and post-export verifier summaries, not just the final clean result.
- add verifier check: keep legacy export detection covered so pre-metadata dogfood exports surface as `run.export_stale` instead of a generic missing-export warning.
- add verifier check: consider a preserved-worktree decision hint that asks whether an archived worktree should remain for review or be removed.
- defer as product question: decide whether `show-run --trace` should collapse journal check events and structured `check.*` events by default, or keep both for full auditability.
