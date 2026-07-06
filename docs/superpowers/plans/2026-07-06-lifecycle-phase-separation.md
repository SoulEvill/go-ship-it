# Lifecycle Phase Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace GoShipit's loose phase string and monolithic close-out with a strict 8-value phase enum, per-phase contract docs, a new `close-out` skill, pluggable inner-loop/review-pipeline fields, a `track: quick|standard` fast path, and hard gates at publish/archive.

**Architecture:** All lifecycle state stays in `run.yaml` + issue frontmatter (files, not a database). `state.py` owns the enum and validation; `verify.py` becomes track/publish-aware; `pull_request.py` gains the absolute publish gate; `cli.py`'s hardcoded next-command ladder is rewritten enum+track aware. Skills go 3 → 4 (`close-out` extracted from `work-issue`), each phase gets one contract ref-doc (Inputs → Outputs → Evidence → Gate), and drift tests bind docs to the enum constants.

**Tech Stack:** Python 3.11+, pytest, PyYAML. No new dependencies.

**Spec:** `docs/design/lifecycle-phase-separation.md` (committed on this branch) — especially §6 decisions, §7 architecture, §8 resolutions (a)–(i).

## Global Constraints

- **FORWARD-ONLY (spec §8 (i)):** NO backward compatibility, NO legacy phase mapping, NO deprecation shims, NO override/force flags on gates, NO fallbacks. Delete tests that only pin old behavior. A default value for a missing optional field (e.g. `track` defaults to `standard`) is a default, not a compat shim — those are fine.
- Working directory for ALL commands: the issue worktree `/Users/zhengisamazing/1.python_dir/go_ship_it_working_dir/go-ship-it/worktrees/go-ship-it/issue-005` (branch `go-ship-it/issue-005`).
- Test command: `uv run pytest -q` (full suite) and `uv run pytest tests/<file>.py -q` (targeted). The FULL suite must pass at the end of every task before committing.
- New phase enum, exact order: `setup, investigate, propose, implement, review, prepare-pr, publish, archived`. The strings `test` and `cleanup` must not survive anywhere as phase values (they remain valid as a *check name* (`run-check --check test`) and a *command name* (`cleanup-issue`)).
- Commit after every task with a conventional-commit message; end each commit message with:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
- Do not modify anything outside this worktree. Never touch the control root's `state/` directory.
- Match existing code style: private helpers prefixed `_`, dataclasses frozen, `GoShipitError` for domain errors, `ValueError` for bad arguments.

---

### Task 1: Phase enum swap in state.py + ripple updates

**Files:**
- Modify: `src/go_ship_it/state.py` (lines 26, 782–815 `run_check`, 907–921 `cleanup_issue`, 1724–1739 `_write_run_cleanup`, 1777–1782 `_validate_phase`)
- Modify: `src/go_ship_it/verify.py` (line 202–206 `_export_is_stale`)
- Modify: `tests/test_state.py`, `tests/test_verify_run.py`, `tests/test_export_run.py`, `tests/test_cli_smoke.py`, `tests/test_evidence.py` (phase-string ripple)
- Test: `tests/test_evidence.py` (new enum tests live beside the existing `set_phase` tests)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `PHASES: tuple[str, ...]` module constant in `go_ship_it.state` with exact value `("setup", "investigate", "propose", "implement", "review", "prepare-pr", "publish", "archived")`. `_validate_phase(phase: str) -> str` accepting only those values. `run_check` labels notes with the run's *current* phase. `cleanup_issue`/`_write_run_cleanup` write phase `archived` (not `cleanup`) on archive. Every later task relies on `PHASES` existing under that name.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_evidence.py`:

```python
def test_phase_enum_accepts_all_lifecycle_phases(tmp_path):
    root = _issue_root(tmp_path)
    from go_ship_it.state import PHASES

    assert PHASES == (
        "setup",
        "investigate",
        "propose",
        "implement",
        "review",
        "prepare-pr",
        "publish",
        "archived",
    )
    for phase in ("review", "prepare-pr", "publish"):
        issue_file = set_phase(root, "sample/issue-001", phase, note=f"Entering {phase}.")
        assert issue_file.exists()


def test_phase_enum_rejects_retired_phase_names(tmp_path):
    root = _issue_root(tmp_path)
    for retired in ("test", "cleanup"):
        with pytest.raises(ValueError, match="phase must be one of"):
            set_phase(root, "sample/issue-001", retired, note="Nope.")
```

