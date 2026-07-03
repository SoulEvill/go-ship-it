# Readiness First-Issue Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make GoShipit's active-run workflow easier for a new user and safer before cleanup/archive by adding a clear readiness gate, phase-aware status guidance, structured command output, and first-issue onboarding docs.

**Execution Status:** Completed in branch `go-ship-it-readiness-polish`; see `docs/dogfood/issue-019-readiness-first-issue-polish.md` for verification evidence.

**Architecture:** Keep the three-skill surface unchanged. Extend existing CLI plumbing: `verify-run` becomes the readiness gate, `status` becomes more phase-aware, and JSON output is added to the existing commands rather than introducing a new protocol. Docs and skill references explain what gets created and how users should move through the first issue.

**Tech Stack:** Python 3.11+, PyYAML, argparse CLI, pytest, visible filesystem state under `state/` and `worktrees/`.

---

### Task 1: Strengthen Run Readiness Verification

**Files:**
- Modify: `src/go_ship_it/verify.py`
- Modify: `src/go_ship_it/cli.py`
- Test: `tests/test_verify_run.py`
- Test: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert `verify_run()` warns when an active issue has acceptance criteria that are not mentioned in journal/check evidence, warns when an active run has no handoff file, and accepts the same run once evidence and handoff exist.

- [ ] **Step 2: Run focused tests to verify failure**

Run: `uv run pytest tests/test_verify_run.py -q`

Expected: new tests fail because acceptance coverage and handoff checks do not exist yet.

- [ ] **Step 3: Implement minimal verifier checks**

Parse acceptance criteria from the issue body, compare each criterion against normalized run evidence text, and add `handoff.missing` / `handoff.present` findings for active execution runs. Keep findings as warnings so existing `--strict` controls whether warnings fail the CLI.

- [ ] **Step 4: Run focused tests to verify pass**

Run: `uv run pytest tests/test_verify_run.py -q`

Expected: all verifier tests pass.

### Task 2: Add Structured JSON Output

**Files:**
- Modify: `src/go_ship_it/cli.py`
- Test: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write failing CLI tests**

Add tests for `status --json`, `doctor --json`, and `verify-run --json`. Assert the output is parseable JSON with summary counts and finding codes where applicable.

- [ ] **Step 2: Run focused tests to verify failure**

Run: `uv run pytest tests/test_cli_smoke.py -q`

Expected: parser rejects the new flags or commands print Markdown only.

- [ ] **Step 3: Implement minimal JSON formatters**

Add optional `--json` flags to `status`, `doctor`, and `verify-run`. Reuse existing state/report objects and keep JSON schema simple: `summary`, `current`, `todo`, `active`, `worktrees`, and `findings` arrays.

- [ ] **Step 4: Run focused tests to verify pass**

Run: `uv run pytest tests/test_cli_smoke.py -q`

Expected: all CLI smoke tests pass.

### Task 3: Make Status Phase-Aware

**Files:**
- Modify: `src/go_ship_it/cli.py`
- Test: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write failing status guidance tests**

Assert active issues in `investigate`, `propose`, `implement`, and `test` phases show next useful commands appropriate to that phase, including the readiness sequence: `run-check`, `handoff --write`, `export-run`, `verify-run --strict`, then cleanup.

- [ ] **Step 2: Run focused tests to verify failure**

Run: `uv run pytest tests/test_cli_smoke.py::test_main_status_prints_workspace_summary -q`

Expected: missing phase-specific guidance.

- [ ] **Step 3: Implement minimal phase-aware guidance**

Extract a helper that returns commands by phase. Keep `status` concise and avoid a new skill or lifecycle state.

- [ ] **Step 4: Run focused tests to verify pass**

Run: `uv run pytest tests/test_cli_smoke.py -q`

Expected: all CLI smoke tests pass.

### Task 4: Update Skills And Onboarding Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/install.md`
- Modify: `docs/user-e2e.md`
- Modify: `docs/maintainers.md`
- Modify: `skills/work-issue/SKILL.md`
- Modify: `skills/work-issue/references/workflow-notes-template.md`
- Modify: `skills/using-go-ship-it/references/command-surface.md`
- Test: `tests/test_skills.py`

- [ ] **Step 1: Write failing skill/doc checks**

Add tests for required phrases: `verify-run --strict`, `status --json`, `acceptance criteria`, `what gets created`, and no new skill folders.

- [ ] **Step 2: Run focused tests to verify failure**

Run: `uv run pytest tests/test_skills.py -q`

Expected: new phrase checks fail.

- [ ] **Step 3: Update docs and skill references**

Add first-issue tutorial content, state artifact explanation, evidence-before-cleanup checklist, and maintainer guidance that skill changes need pressure scenarios or dogfood notes.

- [ ] **Step 4: Run focused tests to verify pass**

Run: `uv run pytest tests/test_skills.py -q`

Expected: skill/doc checks pass.

### Task 5: Full Verification And Dogfood Record

**Files:**
- Create: `docs/dogfood/issue-019-readiness-first-issue-polish.md`

- [ ] **Step 1: Run focused test suites**

Run: `uv run pytest tests/test_verify_run.py tests/test_cli_smoke.py tests/test_skills.py -q`

Expected: focused suites pass.

- [ ] **Step 2: Run full release gate**

Run: `just release-check`

Expected: full test suite, doctor, build, packaged install, and agent CLI validation pass.

- [ ] **Step 3: Write dogfood report**

Record what changed, commands run, rough edges, and deferred product questions.

- [ ] **Step 4: Commit**

Run: `git add ... && git commit -m "Improve readiness and first-issue onboarding"`.
