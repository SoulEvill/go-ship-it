# Repo-Centric State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each registered target repo own its issues and run evidence, while keeping code worktrees in the top-level `worktrees/` tree.

**Architecture:** The canonical issue identity is `<repo-id>/<issue-id>`. Issue lifecycle status comes from `state/repos/<repo-id>/issues/{todo,execution,archive}/`. Active run metadata, authored notes, handoff files, and generated logs live inside the execution issue folder at `state/repos/<repo-id>/issues/execution/<issue-id>/`. Worktrees remain under `worktrees/<repo-id>/<issue-id>/`. Issue frontmatter no longer stores repo or status because those values are path-derived.

**Tech Stack:** Python, pytest, YAML frontmatter, git worktree, existing GoShipit CLI.

---

### Task 1: State Layout and Identity

**Files:**
- Modify: `src/go_ship_it/state.py`
- Test: `tests/test_state.py`

- [x] Write failing tests that `ensure_layout()` creates only top-level control folders and `register_repo()` creates repo-local issue state folders.
- [x] Write failing tests that `add_issue()` writes `state/repos/<repo>/issues/todo/<issue>/issue.md` with no `repo` or `status` frontmatter.
- [x] Write failing tests that separate repos can both have `issue-001`.
- [x] Implement repo-local issue id generation and repo-owned issue/run path helpers.

### Task 2: Lifecycle Operations

**Files:**
- Modify: `src/go_ship_it/state.py`
- Test: `tests/test_state.py`, `tests/test_run_check.py`, `tests/test_evidence.py`, `tests/test_export_run.py`, `tests/test_trace.py`

- [x] Update failing tests to use canonical issue refs such as `sample/issue-001`.
- [x] Update start, current-run resolution, note/phase/check/cleanup/export/handoff operations to resolve repo and issue deterministically.
- [x] Keep current-run commands ergonomic by resolving `.go-ship-it/context.yaml` to the repo-owned execution issue folder.
- [x] Put generated records under `logs/` and keep authored narrative in `notes.md` and `handoff.md`.

### Task 3: CLI and Health Checks

**Files:**
- Modify: `src/go_ship_it/cli.py`, `src/go_ship_it/doctor.py`, `src/go_ship_it/verify.py`
- Test: `tests/test_cli_smoke.py`, `tests/test_doctor.py`, `tests/test_verify_run.py`, `tests/test_navigation.py`

- [x] Make explicit CLI issue arguments use `<repo>/<issue-id>`.
- [x] Keep `--current` and managed-worktree inference working without requiring explicit issue refs.
- [x] Update status, JSON payloads, doctor checks, and verify checks to display and validate repo-owned paths.

### Task 4: Docs, Skills, Scripts, and Cleanup

**Files:**
- Modify: `README.md`, `docs/`, `references/`, `skills/`, `scripts/`, `pyproject.toml`
- Delete: old global-state `.gitkeep` files under `state/issues/` and `state/runs/`

- [x] Replace user-facing path examples with repo-owned paths.
- [x] Update skills to teach `repo/issue-id` as the explicit issue handle.
- [x] Update packaged install and target e2e scripts for the new layout.
- [x] Remove old global state placeholders and references.

### Task 5: Verification

**Files:**
- Modify as needed based on failures.

- [x] Run focused tests for state, CLI, doctor, verify, evidence, export, and scripts.
- [x] Run `uv run pytest -q`.
- [x] Run `uv run go-ship-it doctor`.
- [x] Run `just release-check`.
- [x] Review `git diff --stat` and `rg "state/issues|state/runs"` to catch stale public docs; only dated dogfood evidence keeps legacy paths for history.