(`_issue_root` is this file's existing fixture helper that registers `sample` and starts `sample/issue-001` — reuse whatever that helper is actually named in the file; read the file first and copy the existing test setup pattern exactly.)

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `uv run pytest tests/test_evidence.py -q`
Expected: FAIL — `ImportError: cannot import name 'PHASES'` (or ValueError for `review`).

- [ ] **Step 3: Implement the enum in state.py**

Replace line 26 (`ALLOWED_PHASES = {...}`) with:

```python
PHASES = (
    "setup",
    "investigate",
    "propose",
    "implement",
    "review",
    "prepare-pr",
    "publish",
    "archived",
)
```

Replace `_validate_phase` (state.py:1777) with:

```python
def _validate_phase(phase: str) -> str:
    safe_phase = phase.strip().lower()
    if safe_phase not in PHASES:
        raise ValueError(f"phase must be one of: {', '.join(PHASES)}")
    return safe_phase
```

Remove every other reference to `ALLOWED_PHASES` (grep for it; it appears only in these two places).

- [ ] **Step 4: Update the retired-phase producers**

In `run_check` (state.py:782): the `_run_logged_command(...)` call currently passes `phase="test"`. Replace with the run's current phase, read strictly:

```python
    run_file = run_dir / "run.yaml"
    current_phase = _validate_phase(str(_load_run(run_file).get("phase") or ""))
```

(place the two lines just before the `_run_logged_command` call, and pass `phase=current_phase`).

In `cleanup_issue` (state.py:919): change `metadata["phase"] = "cleanup"` to `metadata["phase"] = "archived"`.

In `_write_run_cleanup` (state.py:1733): change `run["phase"] = "cleanup"` to:

```python
    run["phase"] = "archived" if destination == "archive" else "setup"
```

(`_write_run_cleanup` already receives `destination`.)

In `verify.py` `_export_is_stale` (line 203): change `export.get("run_phase") != "cleanup"` to `export.get("run_phase") != "archived"`.

- [ ] **Step 5: Fix the ripple in existing tests (forward-only: update, don't shim)**

Run `uv run pytest -q` and fix every failure by updating the *test* to the new enum. Known ripple points:
- `tests/test_verify_run.py:120-121` `_write_required_notes`: `set_phase(..., "test", ...)` → `"review"`; `append_note(..., phase="test", ...)` → `phase="review"`.
- `tests/test_state.py:656`: `assert metadata["phase"] == "cleanup"` → `"archived"`.
- `tests/test_export_run.py:99`: `assert export["run_phase"] == "cleanup"` → `"archived"`.
- `tests/test_cli_smoke.py:747,753`: `set-phase ... test` → `review` (the status-ladder assertions at 698–766 may still pass since the ladder itself is rewritten in Task 7 — only fix what fails NOW, with the old ladder emitting whatever it emits; if the ladder emits `set-phase {ref} test`, update the ladder's string literally from `test` to `review` and from the `"test"` phase-branch key to `"review"` as a minimal edit — the full rewrite happens in Task 7).
- Any other failure: same treatment — new enum value in, retired value out.

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS (all tests).

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "feat: replace free-phase set with strict 8-value lifecycle enum

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `track: quick|standard` field + `start-issue --quick` + `set-track` promotion

**Files:**
- Modify: `src/go_ship_it/state.py` (constants block ~line 26; `start_issue` ~532–666; new `set_track` function after `set_phase`)
- Modify: `src/go_ship_it/cli.py` (start-issue parser ~124; new set-track parser after set-phase parser ~161; main dispatch ~869 and after the set-phase branch ~905; import list ~17)
- Test: `tests/test_state.py` (append), `tests/test_cli_smoke.py` (append)

**Interfaces:**
- Consumes: `PHASES` from Task 1.
- Produces: `TRACKS = ("standard", "quick")` constant; `INNER_LOOPS = ("tdd", "debug", "spike", "none")` constant (declared here because quick-start records a default inner loop); `start_issue(root, issue_ref, *, claimed_by=None, track="standard")`; `set_track(root, issue_ref, track, *, note) -> Path` (quick→standard promotion only); quick runs start at phase `implement` (or `setup` first when a worktree-setup command exists) and record `inner_loop: tdd` in both `run.yaml` and issue frontmatter. `run.yaml` gains a `track:` key on every new run.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_state.py` (reuse this file's existing `register_repo`/`add_issue` fixture pattern — read it first):

```python
def test_start_issue_records_standard_track_by_default(tmp_path):
    root = _root_with_todo_issue(tmp_path)  # use the file's real helper for register+add
    run = start_issue(root, "sample/issue-001", claimed_by="t")
    run_data = yaml.safe_load(run.run_file.read_text())
    assert run_data["track"] == "standard"
    assert run_data["phase"] == "investigate"


def test_start_issue_quick_track_starts_at_implement_with_tdd_loop(tmp_path):
    root = _root_with_todo_issue(tmp_path)
    run = start_issue(root, "sample/issue-001", claimed_by="t", track="quick")
    run_data = yaml.safe_load(run.run_file.read_text())
    assert run_data["track"] == "quick"
    assert run_data["phase"] == "implement"
    assert run_data["inner_loop"] == "tdd"
    metadata, _body = parse_frontmatter(run.issue_file.read_text())
    assert metadata["track"] == "quick"
    assert metadata["inner_loop"] == "tdd"


def test_start_issue_rejects_unknown_track(tmp_path):
    root = _root_with_todo_issue(tmp_path)
    with pytest.raises(ValueError, match="track must be one of"):
        start_issue(root, "sample/issue-001", claimed_by="t", track="heavy")


def test_set_track_promotes_quick_to_standard(tmp_path):
    root = _root_with_todo_issue(tmp_path)
    run = start_issue(root, "sample/issue-001", claimed_by="t", track="quick")
    set_track(root, "sample/issue-001", "standard", note="Grew beyond a quick fix.")
    run_data = yaml.safe_load(run.run_file.read_text())
    assert run_data["track"] == "standard"
    metadata, _body = parse_frontmatter(run.issue_file.read_text())
    assert metadata["track"] == "standard"


def test_set_track_refuses_demotion(tmp_path):
    root = _root_with_todo_issue(tmp_path)
    start_issue(root, "sample/issue-001", claimed_by="t")
    with pytest.raises(GoShipitError, match="only promotes"):
        set_track(root, "sample/issue-001", "quick", note="Nope.")
```

Add the needed imports at the top of the test file (`set_track`, `GoShipitError`, `parse_frontmatter` from `go_ship_it.frontmatter`, `yaml`) if not already present. If the file has no reusable `_root_with_todo_issue`-style helper, write one locally in the test file following the exact pattern of `tests/test_verify_run.py::_started_issue_root` (git repo fixture + `register_repo` + `add_issue`), stopping before `start_issue`.

Append to `tests/test_cli_smoke.py` in the parser-assertion test (~line 178 area):

```python
    quick = parser.parse_args(["start-issue", "sample/issue-002", "--quick"])
    assert quick.quick is True
    track = parser.parse_args(["set-track", "sample/issue-002", "standard", "--note", "Promoted"])
    assert track.command == "set-track"
    assert track.track == "standard"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_state.py tests/test_cli_smoke.py -q`
Expected: FAIL — `ImportError: cannot import name 'set_track'`, unrecognized `--quick`.

- [ ] **Step 3: Implement in state.py**

Below `PHASES` add:

```python
TRACKS = ("standard", "quick")
INNER_LOOPS = ("tdd", "debug", "spike", "none")
```

Add validators next to `_validate_phase`:

```python
def _validate_track(track: str) -> str:
    safe_track = track.strip().lower()
    if safe_track not in TRACKS:
        raise ValueError(f"track must be one of: {', '.join(TRACKS)}")
    return safe_track
```

In `start_issue`: change the signature to `def start_issue(root: Path, issue_ref: str, *, claimed_by: str | None = None, track: str = "standard") -> StartedRun:` and at the top of the function body add `safe_track = _validate_track(track)`. Replace the `initial_phase` line (state.py:585) with:

```python
        if setup_command is not None:
            initial_phase = "setup"
        elif safe_track == "quick":
            initial_phase = "implement"
        else:
            initial_phase = "investigate"
        metadata["track"] = safe_track
        if safe_track == "quick":
            metadata["inner_loop"] = "tdd"
```

In the `run_file.write_text(_render_mapping({...}))` mapping, add `"track": safe_track,` after `"phase": initial_phase,` and, when quick, `"inner_loop": "tdd"`. Since the mapping is a literal dict, build it first:

```python
        run_values: dict[str, object] = {
            "issue_id": safe_issue_id,
            "repo": repo_id,
            "branch": branch,
            "worktree": worktree_relative.as_posix(),
            "claimed_by": resolved_claimed_by,
            "claim_id": claim_id,
            "phase": initial_phase,
            "track": safe_track,
            "started_at": timestamp,
            "last_activity_at": timestamp,
        }
        if safe_track == "quick":
            run_values["inner_loop"] = "tdd"
        run_file.write_text(_render_mapping(run_values))
```

At the post-setup transition (state.py:665) replace `"investigate"` with:

```python
        _write_active_phase(
            execution_file,
            run_dir / "run.yaml",
            "implement" if safe_track == "quick" else "investigate",
        )
```

Add `set_track` directly after `set_phase`:

```python
def set_track(root: Path, issue_ref: str, track: str, *, note: str) -> Path:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    safe_track = _validate_track(track)
    issue_file = _active_issue_file(root, repo_id, issue_id)
    run_dir = _run_dir(root, repo_id, issue_id)
    run_file = run_dir / "run.yaml"

    run = _load_run(run_file)
    current = str(run.get("track") or "standard")
    if not (current == "quick" and safe_track == "standard"):
        raise GoShipitError(
            f"set-track only promotes quick to standard; run is on track '{current}'"
        )

    metadata, body = parse_frontmatter(issue_file.read_text())
    timestamp = _now_iso()
    metadata["track"] = safe_track
    metadata["last_activity_at"] = timestamp
    issue_file.write_text(render_frontmatter(metadata, body))

    run["track"] = safe_track
    run["last_activity_at"] = timestamp
    run_file.write_text(_render_mapping(run))

    _append_note_to_notes(run_dir / "notes.md", section=f"Track: {safe_track}", note=note, phase=None)
    _append_event(
        run_dir,
        "track.changed",
        f"track={safe_track}",
        timestamp=timestamp,
        track=safe_track,
    )
    return issue_file
```

- [ ] **Step 4: Implement in cli.py**

Parser — extend `start-issue` (cli.py:124):

```python
    start.add_argument("--track", choices=["standard", "quick"], default=None)
    start.add_argument("--quick", action="store_true", help="Shorthand for --track quick.")
```

Add a `set-track` parser directly after the `set-phase` parser block (cli.py:161):

```python
    track_cmd = subparsers.add_parser("set-track", help="Promote an issue's track (quick -> standard).")
    track_cmd.add_argument("issue_id", nargs="?")
    track_cmd.add_argument("track", nargs="?")
    track_cmd.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    track_cmd.add_argument("--note", required=True)
```

Generalize the positional-shuffle resolver: rename `_resolve_phase_target(root, args)` to `_resolve_positional_target(root, args, attr: str)` where `phase = getattr(args, attr)` replaces `args.phase` and the required-error message becomes `f"{attr} is required"`. Update the set-phase dispatch to call `_resolve_positional_target(root, args, "phase")`.

Dispatch — in `main`, update the `start-issue` branch:

```python
        if args.command == "start-issue":
            if args.quick and args.track == "standard":
                raise ValueError("Cannot combine --quick with --track standard")
            track = "quick" if args.quick else (args.track or "standard")
            run = start_issue(root, args.issue_id, claimed_by=args.claimed_by, track=track)
```

Add a `set-track` branch after `set-phase`:

```python
        if args.command == "set-track":
            target_root, issue_id, track = _resolve_positional_target(root, args, "track")
            issue_file = set_track(target_root, issue_id, track, note=args.note)
            print(issue_file)
            return 0
```

Add `set_track` to the `from go_ship_it.state import (...)` list.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: add track quick|standard with start-issue --quick and set-track promotion

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Pluggable-axis fields — `--inner-loop` at implement-entry, `--review-pipeline` at review-entry

**Files:**
- Modify: `src/go_ship_it/state.py` (`set_phase` ~752–779; constants block; validators)
- Modify: `src/go_ship_it/cli.py` (set-phase parser ~156–160; set-phase dispatch)
- Test: `tests/test_evidence.py` (append)

**Interfaces:**
- Consumes: `PHASES`, `INNER_LOOPS` (Task 2 declared it), `set_phase`.
- Produces: `REVIEW_PIPELINES = ("self", "clean-room")` constant (plus the `plugin:<name>` prefix form); `set_phase(root, issue_ref, phase, *, note, inner_loop=None, inner_loop_reason=None, review_pipeline=None)`. Entering `implement` records `inner_loop` (default `tdd`; `none` requires a reason). Entering `review` records `review_pipeline` (default `self`). Both are written to `run.yaml` AND issue frontmatter.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_evidence.py`:

```python
def test_entering_implement_records_default_tdd_inner_loop(tmp_path):
    root = _issue_root(tmp_path)
    set_phase(root, "sample/issue-001", "implement", note="Building.")
    run = yaml.safe_load(_run_file(root).read_text())
    assert run["inner_loop"] == "tdd"


def test_entering_implement_with_none_loop_requires_reason(tmp_path):
    root = _issue_root(tmp_path)
    with pytest.raises(ValueError, match="requires --inner-loop-reason"):
        set_phase(root, "sample/issue-001", "implement", note="Building.", inner_loop="none")
    set_phase(
        root,
        "sample/issue-001",
        "implement",
        note="Docs only.",
        inner_loop="none",
        inner_loop_reason="Docs-only change; no executable behavior.",
    )
    run = yaml.safe_load(_run_file(root).read_text())
    assert run["inner_loop"] == "none"
    assert run["inner_loop_reason"] == "Docs-only change; no executable behavior."


def test_entering_review_records_default_self_pipeline(tmp_path):
    root = _issue_root(tmp_path)
    set_phase(root, "sample/issue-001", "review", note="Reviewing.")
    run = yaml.safe_load(_run_file(root).read_text())
    assert run["review_pipeline"] == "self"


def test_review_pipeline_accepts_plugin_form_and_rejects_junk(tmp_path):
    root = _issue_root(tmp_path)
    set_phase(root, "sample/issue-001", "review", note="R.", review_pipeline="plugin:code-review")
    run = yaml.safe_load(_run_file(root).read_text())
    assert run["review_pipeline"] == "plugin:code-review"
    with pytest.raises(ValueError, match="review_pipeline"):
        set_phase(root, "sample/issue-001", "review", note="R.", review_pipeline="vibes")
    with pytest.raises(ValueError, match="review_pipeline"):
        set_phase(root, "sample/issue-001", "review", note="R.", review_pipeline="plugin:")


def test_axis_flags_rejected_outside_their_phase(tmp_path):
    root = _issue_root(tmp_path)
    with pytest.raises(ValueError, match="inner-loop"):
        set_phase(root, "sample/issue-001", "propose", note="P.", inner_loop="tdd")
    with pytest.raises(ValueError, match="review-pipeline"):
        set_phase(root, "sample/issue-001", "implement", note="I.", review_pipeline="self")
```

Add a tiny local helper if the file lacks one: `_run_file(root)` returning `root / "state/repos/sample/issues/execution/issue-001/run.yaml"`. Import `yaml`.

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_evidence.py -q`
Expected: FAIL — unexpected keyword argument `inner_loop`.

- [ ] **Step 3: Implement in state.py**

Below `INNER_LOOPS` add:

```python
REVIEW_PIPELINES = ("self", "clean-room")
```

Validators next to `_validate_track`:

```python
def _validate_inner_loop(value: str) -> str:
    safe_value = value.strip().lower()
    if safe_value not in INNER_LOOPS:
        raise ValueError(f"inner_loop must be one of: {', '.join(INNER_LOOPS)}")
    return safe_value


def _validate_review_pipeline(value: str) -> str:
    safe_value = value.strip()
    if safe_value in REVIEW_PIPELINES:
        return safe_value
    if safe_value.startswith("plugin:") and len(safe_value) > len("plugin:"):
        return safe_value
    allowed = ", ".join((*REVIEW_PIPELINES, "plugin:<name>"))
    raise ValueError(f"review_pipeline must be one of: {allowed}")
```

Rewrite `set_phase`:

```python
def set_phase(
    root: Path,
    issue_ref: str,
    phase: str,
    *,
    note: str,
    inner_loop: str | None = None,
    inner_loop_reason: str | None = None,
    review_pipeline: str | None = None,
) -> Path:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    safe_phase = _validate_phase(phase)
    if safe_phase != "implement" and (inner_loop is not None or inner_loop_reason is not None):
        raise ValueError("--inner-loop/--inner-loop-reason only apply when entering the implement phase")
    if safe_phase != "review" and review_pipeline is not None:
        raise ValueError("--review-pipeline only applies when entering the review phase")

    axis_values: dict[str, object] = {}
    if safe_phase == "implement":
        loop = _validate_inner_loop(inner_loop or "tdd")
        if loop == "none" and not (inner_loop_reason and inner_loop_reason.strip()):
            raise ValueError("inner_loop 'none' requires --inner-loop-reason recording why no test loop is used")
        axis_values["inner_loop"] = loop
        if inner_loop_reason and inner_loop_reason.strip():
            axis_values["inner_loop_reason"] = inner_loop_reason.strip()
    if safe_phase == "review":
        axis_values["review_pipeline"] = _validate_review_pipeline(review_pipeline or "self")

    issue_file = _active_issue_file(root, repo_id, issue_id)
    run_dir = _run_dir(root, repo_id, issue_id)
    run_file = run_dir / "run.yaml"

    metadata, body = parse_frontmatter(issue_file.read_text())
    timestamp = _now_iso()
    metadata["phase"] = safe_phase
    metadata.update(axis_values)
    metadata["last_activity_at"] = timestamp
    issue_file.write_text(render_frontmatter(metadata, body))

    run = _load_run(run_file)
    run["phase"] = safe_phase
    run.update(axis_values)
    run["last_activity_at"] = timestamp
    run_file.write_text(_render_mapping(run))

    note_timestamp = _append_note_to_notes(run_dir / "notes.md", section=f"Phase: {safe_phase}", note=note, phase=safe_phase)
    _append_event(
        run_dir,
        "phase.changed",
        f"phase={safe_phase}",
        timestamp=timestamp,
        phase=safe_phase,
        note_timestamp=note_timestamp,
        **axis_values,
    )
    return issue_file
```

- [ ] **Step 4: Wire cli.py**

Extend the set-phase parser (cli.py:156):

```python
    phase.add_argument("--inner-loop", dest="inner_loop", choices=list(INNER_LOOPS), default=None,
                       help="Record the implement inner loop (default tdd; 'none' requires --inner-loop-reason).")
    phase.add_argument("--inner-loop-reason", dest="inner_loop_reason", default=None)
    phase.add_argument("--review-pipeline", dest="review_pipeline", default=None,
                       help="Record the review pipeline: self, clean-room, or plugin:<name>.")
```

Import `INNER_LOOPS` from `go_ship_it.state`. Update the set-phase dispatch:

```python
        if args.command == "set-phase":
            target_root, issue_id, phase = _resolve_positional_target(root, args, "phase")
            issue_file = set_phase(
                target_root,
                issue_id,
                phase,
                note=args.note,
                inner_loop=args.inner_loop,
                inner_loop_reason=args.inner_loop_reason,
                review_pipeline=args.review_pipeline,
            )
            print(issue_file)
            return 0
```

- [ ] **Step 5: Full suite, then commit**

Run: `uv run pytest -q` → PASS.

```bash
git add -A && git commit -m "feat: record pluggable inner_loop and review_pipeline at phase entry

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Terminal archive gate + close-out phase transitions

**Files:**
- Modify: `src/go_ship_it/state.py` (`cleanup_issue` ~870)
- Modify: `src/go_ship_it/cli.py` (cleanup parser ~128; cleanup dispatch ~882)
- Modify: `src/go_ship_it/pull_request.py` (`prepare_pull_request`, `publish_pull_request`)
- Test: `tests/test_state.py`, `tests/test_pull_request.py` (append), plus ripple (`confirm_archive=True` in every existing archive-destination call across the test suite)

**Interfaces:**
- Consumes: `PHASES`, `_write_active_phase` (already exists in state.py).
- Produces: `cleanup_issue(..., confirm_archive: bool = False)` — archiving without `confirm_archive=True` raises `GoShipitError` mentioning "terminal"; CLI flag `--confirm`. `prepare_pull_request` moves an execution-status issue to phase `prepare-pr`; `publish_pull_request` moves it to phase `publish` on success. Later tasks (7, 8) rely on these phases actually being set.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_state.py`:

```python
def test_archive_without_confirm_is_refused_as_terminal(tmp_path):
    root = _root_with_started_issue(tmp_path)  # reuse/adapt the file's existing started-issue helper
    with pytest.raises(GoShipitError, match="terminal"):
        cleanup_issue(root, "sample/issue-001", destination="archive", note="Done.", remove_worktree=False)


def test_archive_with_confirm_succeeds_and_sets_archived_phase(tmp_path):
    root = _root_with_started_issue(tmp_path)
    issue_file = cleanup_issue(
        root,
        "sample/issue-001",
        destination="archive",
        note="Done.",
        remove_worktree=False,
        confirm_archive=True,
    )
    metadata, _body = parse_frontmatter(issue_file.read_text())
    assert metadata["phase"] == "archived"


def test_return_to_todo_needs_no_confirm(tmp_path):
    root = _root_with_started_issue(tmp_path)
    issue_file = cleanup_issue(
        root,
        "sample/issue-001",
        destination="todo",
        note="Later.",
        remove_worktree=True,
    )
    assert issue_file.exists()
```

Append to `tests/test_pull_request.py` (reuse its existing fixtures for a prepared repo/issue — read the file first and copy its setup helper):

```python
def test_prepare_pr_moves_active_issue_to_prepare_pr_phase(tmp_path):
    root = _prepared_root(tmp_path)  # the file's existing helper that registers, starts, commits work
    prepare_pull_request(root, ISSUE_REF, branch="feature/sample")
    run = yaml.safe_load((_run_dir(root) / "run.yaml").read_text())
    assert run["phase"] == "prepare-pr"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_state.py tests/test_pull_request.py -q`
Expected: FAIL — unexpected keyword `confirm_archive`; phase still whatever it was.

- [ ] **Step 3: Implement the archive gate in state.py**

`cleanup_issue` signature gains `confirm_archive: bool = False` (after `discard_worktree_changes`). Directly after the existing destination validation (state.py:881–884) add:

```python
    if destination == "archive" and not confirm_archive:
        raise GoShipitError(
            "Archiving is terminal: there is no reopen or unarchive. "
            f"Re-run with --confirm to archive {issue_ref}."
        )
```

- [ ] **Step 4: Wire the CLI flag**

cleanup parser (cli.py:128):

```python
    cleanup.add_argument(
        "--confirm",
        action="store_true",
        help="Acknowledge that archiving is terminal (required with --destination archive).",
    )
```

Dispatch: pass `confirm_archive=args.confirm` to `cleanup_issue`.

- [ ] **Step 5: Implement close-out phase transitions in pull_request.py**

Add `_write_active_phase` to the existing `from go_ship_it.state import (...)` list. In `prepare_pull_request`, after the `_append_event(... "pull_request.prepared" ...)` call and before `return`:

```python
    if issue.summary.status == "execution":
        _write_active_phase(issue.summary.issue_file, run.run_file, "prepare-pr")
```

In `publish_pull_request`, after `_record_pull_request(run.run_file, {"published_url": ...})` and its `_append_event`, before `return`:

```python
    issue = show_issue(root, issue_ref)
    if issue.summary.status == "execution":
        _write_active_phase(issue.summary.issue_file, run.run_file, "publish")
```

- [ ] **Step 6: Fix the ripple**

Run `uv run pytest -q`. Every existing test that calls `cleanup_issue(..., destination="archive", ...)` must add `confirm_archive=True` (test_state.py, test_verify_run.py, test_export_run.py, test_navigation.py, test_cli_smoke.py, and any CLI-main invocation adds `"--confirm"` to its argv list). Update assertions that check status-ladder cleanup hints only if they fail (full rewrite comes in Task 7).

- [ ] **Step 7: Full suite, then commit**

Run: `uv run pytest -q` → PASS.

```bash
git add -A && git commit -m "feat: gate terminal archive behind --confirm and set prepare-pr/publish phases

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: `pull_request.provider: none` + track/publish-aware verify-run

**Files:**
- Modify: `src/go_ship_it/state.py` (`_validate_pull_request_config` ~456; new `TRACK_REQUIRED_NOTE_SECTIONS` constant)
- Modify: `src/go_ship_it/pull_request.py` (`publish_pull_request` provider check ~143)
- Modify: `src/go_ship_it/verify.py` (`verify_run`, `_check_notes`, new `_check_publish`)
- Test: `tests/test_repo_config.py` (append), `tests/test_verify_run.py` (append), `tests/test_pull_request.py` (append)

**Interfaces:**
- Consumes: `TRACKS` (Task 2), archive gate (Task 4).
- Produces: provider value `none` accepted in repo config and refused by `publish_pull_request` with a clear message; `TRACK_REQUIRED_NOTE_SECTIONS = {"standard": ("Investigation", "Proposal", "Implementation", "Review"), "quick": ("Implementation", "Review")}` exported from `state.py`; `verify_run` requires note sections per the run's track, errors on an unknown track value (`run.track_invalid`), and for archived issues adds finding codes `publish.recorded` (ok), `publish.not_required` (ok, provider none), `publish.missing` (warning). Task 6's gate and Task 7's ladder rely on these codes/semantics.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_repo_config.py` (copy its existing update_repo_config test pattern):

```python
def test_pull_request_provider_accepts_none(tmp_path):
    root = _registered_root(tmp_path)  # the file's existing register fixture
    update_repo_config(root, "sample", updates={"pull_request": {"provider": "none"}}, clears=set())
    config = read_repo_config(root, "sample")
    assert config["pull_request"]["provider"] == "none"


def test_pull_request_provider_rejects_unknown_values(tmp_path):
    root = _registered_root(tmp_path)
    with pytest.raises(ValueError, match="provider"):
        update_repo_config(root, "sample", updates={"pull_request": {"provider": "gitlab"}}, clears=set())
```

Append to `tests/test_verify_run.py`:

```python
def test_verify_run_quick_track_requires_only_implementation_and_review_notes(tmp_path):
    root = _started_issue_root(tmp_path, track="quick")
    set_phase(root, ISSUE_REF, "review", note="Reviewing.")
    append_note(root, ISSUE_REF, section="Implementation", phase="implement", note="Changed files.")
    append_note(root, ISSUE_REF, section="Review", phase="review", note="Ready.")
    run_check(root, ISSUE_REF, check="test")

    report = verify_run(root, ISSUE_REF)

    codes = {item.code for item in report.warnings}
    assert "notes.investigation_missing" not in codes
    assert "notes.proposal_missing" not in codes


def test_verify_run_standard_track_still_requires_all_four_sections(tmp_path):
    root = _started_issue_root(tmp_path)
    report = verify_run(root, ISSUE_REF)
    codes = {item.code for item in report.warnings}
    assert "notes.investigation_missing" in codes
    assert "notes.proposal_missing" in codes


def test_verify_run_warns_when_archived_without_published_pr(tmp_path):
    root = _started_issue_root(tmp_path)
    _write_required_notes(root, ISSUE_REF)
    run_check(root, ISSUE_REF, check="test")
    cleanup_issue(root, ISSUE_REF, destination="archive", note="Done.", remove_worktree=False, confirm_archive=True)

    report = verify_run(root, ISSUE_REF)

    assert any(item.code == "publish.missing" for item in report.warnings)


def test_verify_run_accepts_archive_without_publish_when_provider_none(tmp_path):
    root = _started_issue_root(tmp_path)
    update_repo_config(root, "sample", updates={"pull_request": {"provider": "none"}}, clears=set())
    _write_required_notes(root, ISSUE_REF)
    run_check(root, ISSUE_REF, check="test")
    cleanup_issue(root, ISSUE_REF, destination="archive", note="Done.", remove_worktree=False, confirm_archive=True)

    report = verify_run(root, ISSUE_REF)

    assert not any(item.code == "publish.missing" for item in report.warnings)
    assert any(item.code == "publish.not_required" for item in report.ok)
```

Extend `_started_issue_root` in that file with a `track: str = "standard"` keyword passed through to `start_issue`, and import `update_repo_config`.

Append to `tests/test_pull_request.py`:

```python
def test_publish_refuses_when_provider_is_none(tmp_path):
    root = _prepared_root(tmp_path)
    update_repo_config(root, REPO_ID, updates={"pull_request": {"provider": "none"}}, clears=set())
    prepare_pull_request(root, ISSUE_REF, branch="feature/sample")
    with pytest.raises(GoShipitError, match="no publish target"):
        publish_pull_request(root, ISSUE_REF, approved=True)
```

(Adapt fixture/constant names to the file's actual ones after reading it.)

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_repo_config.py tests/test_verify_run.py tests/test_pull_request.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement provider none**

state.py `_validate_pull_request_config`: replace the provider/remote loop with:

```python
def _validate_pull_request_config(config: dict[str, object]) -> None:
    provider = config.get("provider")
    if provider not in {"github", "none"}:
        raise ValueError("pull_request.provider must be 'github' or 'none'")
    remote = config.get("remote")
    if not isinstance(remote, str) or not remote.strip():
        raise ValueError("pull_request.remote must not be empty")
    if config.get("auto_publish") not in {True, False}:
        raise ValueError("pull_request.auto_publish must be true or false")
```

pull_request.py `publish_pull_request` provider check becomes:

```python
    provider = _required_record_string(record, "provider")
    if provider == "none":
        raise GoShipitError(
            "This repo has no publish target (pull_request.provider: none); "
            "archive after local pr.md sign-off instead"
        )
    if provider != "github":
        raise GoShipitError(f"Unsupported pull_request.provider: {provider}")
```

- [ ] **Step 4: Implement track/publish-aware verify**

state.py, below `REVIEW_PIPELINES`:

```python
TRACK_REQUIRED_NOTE_SECTIONS = {
    "standard": ("Investigation", "Proposal", "Implementation", "Review"),
    "quick": ("Implementation", "Review"),
}
```

verify.py: import additions —

```python
from go_ship_it.state import (
    TRACK_REQUIRED_NOTE_SECTIONS,
    pull_request_config,
    read_repo_config,
    show_issue,
    show_run,
)
```

In `verify_run`, after the run loads successfully:

```python
    track = str(run.run.get("track") or "standard")
    if track not in TRACK_REQUIRED_NOTE_SECTIONS:
        findings.append(_error("run.track_invalid", "run/track", f"Unknown track: {track}"))
        track = "standard"
    _check_run_metadata(findings, run.run)
    _check_notes(findings, run.notes, track)
    _check_commands(findings, run.commands)
    if issue is not None:
        _check_acceptance_criteria(findings, issue.body, run.notes, run.commands)
        _check_active_handoff(findings, root, run.run_file, issue.summary.status)
        _check_cleanup_and_exports(findings, root, issue_id, issue.summary.status, issue.metadata, run.run)
        _check_publish(findings, root, issue.summary.repo, issue.summary.status, run.run)
    return _report(findings)
```

`_check_notes` becomes:

```python
def _check_notes(findings: list[VerificationFinding], notes: str, track: str) -> None:
    for section in TRACK_REQUIRED_NOTE_SECTIONS[track]:
        if f"## {section}" in notes:
            findings.append(_ok(f"notes.{section.lower()}", f"notes/{section}", f"{section} note exists"))
        else:
            findings.append(
                _warning(f"notes.{section.lower()}_missing", f"notes/{section}", f"{section} note is missing")
            )
```

New `_check_publish` after `_check_cleanup_and_exports`:

```python
def _check_publish(
    findings: list[VerificationFinding],
    root: Path,
    repo_id: str,
    issue_status: str,
    run: dict[str, object],
) -> None:
    if issue_status != "archive":
        return
    try:
        provider = str(pull_request_config(read_repo_config(root, repo_id)).get("provider"))
    except (OSError, ValueError) as exc:
        findings.append(_warning("publish.config_unreadable", "publish", f"Repo PR config unreadable: {exc}"))
        return
    if provider == "none":
        findings.append(_ok("publish.not_required", "publish", "Repo has no publish target; local pr.md sign-off is the gate"))
        return
    record = run.get("pull_request")
    if isinstance(record, dict) and isinstance(record.get("published_url"), str) and record["published_url"].strip():
        findings.append(_ok("publish.recorded", "publish", f"Published: {record['published_url']}"))
    else:
        findings.append(_warning("publish.missing", "publish", "Archived without a published PR"))
```

- [ ] **Step 5: Full suite (fix any archive-test ripple from the new `publish.missing` warning — existing tests assert on specific codes, not warning counts, so expect little), then commit**

Run: `uv run pytest -q` → PASS.

```bash
git add -A && git commit -m "feat: provider none + track- and publish-aware verify-run

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Absolute publish gate — verify-run must be clean, no override

**Files:**
- Modify: `src/go_ship_it/pull_request.py` (`publish_pull_request`)
- Test: `tests/test_pull_request.py` (append)

**Interfaces:**
- Consumes: `verify_run` semantics from Task 5.
- Produces: `publish_pull_request` raises `GoShipitError` (message starts "Cannot publish: verify-run") when the report has ANY errors or warnings. There is deliberately NO flag to bypass this (spec §8 (e)).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pull_request.py`:

```python
def test_publish_blocks_when_verify_run_has_findings(tmp_path):
    root = _prepared_root(tmp_path)  # a run without notes/handoff => verify warnings exist
    prepare_pull_request(root, ISSUE_REF, branch="feature/sample")
    with pytest.raises(GoShipitError, match="Cannot publish: verify-run"):
        publish_pull_request(root, ISSUE_REF, approved=True)
```

If the file's existing publish-path tests build a fully-mocked `gh`/git flow, place this test before any mock so it fails on the gate (the gate must run before `git push`).

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_pull_request.py -q`
Expected: the new test FAILS (publish proceeds to git/gh and errors differently, or succeeds against the fixture).

- [ ] **Step 3: Implement the gate**

pull_request.py: add `from go_ship_it.verify import verify_run` (verify imports only state — no cycle). In `publish_pull_request`, insert immediately after `_require_commits_ahead(worktree, base)` and before the `git push`:

```python
    report = verify_run(root, run.issue_ref)
    blockers = [*report.errors, *report.warnings]
    if blockers:
        sample = "; ".join(f"{item.code}: {item.message}" for item in blockers[:5])
        raise GoShipitError(
            f"Cannot publish: verify-run found {report.error_count} errors and "
            f"{report.warning_count} warnings. Fix the evidence and rerun. First findings: {sample}"
        )
```

- [ ] **Step 4: Fix ripple**

Any existing test that expected publish to succeed must now first satisfy verify-run (write the four notes sections, pass `run-check --check test`, write handoff, add acceptance evidence — copy the `_write_required_notes` + `write_handoff` pattern from `tests/test_verify_run.py`). Update those fixtures rather than weakening the gate. Note the acceptance-evidence warning: the fixture issue's acceptance criterion text must literally appear in a note (see `tests/test_verify_run.py::test_verify_run_accepts_acceptance_criteria_with_evidence`).

- [ ] **Step 5: Full suite, then commit**

Run: `uv run pytest -q` → PASS.

```bash
git add -A && git commit -m "feat: hard-block publish-pr on any verify-run finding (no override)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Rewrite the status next-command ladder (enum + track + provider aware)

**Files:**
- Modify: `src/go_ship_it/cli.py` (`_active_issue_next_commands` ~744–793; import `pull_request_config` from state)
- Test: `tests/test_cli_smoke.py` (rewrite the ladder assertions ~690–850)

**Interfaces:**
- Consumes: `PHASES`, track field (`show_run(...).run.get("track")`), `pull_request_config`, `--confirm` flag, prepare-pr/publish phases.
- Produces: `_active_issue_next_commands(root, item) -> list[str]` emitting the ladder below. Task 8's skills quote these same command shapes.

- [ ] **Step 1: Write the failing tests**

Replace/extend the ladder assertions in `tests/test_cli_smoke.py` (find the existing status-output tests around lines 690–850 and update in place):

```python
def test_status_ladder_quick_track_setup_goes_straight_to_implement(tmp_path, capsys):
    root = _status_root(tmp_path, track="quick")  # adapt the file's existing status fixture to accept track
    main(["--root", str(root), "status"])
    out = capsys.readouterr().out
    assert "go-ship-it set-phase sample/issue-001 implement" in out
    assert "set-phase sample/issue-001 investigate" not in out


def test_status_ladder_review_phase_offers_closeout_handoff(tmp_path, capsys):
    root = _status_root(tmp_path)
    set_phase(root, "sample/issue-001", "review", note="Reviewing.")
    main(["--root", str(root), "status"])
    out = capsys.readouterr().out
    assert "go-ship-it prepare-pr sample/issue-001 --branch <pr-branch>" in out
    assert "go-ship-it handoff sample/issue-001 --write" in out
    assert "cleanup-issue" not in out


def test_status_ladder_prepare_pr_phase_offers_publish(tmp_path, capsys):
    root = _status_root(tmp_path)
    set_phase(root, "sample/issue-001", "prepare-pr", note="PR drafted.")
    main(["--root", str(root), "status"])
    out = capsys.readouterr().out
    assert "go-ship-it publish-pr sample/issue-001 --approved" in out
    assert "cleanup-issue" not in out


def test_status_ladder_publish_phase_offers_confirmed_archive(tmp_path, capsys):
    root = _status_root(tmp_path)
    set_phase(root, "sample/issue-001", "publish", note="Published.")
    main(["--root", str(root), "status"])
    out = capsys.readouterr().out
    assert (
        "go-ship-it cleanup-issue sample/issue-001 --destination archive --confirm "
        "--note \"<note>\" --remove-worktree"
    ) in out
```

Also update every EXISTING assertion in this file that expects the old ladder (`set-phase ... test`, unconditional `cleanup-issue ...` hints without `--confirm`) to the new shapes — delete assertions that only pinned retired behavior.

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_cli_smoke.py -q`
Expected: new tests FAIL.

- [ ] **Step 3: Implement the ladder**

Add `pull_request_config` to the cli.py state-import list. Replace `_active_issue_next_commands` entirely:

```python
def _active_issue_next_commands(root: Path, item: object) -> list[str]:
    ref = _summary_ref(item)
    commands = [
        f"go-ship-it show-run {ref}",
        f"go-ship-it show-run {ref} --trace",
        f"go-ship-it show-run {ref} --handoff",
    ]
    track = "standard"
    try:
        track = str(show_run(root, ref).run.get("track") or "standard")
    except (OSError, ValueError):
        pass
    provider = "github"
    try:
        provider = str(pull_request_config(read_repo_config(root, item.repo)).get("provider"))
    except (OSError, ValueError):
        pass

    phase = (item.phase or "").strip().casefold()
    if phase in {"", "setup"}:
        if track == "quick":
            commands.append(f"go-ship-it set-phase {ref} implement --note \"<quick-track start>\"")
        else:
            commands.append(f"go-ship-it set-phase {ref} investigate --note \"<investigation started>\"")
    elif phase == "investigate":
        commands.extend(
            [
                f"go-ship-it append-note {ref} --section \"Investigation\" --for-phase investigate --note \"<findings>\"",
                f"go-ship-it set-phase {ref} propose --note \"<investigation summary>\"",
            ]
        )
    elif phase == "propose":
        commands.extend(
            [
                f"go-ship-it append-note {ref} --section \"Proposal\" --for-phase propose --note \"<proposal and acceptance-level failing test>\"",
                f"go-ship-it set-phase {ref} implement --inner-loop tdd --note \"<proposal accepted>\"",
            ]
        )
    elif phase == "implement":
        commands.extend(
            [
                f"go-ship-it append-note {ref} --section \"Implementation\" --for-phase implement --note \"<changed files and decisions>\"",
                f"go-ship-it set-phase {ref} review --note \"<ready for review>\"",
            ]
        )
    elif phase == "review":
        commands.append(
            f"go-ship-it append-note {ref} --section \"Review\" --for-phase review --note \"<review findings and readiness>\""
        )

    for check in _configured_checks(root, item.repo):
        commands.append(f"go-ship-it run-check {ref} --check {check}")

    if phase == "review":
        commands.extend(
            [
                f"go-ship-it handoff {ref} --write",
                f"go-ship-it export-run {ref}",
                f"go-ship-it prepare-pr {ref} --branch <pr-branch>",
            ]
        )
    if phase == "prepare-pr" and provider != "none":
        commands.append(f"go-ship-it publish-pr {ref} --approved")

    commands.append(f"go-ship-it verify-run {ref} --strict")
    if phase == "publish" or (phase == "prepare-pr" and provider == "none"):
        commands.append(
            f"go-ship-it cleanup-issue {ref} --destination archive --confirm --note \"<note>\" --remove-worktree"
        )
    if track == "quick":
        commands.append(f"go-ship-it set-track {ref} standard --note \"<why the issue grew>\"")
    return commands
```

- [ ] **Step 4: Full suite, then commit**

Run: `uv run pytest -q` → PASS.

```bash
git add -A && git commit -m "feat: enum/track/provider-aware status next-command ladder

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: close-out skill + work-issue shrink + per-phase contract docs + drift tests

**Files:**
- Create: `skills/close-out/SKILL.md`
- Create: `skills/close-out/references/phases/write-pr.md`, `skills/close-out/references/phases/publish.md`, `skills/close-out/references/phases/archive.md`
- Create: `skills/work-issue/references/phases/investigate.md`, `propose.md`, `implement.md`, `review.md`
- Create: `tests/test_phase_docs.py`
- Modify: `skills/work-issue/SKILL.md` (remove PR/publish/archive guidance; new review-phase commands; point to phase docs and to close-out)
- Modify: `skills/using-go-ship-it/SKILL.md` (Skill Routing: 3 operational skills)
- Modify: `skills/manage-issues/SKILL.md` (archive boundary note: archive goes through close-out; manage-issues keeps return-to-todo; add `--confirm` to its archive example)
- Modify: `references/lifecycle.md` (new phase ladder, tracks, gates)
- Modify: `tests/test_skills.py` (4-skill surface)

**Interfaces:**
- Consumes: everything above — the docs quote real flags (`--inner-loop`, `--review-pipeline`, `--confirm`, `--quick`, `set-track`) and the drift tests import `PHASES`, `TRACKS`, `INNER_LOOPS`, `REVIEW_PIPELINES` from `go_ship_it.state`.
- Produces: the 4-skill surface and the per-phase contract docs later tasks/dogfooding rely on.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_phase_docs.py`:

```python
from pathlib import Path

from go_ship_it.state import INNER_LOOPS, PHASES, REVIEW_PIPELINES, TRACKS

ROOT = Path(__file__).resolve().parents[1]

PHASE_DOCS = {
    "investigate": "skills/work-issue/references/phases/investigate.md",
    "propose": "skills/work-issue/references/phases/propose.md",
    "implement": "skills/work-issue/references/phases/implement.md",
    "review": "skills/work-issue/references/phases/review.md",
    "prepare-pr": "skills/close-out/references/phases/write-pr.md",
    "publish": "skills/close-out/references/phases/publish.md",
    "archived": "skills/close-out/references/phases/archive.md",
}


def test_every_lifecycle_phase_has_exactly_one_contract_doc():
    assert set(PHASE_DOCS) == set(PHASES) - {"setup"}


def test_phase_docs_follow_the_contract_template():
    for _phase, relative in sorted(PHASE_DOCS.items()):
        text = (ROOT / relative).read_text()
        for heading in ("## Inputs", "## Outputs", "## Evidence", "## Gate"):
            assert heading in text, f"{relative} missing {heading}"


def test_implement_doc_names_the_pluggable_inner_loops():
    text = (ROOT / PHASE_DOCS["implement"]).read_text()
    for loop in INNER_LOOPS:
        assert loop in text


def test_review_doc_names_the_pluggable_pipelines():
    text = (ROOT / PHASE_DOCS["review"]).read_text()
    for pipeline in REVIEW_PIPELINES:
        assert pipeline in text
    assert "plugin:" in text


def test_propose_doc_pins_the_acceptance_test_gate():
    text = (ROOT / PHASE_DOCS["propose"]).read_text()
    assert "acceptance-level failing test" in text


def test_archive_doc_warns_terminal():
    text = (ROOT / PHASE_DOCS["archived"]).read_text()
    assert "terminal" in text
    assert "--confirm" in text


def test_lifecycle_reference_matches_the_phase_enum():
    text = (ROOT / "references" / "lifecycle.md").read_text()
    assert " -> ".join(PHASES) in text
    for track in TRACKS:
        assert track in text
```

Update `tests/test_skills.py`:
- `SKILLS` gains `"close-out"`.
- `SKILL_REFERENCES` becomes:

```python
SKILL_REFERENCES = {
    "using-go-ship-it": ("references/command-surface.md",),
    "manage-issues": ("references/state-lifecycle.md",),
    "work-issue": (
        "references/workflow-notes-template.md",
        "references/phases/investigate.md",
        "references/phases/propose.md",
        "references/phases/implement.md",
        "references/phases/review.md",
    ),
    "close-out": (
        "references/phases/write-pr.md",
        "references/phases/publish.md",
        "references/phases/archive.md",
    ),
}
```

- `ORIENTATION_COMMANDS` gains `"close-out": ("go-ship-it show-run", "go-ship-it verify-run")`.
- `SKILL_COMMANDS` becomes:

```python
SKILL_COMMANDS = {
    "manage-issues": (
        "go-ship-it init",
        "go-ship-it add-issue",
        "go-ship-it start-issue",
        "go-ship-it cleanup-issue",
    ),
    "work-issue": (
        "go-ship-it set-phase",
        "go-ship-it append-note",
        "go-ship-it run-check",
        "go-ship-it handoff",
    ),
    "close-out": (
        "go-ship-it prepare-pr",
        "go-ship-it publish-pr",
        "go-ship-it cleanup-issue",
    ),
}
```

- Rename `test_bootstrap_skill_routes_to_two_operational_skills` → `test_bootstrap_skill_routes_to_three_operational_skills` and add `assert "`close-out`" in text`.
- `test_work_issue_skill_names_readiness_gate_and_acceptance_evidence`: keep the verify-run/acceptance/sub-agent assertions (they stay in work-issue's Review phase) but drop nothing else unless it fails.

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_phase_docs.py tests/test_skills.py -q`
Expected: FAIL — missing files.

- [ ] **Step 3: Write the seven phase contract docs**

Every doc uses this exact skeleton (fill each section with the phase's real content; no placeholders):

```markdown
# Phase: <phase-name>

One-sentence purpose.

## Inputs

- What must exist before entering (artifacts, prior-phase outputs, run state).

## Outputs

- The artifact(s) this phase produces (the contract later phases consume).

## Evidence

- The exact notes sections / command records / files that prove the phase ran.

## Gate

- What must be true (and who decides) before leaving this phase.
```

Required content per doc:
- `investigate.md` — Inputs: started run, issue.md problem/acceptance. Outputs: Investigation note (findings, validation boundary). Evidence: `## Investigation` note section. Gate: none (self-transition to propose).
- `propose.md` — Inputs: Investigation note. Outputs: Proposal note AND **the acceptance-level failing test** authored in the worktree (spec §8 (f): propose pre-approves the acceptance-level failing test(s) — the executable definition of done; per-task unit tests stay inside implement's loop). Evidence: `## Proposal` note naming the test file/command and its RED output. Gate: HUMAN — user approves proposal + acceptance test before `set-phase implement`.
- `implement.md` — Inputs: approved proposal + failing acceptance test. Outputs: code driving the test green. Evidence: `## Implementation` note; `inner_loop` recorded in run.yaml (`tdd | debug | spike | none`; `none` requires `--inner-loop-reason`, spec §8 (g)). Gate: acceptance test green before `set-phase review`. Mention that the methodology itself is pluggable and may come from the platform (e.g. a Superpowers-style TDD or debugging skill).
- `review.md` — Inputs: implemented change. Outputs: Review note with findings classified `auto-fix | no-op | ask-user` (only `ask-user` findings stop the human). Evidence: `## Review` note, `run-check` records, `review_pipeline` recorded (`self | clean-room | plugin:<name>`). Gate: `verify-run --strict` clean + independent checker verdict recorded; then hand off to the close-out skill.
- `write-pr.md` — Inputs: reviewed run, clean verify. Outputs: local `pr.md` (reversible; THIS doc is the single place to change PR shape/template). Evidence: `pull_request` record in run.yaml, phase `prepare-pr`. Gate: none — local and reversible; user reviews `pr.md`.
- `publish.md` — Inputs: user-reviewed `pr.md`. Outputs: pushed branch + created PR (`published_url`). Evidence: phase `publish`, `pull_request.published_url`. Gate: HUMAN — `publish-pr --approved` (or repo `auto_publish: true`); publish is mechanically blocked while verify-run has ANY findings — no override; repos with `pull_request.provider: none` skip this phase entirely.
- `archive.md` — Inputs: published PR (or provider `none` + signed-off `pr.md`). Outputs: issue moved to archive, phase `archived`. Evidence: cleanup metadata (`cleanup_destination`, `closed_at`), fresh export. Gate: HUMAN — archive is **terminal** (no reopen/unarchive); requires `cleanup-issue --destination archive --confirm`.

- [ ] **Step 4: Write `skills/close-out/SKILL.md`**

```markdown
---
name: close-out
description: Use when shipping a reviewed GoShipit issue: preparing the local PR preview, publishing the PR, or archiving the finished issue.
---

# Close Out

## When To Use

Use after `work-issue` finishes the review phase and `verify-run --strict` is clean.

Do not use for build work (investigate/propose/implement/review) — that is `work-issue`. Do not use for returning an issue to todo — that is `manage-issues`.

## Orientation

```sh
go-ship-it show-run <repo>/<issue-id>
go-ship-it verify-run <repo>/<issue-id> --strict
```

Use the resolved GoShipit command from `using-go-ship-it`. In this development checkout that is usually `uv run go-ship-it`.

## The Three Gates

Close-out is three separate gates, crossed in order, never bundled:

1. **prepare-pr** (reversible, local) — write the PR preview. Read `references/phases/write-pr.md`; edit only that contract to change PR shape.

```sh
go-ship-it prepare-pr <repo>/<issue-id> --branch <team-branch-name>
```

The first `prepare-pr` needs `--branch`; reruns reuse the recorded branch. This writes `pr.md` beside the run files, records the PR branch in `run.yaml`, and moves the phase to `prepare-pr`. Stop here and show the user `pr.md` and `evidence.md`.

2. **publish** (irreversible: pushes and opens a PR) — read `references/phases/publish.md`.

```sh
go-ship-it publish-pr <repo>/<issue-id> --approved
```

Run only after the user approves publishing (or `pull_request.auto_publish: true`). Publishing is mechanically blocked while `verify-run` reports any finding — there is no override; fix the evidence instead. Repos with `pull_request.provider: none` never publish: the reviewed local `pr.md` is their final gate.

3. **archive** (terminal: no reopen or unarchive) — read `references/phases/archive.md`.

```sh
go-ship-it export-run <repo>/<issue-id>
go-ship-it cleanup-issue <repo>/<issue-id> --destination archive --confirm --note "<final note>" --remove-worktree
```

Ask the user before archiving. Never bundle archive with publish in a single step. If the worktree has uncommitted changes, cleanup refuses to remove it; commit first or archive without `--remove-worktree` to preserve it for inspection.

## Failure Behavior

If any gate refuses (verify findings, dirty worktree, missing approval), stop, report the exact blocker, and leave the issue in execution.
```

(If `tests/test_skills.py::test_skill_frontmatter_is_trigger_focused` fails on the description's inner colon, YAML-quote the description string.)

- [ ] **Step 5: Shrink `skills/work-issue/SKILL.md` and update the other two skills + lifecycle reference**

work-issue edits:
- Frontmatter description: `Use when investigating, proposing, implementing, or reviewing an active GoShipit issue and recording its evidence.`
- Replace the "Test and review" command block with a "Review" block:

```sh
go-ship-it set-phase <repo>/<issue-id> review --note "<ready for review>"
go-ship-it set-phase <repo>/<issue-id> review --review-pipeline plugin:code-review --note "<ready for review>"
go-ship-it run-check <repo>/<issue-id> --check test
go-ship-it append-note <repo>/<issue-id> --section "Review" --for-phase review --note "<review findings and readiness>"
```

- Implementation block gains the entry contract: `set-phase <repo>/<issue-id> implement --inner-loop tdd --note "<proposal accepted>"` and a sentence: the acceptance-level failing test approved during propose is the entry ticket; `--inner-loop none` requires `--inner-loop-reason`.
- Proposal block gains: author the acceptance-level failing test in the worktree and record its RED output in the Proposal note; the user approves both before implement.
- Add one line pointing at the per-phase contracts: `Read references/phases/<phase>.md for each phase's contract (Inputs → Outputs → Evidence → Gate).`
- DELETE the prepare-pr/publish-pr/archive guidance (old lines 110–132 minus what the Review block keeps): keep `handoff --write`, `export-run`, `verify-run --strict` as the readiness gate, then end with: `When verify-run --strict is clean, hand off to the close-out skill for prepare-pr → publish → archive.`
- Keep the independent-checker paragraph (test_skills asserts `sub-agent` and `semantic done/not-done judgment`).
- Keep quick-track mention: on a `quick` track the run starts at implement; `set-track <repo>/<issue-id> standard` promotes it if it grows.

using-go-ship-it: in `## Skill Routing`, the list becomes three operational skills:

```markdown
- `manage-issues` when initializing a control root, registering a repo, creating a todo, starting work, checking status, or returning an active issue to todo.
- `work-issue` when investigating, proposing, implementing, or reviewing inside an active issue.
- `close-out` when shipping a reviewed issue: prepare the local PR, publish it, archive the issue.
```

manage-issues: in the Core Commands block change the archive example to include `--confirm`, and add one boundary sentence: `Archiving a finished issue is part of the close-out skill's three-gate flow; use cleanup-issue --destination todo here only for returning unfinished work.`

references/lifecycle.md: replace the phase ladder line with:

```text
setup -> investigate -> propose -> implement -> review -> prepare-pr -> publish -> archived
```

and add below it:

```markdown
Each issue runs on a `track`: `standard` requires every phase; `quick` skips investigate/propose
and starts at implement (promote with `go-ship-it set-track <repo>/<issue-id> standard`).
Both tracks cross the same close-out gates: prepare-pr (local, reversible), publish
(human-approved; blocked while verify-run has findings), archive (terminal; requires --confirm).
```

- [ ] **Step 6: No `.agents` step**

The `.agents/` scaffold is local-only and git-ignored (ef9cf2a); its existence tests were removed (see the fix commit after Task 1). Do not create anything under `.agents/` in the repo.

- [ ] **Step 7: Full suite, then commit**

Run: `uv run pytest -q` → PASS (test_skills, test_phase_docs, and everything else).

```bash
git add -A && git commit -m "feat: extract close-out skill and add per-phase contract docs with drift tests

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 9: Docs sweep + full green

**Files:**
- Modify: `README.md` (lifecycle/phase mentions), `docs/maintainers.md` (skill surface is now 4), `skills/using-go-ship-it/references/command-surface.md` (new commands/flags)
- Test: existing suite only (no new tests; `test_command_surface_mentions_json_and_strict_readiness`, `test_first_issue_docs_explain_what_gets_created`, `test_maintainer_notes_require_pressure_scenarios_for_skill_changes` must stay green)

**Interfaces:**
- Consumes: everything.
- Produces: consistent docs; the shipped branch.

- [ ] **Step 1: Sweep for retired vocabulary**

```bash
grep -rn "set-phase.*test\|phase.*cleanup\|investigate → propose → implement → test\|test -> cleanup\|test → cleanup" README.md docs/ skills/ references/ --include="*.md" | grep -v "docs/design/" | grep -v "docs/superpowers/" | grep -v "docs/dogfood/"
```

(Design/dogfood/plan records are history — leave them.) Update every live-doc hit to the new enum and flags. In `command-surface.md` add `set-track`, `start-issue --quick`, `set-phase --inner-loop/--review-pipeline`, `cleanup-issue --confirm` to the CLI list, keeping the strings its test asserts. In `docs/maintainers.md`, update the skill-surface sentence to name the four skills and note that close-out earned its slot via the distinct "gate" mental model (cite `docs/design/lifecycle-phase-separation.md`); keep the words "pressure scenario", "dogfood", "new skills".

- [ ] **Step 2: Full suite**

Run: `uv run pytest -q`
Expected: PASS, zero failures.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "docs: align README, maintainers, and command surface with the new lifecycle

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Post-plan (handled by the orchestrator, not plan tasks)

Three independent review sessions (correctness, design-conformance vs the spec incl. forward-only, skills/docs consistency), fixes, an end-to-end dogfood validation run recorded as GoShipit evidence, then close-out through the new three-gate flow.
