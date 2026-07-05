from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from go_ship_it.frontmatter import parse_frontmatter, render_frontmatter
from go_ship_it.portable import portable_path_value, portable_text, relative_to_root


STATE_DIRS = (
    "state/repos",
    "worktrees",
)

ISSUE_STATES = ("todo", "execution", "archive")
ALLOWED_PHASES = {"setup", "investigate", "propose", "implement", "test", "cleanup"}
OPTIONAL_COMMAND_FIELDS = {"setup_command", "test_command", "lint_command"}
REQUIRED_REPO_FIELDS = {"id", "path", "default_branch", "worktree_root"}
UPDATABLE_REPO_FIELDS = REQUIRED_REPO_FIELDS | OPTIONAL_COMMAND_FIELDS


class GoShipitError(RuntimeError):
    pass


class CheckFailedError(GoShipitError):
    def __init__(self, check: str, exit_code: int, record_file: Path) -> None:
        super().__init__(f"{check} check failed with exit code {exit_code}; evidence={record_file}")
        self.check = check
        self.exit_code = exit_code
        self.record_file = record_file


class IssueAlreadyActiveError(GoShipitError):
    def __init__(
        self,
        issue_id: str,
        *,
        issue_file: Path | None,
        run_file: Path | None,
        worktree: str | None,
    ) -> None:
        parts = [f"{issue_id} already has an active run"]
        if issue_file is not None:
            parts.append(f"issue_path={issue_file}")
        if run_file is not None:
            parts.append(f"run_path={run_file}")
        if worktree is not None:
            parts.append(f"worktree={worktree}")
        super().__init__("; ".join(parts))
        self.issue_id = issue_id
        self.issue_file = issue_file
        self.run_file = run_file
        self.worktree = worktree


@dataclass(frozen=True)
class StartedRun:
    issue_id: str
    repo_id: str
    issue_ref: str
    branch: str
    worktree: Path
    issue_file: Path
    run_file: Path
    claim_id: str = ""
    claimed_by: str | None = None
    already_active: bool = False
    context_file: Path | None = None


@dataclass(frozen=True)
class CurrentRun:
    issue_id: str
    repo_id: str
    issue_ref: str
    control_root: Path
    worktree: Path
    branch: str
    run_file: Path
    context_file: Path
    claim_id: str
    claimed_by: str | None = None


@dataclass(frozen=True)
class IssueSummary:
    issue_id: str
    status: str
    repo: str
    title: str
    phase: str
    issue_file: Path


@dataclass(frozen=True)
class IssueDetail:
    summary: IssueSummary
    metadata: dict[str, object]
    body: str


@dataclass(frozen=True)
class RunDetail:
    issue_id: str
    repo_id: str
    issue_ref: str
    run_file: Path
    run: dict[str, object]
    notes: str
    commands: list[dict[str, object]]


@dataclass(frozen=True)
class RunEvent:
    timestamp: str
    kind: str
    detail: str


@dataclass(frozen=True)
class WorkspaceStatus:
    repo_count: int
    todo_count: int
    execution_count: int
    archive_count: int
    run_count: int
    active: list[IssueSummary]
    worktrees: list[str]


def ensure_layout(root: Path) -> None:
    for relative in STATE_DIRS:
        (root / relative).mkdir(parents=True, exist_ok=True)


def next_issue_id(root: Path, repo_id: str) -> str:
    safe_repo_id = _safe_id(repo_id)
    issue_dirs = tuple(_repo_issues_dir(root, safe_repo_id, state) for state in ISSUE_STATES)
    existing = [path for directory in issue_dirs for path in _collect_issue_dirs(directory)]
    existing.extend(_collect_issue_dirs(root / "worktrees" / safe_repo_id))
    next_number = max((_issue_number(path) for path in existing), default=0) + 1
    return f"issue-{next_number:03d}"


def register_repo(
    root: Path,
    *,
    repo_id: str,
    path: Path,
    default_branch: str,
    setup_command: str | None,
    test_command: str | None,
    lint_command: str | None,
) -> Path:
    ensure_layout(root)
    safe_repo_id = _safe_id(repo_id)
    repo_dir = _repo_dir(root, safe_repo_id)
    repo_dir.mkdir(parents=True, exist_ok=True)
    for state in ISSUE_STATES:
        _repo_issues_dir(root, safe_repo_id, state).mkdir(parents=True, exist_ok=True)
    repo_file = repo_dir / "repo.yaml"
    context_file = repo_dir / "context.md"
    values = {
        "id": safe_repo_id,
        "path": str(path),
        "default_branch": default_branch,
        "worktree_root": f"worktrees/{safe_repo_id}",
        "context_file": relative_to_root(root, context_file),
        "setup_command": setup_command,
        "test_command": test_command,
        "lint_command": lint_command,
    }
    repo_file.write_text(_render_mapping(values))
    if not context_file.exists():
        context_file.write_text(_repo_context_template(safe_repo_id))
    return repo_file


def read_repo_config(root: Path, repo_id: str) -> dict[str, object]:
    return _read_repo(root, repo_id)


def repo_config_files(root: Path, *, repo_id: str | None = None) -> list[Path]:
    repo_dir = root / "state" / "repos"
    if not repo_dir.exists():
        return []
    files = sorted(path for path in repo_dir.glob("*/repo.yaml") if path.is_file())
    if repo_id is not None:
        safe_repo_id = _safe_id(repo_id)
        files = [path for path in files if repo_config_id(path) == safe_repo_id]
    return files


def repo_config_id(repo_file: Path) -> str:
    return repo_file.parent.name


def repo_config_exists(root: Path, repo_id: str) -> bool:
    return _repo_file(root, repo_id).exists()


def list_issues(root: Path, *, state: str = "all", repo_id: str | None = None) -> list[IssueSummary]:
    if state != "all" and state not in ISSUE_STATES:
        raise ValueError("state must be one of: todo, execution, archive, all")

    states = ISSUE_STATES if state == "all" else (state,)
    repo_ids = [_safe_id(repo_id)] if repo_id is not None else [repo_config_id(path) for path in repo_config_files(root)]
    summaries: list[IssueSummary] = []

    for repo in repo_ids:
        for issue_state in states:
            directory = _repo_issues_dir(root, repo, issue_state)
            for issue_file in _collect_issue_files(directory):
                metadata, _body = parse_frontmatter(issue_file.read_text())
                summaries.append(
                    IssueSummary(
                        issue_id=_required_string(metadata, "id"),
                        status=issue_state,
                        repo=repo,
                        title=_required_string(metadata, "title"),
                        phase=str(metadata.get("phase") or ""),
                        issue_file=issue_file,
                    )
                )

    return sorted(summaries, key=lambda item: (item.repo, item.issue_id))


def show_issue(root: Path, issue_ref: str) -> IssueDetail:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    issue_file = _find_issue_file(root, repo_id, issue_id)
    if issue_file is None:
        raise FileNotFoundError(f"No issue found for {_issue_ref(repo_id, issue_id)}")

    metadata, body = parse_frontmatter(issue_file.read_text())
    summary = IssueSummary(
        issue_id=_required_string(metadata, "id"),
        status=issue_file.parent.parent.name,
        repo=repo_id,
        title=_required_string(metadata, "title"),
        phase=str(metadata.get("phase") or ""),
        issue_file=issue_file,
    )
    return IssueDetail(summary=summary, metadata=metadata, body=body.strip())


def show_run(root: Path, issue_ref: str) -> RunDetail:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    run_dir = _repo_run_dir(root, repo_id, issue_id)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    run_file = run_dir / "run.yaml"
    notes_file = run_dir / "notes.md"
    commands_dir = _logs_dir(run_dir) / "commands"
    commands = [
        _parse_mapping(command_file.read_text()) | {"record_file": command_file}
        for command_file in sorted(commands_dir.glob("*.yaml"))
    ] if commands_dir.exists() else []
    return RunDetail(
        issue_id=issue_id,
        repo_id=repo_id,
        issue_ref=_issue_ref(repo_id, issue_id),
        run_file=run_file,
        run=_load_run(run_file),
        notes=notes_file.read_text().strip() if notes_file.exists() else "",
        commands=commands,
    )


def run_timeline(root: Path, issue_ref: str) -> list[RunEvent]:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    run_dir = _repo_run_dir(root, repo_id, issue_id)
    return sorted(_read_events(run_dir), key=lambda event: event.timestamp)


def workspace_status(root: Path) -> WorkspaceStatus:
    _require_layout(root)
    repos = repo_config_files(root)
    todo = list_issues(root, state="todo")
    execution = list_issues(root, state="execution")
    archive = list_issues(root, state="archive")
    runs = [
        issue_dir
        for repo_file in repos
        for state in ISSUE_STATES
        for issue_dir in _collect_issue_dirs(_repo_issues_dir(root, repo_config_id(repo_file), state))
        if (issue_dir / "run.yaml").exists()
    ]
    worktrees_root = root / "worktrees"
    worktrees = [path.relative_to(worktrees_root).as_posix() for path in _collect_worktree_issue_dirs(worktrees_root)]
    return WorkspaceStatus(
        repo_count=len(repos),
        todo_count=len(todo),
        execution_count=len(execution),
        archive_count=len(archive),
        run_count=len(runs),
        active=execution,
        worktrees=worktrees,
    )


def _require_layout(root: Path) -> None:
    missing = [relative for relative in STATE_DIRS if not (root / relative).exists()]
    if missing:
        raise GoShipitError(
            "not an initialized GoShipit control repo: "
            f"{root}; missing {', '.join(missing)}. "
            "Run `go-ship-it init` in a new control root, or run from an existing "
            "GoShipit control root and pass --root <control-root> when needed."
        )


def update_repo_config(
    root: Path,
    repo_id: str,
    *,
    updates: dict[str, object],
    clears: set[str],
) -> Path:
    safe_repo_id = _safe_id(repo_id)
    repo_file = _repo_config_path(root, safe_repo_id)
    if not repo_file.exists():
        raise FileNotFoundError(_repo_not_found_message(root, safe_repo_id))

    unknown = (set(updates) | clears) - UPDATABLE_REPO_FIELDS
    if unknown:
        raise ValueError(f"Unknown repo config fields: {', '.join(sorted(unknown))}")

    invalid_clears = clears - OPTIONAL_COMMAND_FIELDS
    if invalid_clears:
        raise ValueError(f"Only command fields can be cleared: {', '.join(sorted(invalid_clears))}")

    config = _parse_mapping(repo_file.read_text())
    for key, value in updates.items():
        if key in REQUIRED_REPO_FIELDS and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{key} must not be empty")
        config[key] = value
    for key in clears:
        config[key] = None

    for key in REQUIRED_REPO_FIELDS:
        value = config.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must not be empty")

    repo_file.write_text(_render_mapping(config))
    return repo_file


def add_issue(
    root: Path,
    *,
    repo_id: str,
    title: str,
    problem: str,
    context: str,
    acceptance_criteria: list[str],
) -> Path:
    ensure_layout(root)
    safe_repo_id = _safe_id(repo_id)
    _read_repo(root, safe_repo_id)
    issue_id = next_issue_id(root, safe_repo_id)
    issue_dir = _repo_issue_dir(root, safe_repo_id, "todo", issue_id)
    issue_dir.mkdir(parents=True, exist_ok=False)
    issue_file = issue_dir / "issue.md"
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    metadata = {
        "id": issue_id,
        "phase": "setup",
        "title": title,
        "created_at": created_at,
        "worktree": None,
        "branch": None,
    }
    criteria = "\n".join(f"- {item}" for item in acceptance_criteria)
    body = (
        f"\n## Problem\n\n{problem.strip()}\n\n"
        f"## Context\n\n{context.strip()}\n\n"
        f"## Acceptance Criteria\n\n{criteria}\n"
    )
    issue_file.write_text(render_frontmatter(metadata, body))
    _append_event(issue_dir, "issue.created", title, created_at=created_at)
    return issue_file


def start_issue(root: Path, issue_ref: str, *, claimed_by: str | None = None) -> StartedRun:
    ensure_layout(root)
    repo_id, safe_issue_id = _parse_issue_ref(issue_ref)
    todo_dir = _repo_issue_dir(root, repo_id, "todo", safe_issue_id)
    todo_file = todo_dir / "issue.md"
    execution_dir = _repo_issue_dir(root, repo_id, "execution", safe_issue_id)
    execution_file = execution_dir / "issue.md"
    run_dir = execution_dir
    claim_dir = run_dir / "claim.lock"

    if execution_file.exists() or claim_dir.exists():
        return _existing_started_run(root, repo_id, safe_issue_id, execution_file, run_dir)
    if not todo_file.exists():
        raise FileNotFoundError(f"No todo issue found at {todo_file}")

    execution_dir.parent.mkdir(parents=True, exist_ok=True)
    todo_dir.rename(execution_dir)
    try:
        claim_dir.mkdir()
    except FileExistsError as exc:
        raise _active_run_error(safe_issue_id, execution_file, run_dir) from exc

    worktree_created = False
    target_repo: Path | None = None
    branch: str | None = None
    worktree: Path | None = None
    try:
        metadata, body = parse_frontmatter(execution_file.read_text())
        repo = _read_repo(root, repo_id)
        target_repo = _resolve_repo_path(root, repo.get("path"))
        _ensure_git_repo(target_repo)

        branch = f"go-ship-it/{safe_issue_id}"
        worktree_relative = Path(_required_string(repo, "worktree_root")) / safe_issue_id
        worktree = root / worktree_relative
        resolved_claimed_by = claimed_by or default_claimed_by(root)
        claim_id = _claim_id(root, safe_issue_id, worktree_relative)
        if worktree.exists():
            raise FileExistsError(f"Worktree path already exists: {worktree}")
        worktree.parent.mkdir(parents=True, exist_ok=True)
        _git(target_repo, "worktree", "add", "-b", branch, str(worktree), _required_string(repo, "default_branch"))
        worktree_created = True

        timestamp = _now_iso()
        metadata["phase"] = "investigate"
        metadata["branch"] = branch
        metadata["worktree"] = worktree_relative.as_posix()
        metadata["claimed_by"] = resolved_claimed_by
        metadata["claim_id"] = claim_id
        metadata["started_at"] = timestamp
        metadata["last_activity_at"] = timestamp
        execution_file.write_text(render_frontmatter(metadata, body))

        run_file = run_dir / "run.yaml"
        run_file.write_text(
            _render_mapping(
                {
                    "issue_id": safe_issue_id,
                    "repo": repo_id,
                    "branch": branch,
                    "worktree": worktree_relative.as_posix(),
                    "claimed_by": resolved_claimed_by,
                    "claim_id": claim_id,
                    "phase": "investigate",
                    "started_at": timestamp,
                    "last_activity_at": timestamp,
                }
            )
        )
        _append_event(
            run_dir,
            "run.started",
            f"branch={branch} worktree={worktree_relative.as_posix()}",
            timestamp=timestamp,
            branch=branch,
            worktree=worktree_relative.as_posix(),
            claim_id=claim_id,
            claimed_by=resolved_claimed_by,
        )
        context_file = _write_worktree_context(
            root,
            issue_id=safe_issue_id,
            repo_id=repo_id,
            branch=branch,
            worktree_relative=worktree_relative,
            claimed_by=resolved_claimed_by,
            claim_id=claim_id,
        )
        return StartedRun(
            issue_id=safe_issue_id,
            repo_id=repo_id,
            issue_ref=_issue_ref(repo_id, safe_issue_id),
            branch=branch,
            worktree=worktree,
            issue_file=execution_file,
            run_file=run_file,
            claim_id=claim_id,
            claimed_by=resolved_claimed_by,
            context_file=context_file,
        )
    except Exception:
        if worktree_created and target_repo is not None and worktree is not None:
            _remove_worktree(target_repo, worktree)
        if worktree_created and target_repo is not None and branch is not None:
            _delete_branch(target_repo, branch)
        shutil.rmtree(claim_dir, ignore_errors=True)
        if execution_dir.exists() and not todo_dir.exists():
            execution_dir.rename(todo_dir)
        raise


def default_claimed_by(root: Path) -> str:
    agent = _detect_agent()
    user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown-user"
    host = socket.gethostname().split(".", 1)[0] or "unknown-host"
    basis = f"{agent}|{user}|{host}|{root.resolve()}|{Path.cwd().resolve()}"
    digest = hashlib.sha256(basis.encode()).hexdigest()[:8]
    return f"{agent}:{user}@{host}:{digest}"


def resolve_current_run(cwd: Path | None = None) -> CurrentRun:
    start = (cwd or Path.cwd()).resolve()
    context_file = _find_worktree_context(start)
    if context_file is None:
        raise GoShipitError(
            "No GoShipit current run context found. "
            "Run this from a managed worktree or pass an explicit issue id."
        )

    context = _parse_mapping(context_file.read_text())
    issue_id = _safe_id(_required_string(context, "issue_id"))
    repo_id = _safe_id(_required_string(context, "repo_id"))
    control_root = Path(_required_string(context, "control_root")).expanduser().resolve()
    run_dir = Path(_required_string(context, "run_dir"))
    run_file = control_root / run_dir / "run.yaml"
    run = _load_run(run_file)

    claim_id = _required_string(context, "claim_id")
    run_claim_id = _required_string(run, "claim_id")
    if claim_id != run_claim_id:
        raise GoShipitError(
            f"current run claim mismatch for {issue_id}: context has {claim_id}, run has {run_claim_id}"
        )

    worktree_value = _required_string(run, "worktree")
    context_worktree = _required_string(context, "worktree")
    if context_worktree != worktree_value:
        raise GoShipitError(
            f"current run worktree mismatch for {issue_id}: context has {context_worktree}, run has {worktree_value}"
        )

    worktree = (control_root / worktree_value).resolve()
    try:
        context_file.resolve().relative_to(worktree)
    except ValueError as exc:
        raise GoShipitError(f"current run context is outside recorded worktree: {context_file}") from exc

    branch = _required_string(run, "branch")
    claimed_by_value = run.get("claimed_by")
    claimed_by = claimed_by_value if isinstance(claimed_by_value, str) else None
    return CurrentRun(
        issue_id=issue_id,
        repo_id=repo_id,
        issue_ref=_issue_ref(repo_id, issue_id),
        control_root=control_root,
        worktree=worktree,
        branch=branch,
        run_file=run_file.resolve(),
        context_file=context_file.resolve(),
        claim_id=run_claim_id,
        claimed_by=claimed_by,
    )


def append_note(root: Path, issue_ref: str, *, section: str, note: str, phase: str | None = None) -> Path:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    if phase is not None:
        _validate_phase(phase)
    _active_issue_file(root, repo_id, issue_id)
    run_dir = _run_dir(root, repo_id, issue_id)

    notes = run_dir / "notes.md"
    timestamp = _append_note_to_notes(notes, section=section, note=note, phase=phase)
    _append_event(
        run_dir,
        "note.appended",
        f"section={section.strip()}",
        timestamp=timestamp,
        section=section.strip(),
        phase=phase,
    )
    return notes


def set_phase(root: Path, issue_ref: str, phase: str, *, note: str) -> Path:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    safe_phase = _validate_phase(phase)
    issue_file = _active_issue_file(root, repo_id, issue_id)
    run_dir = _run_dir(root, repo_id, issue_id)
    run_file = run_dir / "run.yaml"

    metadata, body = parse_frontmatter(issue_file.read_text())
    timestamp = _now_iso()
    metadata["phase"] = safe_phase
    metadata["last_activity_at"] = timestamp
    issue_file.write_text(render_frontmatter(metadata, body))

    run = _load_run(run_file)
    run["phase"] = safe_phase
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
    )
    return issue_file


def run_check(root: Path, issue_ref: str, *, check: str) -> Path:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    safe_check = check.strip().lower()
    if safe_check not in {"setup", "test", "lint"}:
        raise ValueError("check must be one of: setup, test, lint")

    issue_file = _active_issue_file(root, repo_id, issue_id)
    run_dir = _run_dir(root, repo_id, issue_id)
    metadata, _body = parse_frontmatter(issue_file.read_text())
    repo = _read_repo(root, repo_id)
    command = repo.get(f"{safe_check}_command")
    if not isinstance(command, str) or not command.strip():
        raise GoShipitError(f"No {safe_check} command configured for repo {repo_id}")

    worktree_value = metadata.get("worktree")
    if not isinstance(worktree_value, str):
        raise ValueError("worktree must be a string")
    worktree = root / worktree_value
    if not worktree.is_dir():
        raise FileNotFoundError(f"Worktree not found: {worktree}")

    started_at = _now_iso()
    result = subprocess.run(
        command,
        cwd=worktree,
        shell=True,
        capture_output=True,
        check=False,
        text=True,
    )
    ended_at = _now_iso()

    commands_dir = _logs_dir(run_dir) / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    record_file = commands_dir / f"{_timestamp_slug(started_at)}-{safe_check}.yaml"
    record = {
        "check": safe_check,
        "command": command,
        "cwd": str(worktree),
        "exit_code": result.returncode,
        "stdout_tail": _tail(result.stdout),
        "stderr_tail": _tail(result.stderr),
        "started_at": started_at,
        "ended_at": ended_at,
    }
    record_file.write_text(_render_mapping(record))

    record_label = record_file.relative_to(run_dir).as_posix()
    note = f"Command: `{command}`\n\nExit code: {result.returncode}\n\nLog: `{record_label}`"
    _append_note_to_notes(run_dir / "notes.md", section=f"Check: {safe_check}", note=note, phase="test")
    _append_event(
        run_dir,
        f"check.{safe_check}",
        f"exit={result.returncode} command={command}",
        timestamp=started_at,
        check=safe_check,
        command=command,
        exit_code=result.returncode,
        record_file=record_label,
    )

    if result.returncode != 0:
        raise CheckFailedError(safe_check, result.returncode, record_file)
    return record_file


def cleanup_issue(
    root: Path,
    issue_ref: str,
    *,
    destination: str,
    note: str,
    remove_worktree: bool,
) -> Path:
    ensure_layout(root)
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    if destination not in {"todo", "archive"}:
        raise ValueError("destination must be 'todo' or 'archive'")
    if destination == "todo" and not remove_worktree:
        raise ValueError("returning an issue to todo requires remove_worktree=True")

    execution_dir = _repo_issue_dir(root, repo_id, "execution", issue_id)
    execution_file = execution_dir / "issue.md"
    if not execution_file.exists():
        raise FileNotFoundError(f"No execution issue found at {execution_file}")

    metadata, body = parse_frontmatter(execution_file.read_text())
    repo = _read_repo(root, repo_id)
    target_repo = _resolve_repo_path(root, repo.get("path"))
    worktree_value = metadata.get("worktree")
    branch_value = metadata.get("branch")
    timestamp = _now_iso()

    if remove_worktree and isinstance(worktree_value, str):
        worktree = root / worktree_value
        if _is_managed_worktree(root, worktree) and worktree.exists():
            _ensure_git_repo(target_repo)
            _remove_worktree(target_repo, worktree)
            metadata["worktree"] = None

    if destination == "todo":
        if isinstance(branch_value, str):
            _ensure_git_repo(target_repo)
            _delete_branch(target_repo, branch_value)
        metadata["phase"] = "setup"
        metadata["worktree"] = None
        metadata["branch"] = None
        metadata.pop("claimed_by", None)
        metadata.pop("started_at", None)
        metadata["last_activity_at"] = timestamp
        target_dir = _repo_issue_dir(root, repo_id, "todo", issue_id)
    else:
        metadata["phase"] = "cleanup"
        metadata["last_activity_at"] = timestamp
        target_dir = _repo_issue_dir(root, repo_id, "archive", issue_id)
        body = f"{body.rstrip()}\n\n## Final Note\n\n{note.strip()}\n"

    run_dir = execution_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    _append_cleanup_note(run_dir / "notes.md", destination=destination, note=note)
    _write_run_cleanup(
        run_dir / "run.yaml",
        destination=destination,
        note=note,
        branch=branch_value if isinstance(branch_value, str) else None,
        timestamp=timestamp,
    )
    _append_event(
        run_dir,
        "run.cleanup",
        f"destination={destination}",
        timestamp=timestamp,
        destination=destination,
        remove_worktree=remove_worktree,
    )

    shutil.rmtree(run_dir / "claim.lock", ignore_errors=True)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "issue.md"
    execution_file.write_text(render_frontmatter(metadata, body))
    if target_dir.exists():
        raise FileExistsError(f"Target issue directory already exists: {target_dir}")
    execution_dir.rename(target_dir)
    return target_file


def export_run(root: Path, issue_ref: str, *, output: Path) -> Path:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    issue_file = _find_issue_file(root, repo_id, issue_id)
    run_dir = _repo_run_dir(root, repo_id, issue_id)
    if issue_file is None and not run_dir.exists():
        raise FileNotFoundError(f"No issue or run evidence found for {_issue_ref(repo_id, issue_id)}")

    output = output if output.is_absolute() else root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    run_file = run_dir / "run.yaml"
    exported_at = _record_export_metadata(root, issue_file, run_file, output)
    if exported_at is not None:
        _append_event(
            run_dir,
            "export.written",
            relative_to_root(root, output),
            timestamp=exported_at,
            path=relative_to_root(root, output),
        )
    sections = [f"# GoShipit Run Evidence: {_issue_ref(repo_id, issue_id)}", ""]
    sections.extend(_issue_export_section(root, issue_file))
    sections.extend(_run_metadata_export_section(root, run_file))
    sections.extend(_notes_export_section(root, run_dir / "notes.md"))
    sections.extend(_events_export_section(root, _events_file(run_dir)))
    sections.extend(_command_records_export_section(root, _logs_dir(run_dir) / "commands"))
    sections.extend(_worktree_export_section(issue_file, run_file))
    sections.extend(_export_footer_section())
    output.write_text("\n".join(sections).rstrip() + "\n")
    return output


def render_handoff(root: Path, issue_ref: str) -> str:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    canonical = _issue_ref(repo_id, issue_id)
    issue = show_issue(root, canonical)
    run = show_run(root, canonical)
    worktree = run.run.get("worktree") or issue.metadata.get("worktree")
    branch = run.run.get("branch") or issue.metadata.get("branch")
    claimed_by = run.run.get("claimed_by") or issue.metadata.get("claimed_by")
    claim_id = run.run.get("claim_id") or issue.metadata.get("claim_id")
    commands = sorted(run.commands, key=lambda item: str(item.get("started_at") or ""))

    lines = [
        f"# GoShipit Handoff: {canonical}",
        "",
        f"Control Root: `{root}`",
        f"Issue File: `{relative_to_root(root, issue.summary.issue_file)}`",
        f"Run File: `{relative_to_root(root, run.run_file)}`",
        f"Repo: `{issue.summary.repo}`",
        f"Status: `{issue.summary.status}`",
        f"Phase: `{issue.summary.phase or run.run.get('phase') or ''}`",
        f"Branch: `{branch or ''}`",
        f"Worktree: `{worktree or ''}`",
        f"Claimed By: `{claimed_by or ''}`",
        f"Claim ID: `{claim_id or ''}`",
        "",
        "## Issue Summary",
        "",
        f"Title: {issue.summary.title}",
        "",
        issue.body or "No issue body found.",
        "",
        "## Latest Notes",
        "",
        _last_section(run.notes) or "No notes found.",
        "",
        "## Command Summary",
    ]
    if commands:
        for command in commands:
            lines.append(
                f"- {_display_handoff_value(command.get('check'))} "
                f"exit {_display_handoff_value(command.get('exit_code'))}: "
                f"{portable_text(root, command.get('command'))}"
            )
    else:
        lines.append("No command records found.")

    lines.extend(
        [
            "",
            "## Resume Commands",
            "",
            "```sh",
            f"cd {root}",
            f"go-ship-it show-run {canonical}",
            f"go-ship-it show-run {canonical} --trace",
            f"go-ship-it show-run {canonical} --handoff",
            f"go-ship-it verify-run {canonical}",
            "```",
            "",
            "Target repo edits belong only inside the active worktree above.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_handoff(root: Path, issue_ref: str, *, output: Path | None = None) -> Path:
    repo_id, issue_id = _parse_issue_ref(issue_ref)
    output_path = output or _repo_run_dir(root, repo_id, issue_id) / "handoff.md"
    if not output_path.is_absolute():
        output_path = root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_handoff(root, _issue_ref(repo_id, issue_id)))
    return output_path


def _detect_agent() -> str:
    explicit = os.environ.get("GO_SHIP_IT_AGENT")
    if explicit and explicit.strip():
        return _safe_id(explicit)
    if os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("CLAUDECODE"):
        return "claude"
    if os.environ.get("CURSOR_PLUGIN_ROOT") or os.environ.get("CURSOR_TRACE_ID"):
        return "cursor"
    if os.environ.get("CODEX_HOME") or os.environ.get("OPENAI_CODEX"):
        return "codex"
    return "agent"


def _claim_id(root: Path, issue_id: str, worktree_relative: Path) -> str:
    basis = f"{root.resolve()}|{issue_id}|{worktree_relative.as_posix()}"
    digest = hashlib.sha256(basis.encode()).hexdigest()[:12]
    return f"claim-{issue_id}-{digest}"


def _existing_started_run(
    root: Path,
    repo_id: str,
    issue_id: str,
    execution_file: Path,
    run_dir: Path,
) -> StartedRun:
    run_file = run_dir / "run.yaml"
    if not execution_file.exists() or not run_file.exists():
        raise _active_run_error(issue_id, execution_file, run_dir)
    run = _load_run(run_file)
    branch = _required_string(run, "branch")
    worktree_value = _required_string(run, "worktree")
    worktree = root / worktree_value
    claim_id = str(run.get("claim_id") or _claim_id(root, issue_id, Path(worktree_value)))
    claimed_by_value = run.get("claimed_by")
    claimed_by = claimed_by_value if isinstance(claimed_by_value, str) else None
    if run.get("claim_id") != claim_id:
        run["claim_id"] = claim_id
        run_file.write_text(_render_mapping(run))
    metadata, body = parse_frontmatter(execution_file.read_text())
    if metadata.get("claim_id") != claim_id:
        metadata["claim_id"] = claim_id
        execution_file.write_text(render_frontmatter(metadata, body))
    context_file = worktree / ".go-ship-it" / "context.yaml"
    if not context_file.exists() and worktree.exists():
        context_file = _write_worktree_context(
            root,
            issue_id=issue_id,
            repo_id=repo_id,
            branch=branch,
            worktree_relative=Path(worktree_value),
            claimed_by=claimed_by,
            claim_id=claim_id,
        )
    return StartedRun(
        issue_id=issue_id,
        repo_id=repo_id,
        issue_ref=_issue_ref(repo_id, issue_id),
        branch=branch,
        worktree=worktree,
        issue_file=execution_file,
        run_file=run_file,
        claim_id=claim_id,
        claimed_by=claimed_by,
        already_active=True,
        context_file=context_file,
    )


def _write_worktree_context(
    root: Path,
    *,
    issue_id: str,
    repo_id: str,
    branch: str,
    worktree_relative: Path,
    claimed_by: str | None,
    claim_id: str,
) -> Path:
    worktree = root / worktree_relative
    context_dir = worktree / ".go-ship-it"
    context_dir.mkdir(parents=True, exist_ok=True)
    context_file = context_dir / "context.yaml"
    context = {
        "issue_id": issue_id,
        "repo_id": repo_id,
        "control_root": str(root.resolve()),
        "run_dir": f"state/repos/{repo_id}/issues/execution/{issue_id}",
        "issue_file": f"state/repos/{repo_id}/issues/execution/{issue_id}/issue.md",
        "worktree": worktree_relative.as_posix(),
        "branch": branch,
        "claimed_by": claimed_by,
        "claim_id": claim_id,
    }
    context_file.write_text(_render_mapping(context))
    _ignore_worktree_context(worktree)
    return context_file


def _find_worktree_context(start: Path) -> Path | None:
    candidates = (start, *start.parents)
    for directory in candidates:
        context_file = directory / ".go-ship-it" / "context.yaml"
        if context_file.exists():
            return context_file
    return None


def _ignore_worktree_context(worktree: Path) -> None:
    try:
        exclude_value = _git(worktree, "rev-parse", "--git-path", "info/exclude").strip()
    except GoShipitError:
        return
    if not exclude_value:
        return
    exclude_path = Path(exclude_value)
    if not exclude_path.is_absolute():
        exclude_path = worktree / exclude_path
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude_path.read_text() if exclude_path.exists() else ""
    if ".go-ship-it/" not in existing.splitlines():
        prefix = "" if not existing or existing.endswith("\n") else "\n"
        with exclude_path.open("a") as handle:
            handle.write(f"{prefix}.go-ship-it/\n")


def _last_section(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    marker = "\n## "
    index = stripped.rfind(marker)
    if index == -1:
        return portable_text(Path("."), stripped)
    return portable_text(Path("."), stripped[index + 1 :])


def _display_handoff_value(value: object) -> str:
    return "" if value is None else str(value)


def _parse_issue_ref(value: str) -> tuple[str, str]:
    raw = value.strip()
    parts = raw.split("/")
    if len(parts) != 2:
        raise ValueError(f"issue ref must be <repo>/<issue-id>, got: {value}")
    repo, issue = parts
    return _safe_id(repo), _safe_id(issue)


def _issue_ref(repo_id: str, issue_id: str) -> str:
    return f"{_safe_id(repo_id)}/{_safe_id(issue_id)}"


def _find_issue_file(root: Path, repo_id: str, issue_id: str) -> Path | None:
    safe_repo_id = _safe_id(repo_id)
    safe_issue_id = _safe_id(issue_id)
    for status in ("todo", "execution", "archive"):
        path = _repo_issue_dir(root, safe_repo_id, status, safe_issue_id) / "issue.md"
        if path.exists():
            return path
    return None


def _find_issue_dir(root: Path, repo_id: str, issue_id: str) -> Path | None:
    issue_file = _find_issue_file(root, repo_id, issue_id)
    return issue_file.parent if issue_file is not None else None


def _issue_export_section(root: Path, issue_file: Path | None) -> list[str]:
    if issue_file is None:
        return ["## Issue", "", "No issue file found.", ""]
    return [
        "## Issue",
        "",
        f"Source: `{relative_to_root(root, issue_file)}`",
        "",
        "```markdown",
        portable_text(root, issue_file.read_text()).strip(),
        "```",
        "",
    ]


def _run_metadata_export_section(root: Path, run_file: Path) -> list[str]:
    if not run_file.exists():
        return ["## Run Metadata", "", "No run metadata found.", ""]
    return ["## Run Metadata", "", "```yaml", portable_text(root, run_file.read_text()).strip(), "```", ""]


def _record_export_metadata(root: Path, issue_file: Path | None, run_file: Path, output: Path) -> str | None:
    if not run_file.exists():
        return None
    run = _parse_mapping(run_file.read_text())
    issue_status = issue_file.parent.parent.name if issue_file is not None else None
    exported_at = _now_iso()
    exports = run.get("exports")
    if not isinstance(exports, list):
        exports = []
    exports.append(
        {
            "path": relative_to_root(root, output),
            "exported_at": exported_at,
            "issue_status": issue_status,
            "run_phase": run.get("phase"),
        }
    )
    run["exports"] = exports
    run_file.write_text(_render_mapping(run))
    return exported_at


def _read_events(run_dir: Path) -> list[RunEvent]:
    events_file = _events_file(run_dir)
    events: list[RunEvent] = []
    if not events_file.exists():
        return events
    for line in events_file.read_text().splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = data.get("timestamp")
        kind = data.get("kind")
        detail = data.get("detail")
        if not isinstance(timestamp, str) or not isinstance(kind, str):
            continue
        events.append(RunEvent(timestamp, kind, detail if isinstance(detail, str) else ""))
    return events


def _notes_export_section(root: Path, notes: Path) -> list[str]:
    if not notes.exists():
        return ["## Notes", "", "No notes found.", ""]
    return ["## Notes", "", portable_text(root, notes.read_text()).strip(), ""]


def _events_export_section(root: Path, events_file: Path) -> list[str]:
    if not events_file.exists():
        return ["## Generated Logs", "", "No event log found.", ""]
    return [
        "## Generated Logs",
        "",
        f"Events: `{relative_to_root(root, events_file)}`",
        "",
    ]


def _command_records_export_section(root: Path, commands_dir: Path) -> list[str]:
    lines = ["## Command Records", ""]
    records = sorted(commands_dir.glob("*.yaml")) if commands_dir.exists() else []
    if not records:
        return lines + ["No command records found.", ""]

    for record in records:
        data = _parse_mapping(record.read_text())
        lines.extend(
            [
                f"### {record.name}",
                "",
                f"- Check: `{data.get('check')}`",
                f"- Command: `{portable_text(root, data.get('command'))}`",
                f"- CWD: `{portable_path_value(root, data.get('cwd'))}`",
                f"- Exit Code: `{data.get('exit_code')}`",
                f"- Started: `{data.get('started_at')}`",
                f"- Ended: `{data.get('ended_at')}`",
                "",
                "Stdout tail:",
                "",
                "```text",
                portable_text(root, data.get("stdout_tail")).strip(),
                "```",
                "",
                "Stderr tail:",
                "",
                "```text",
                portable_text(root, data.get("stderr_tail")).strip(),
                "```",
                "",
            ]
        )
    return lines


def _worktree_export_section(issue_file: Path | None, run_file: Path) -> list[str]:
    data: dict[str, object] = {}
    if run_file.exists():
        data.update(_parse_mapping(run_file.read_text()))
    if issue_file is not None:
        metadata, _body = parse_frontmatter(issue_file.read_text())
        for key in ("repo", "branch", "worktree"):
            data.setdefault(key, metadata.get(key))

    lines = ["## Worktree", ""]
    fields = (
        ("Repo", "repo"),
        ("Branch", "branch"),
        ("Worktree", "worktree"),
        ("Closed Branch", "closed_branch"),
    )
    found = False
    for label, key in fields:
        value = data.get(key)
        if value is not None:
            lines.append(f"- {label}: `{value}`")
            found = True
    if not found:
        lines.append("No worktree metadata found.")
    lines.append("")
    return lines


def _export_footer_section() -> list[str]:
    return [
        "## Export Notes",
        "",
        "Generated by `go-ship-it export-run`. Command records preserve recorded exit codes.",
        "",
    ]


def _safe_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    if not normalized:
        raise ValueError("Identifier must contain at least one letter or number")
    return normalized


def _collect_issue_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(path / "issue.md" for path in _collect_issue_dirs(directory) if (path / "issue.md").exists())


def _collect_issue_dirs(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("issue-*") if path.is_dir())


def _collect_worktree_issue_dirs(worktrees_root: Path) -> list[Path]:
    if not worktrees_root.exists():
        return []
    issue_dirs: list[Path] = []
    for repo_dir in worktrees_root.iterdir():
        if repo_dir.is_dir():
            issue_dirs.extend(path for path in repo_dir.glob("issue-*") if path.is_dir())
    return sorted(issue_dirs)


def _issue_number(path: Path) -> int:
    match = re.fullmatch(r"issue-(\d+)", path.name)
    return int(match.group(1)) if match else 0


def _active_run_error(issue_id: str, execution_file: Path, run_dir: Path) -> IssueAlreadyActiveError:
    worktree: str | None = None
    if execution_file.exists():
        metadata, _body = parse_frontmatter(execution_file.read_text())
        value = metadata.get("worktree")
        worktree = value if isinstance(value, str) else None
    run_file = run_dir / "run.yaml"
    return IssueAlreadyActiveError(
        issue_id,
        issue_file=execution_file if execution_file.exists() else None,
        run_file=run_file if run_file.exists() else None,
        worktree=worktree,
    )


def _active_issue_file(root: Path, repo_id: str, issue_id: str) -> Path:
    issue_file = _repo_issue_dir(root, _safe_id(repo_id), "execution", _safe_id(issue_id)) / "issue.md"
    if not issue_file.exists():
        raise FileNotFoundError(f"No execution issue found at {issue_file}")
    return issue_file


def _run_dir(root: Path, repo_id: str, issue_id: str) -> Path:
    run_dir = _repo_run_dir(root, _safe_id(repo_id), _safe_id(issue_id))
    if not run_dir.is_dir() or not (run_dir / "run.yaml").exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    return run_dir


def _load_run(run_file: Path) -> dict[str, object]:
    if not run_file.exists():
        raise FileNotFoundError(f"Run file not found: {run_file}")
    return _parse_mapping(run_file.read_text())


def _repo_dir(root: Path, repo_id: str) -> Path:
    return root / "state" / "repos" / _safe_id(repo_id)


def _repo_issues_dir(root: Path, repo_id: str, state: str) -> Path:
    if state not in ISSUE_STATES:
        raise ValueError("state must be one of: todo, execution, archive")
    return _repo_dir(root, repo_id) / "issues" / state


def _repo_issue_dir(root: Path, repo_id: str, state: str, issue_id: str) -> Path:
    return _repo_issues_dir(root, repo_id, state) / _safe_id(issue_id)


def _repo_run_dir(root: Path, repo_id: str, issue_id: str) -> Path:
    found = _find_issue_dir(root, repo_id, issue_id)
    if found is not None:
        return found
    return _repo_issue_dir(root, repo_id, "execution", issue_id)


def _repo_file(root: Path, repo_id: str) -> Path:
    return _repo_dir(root, repo_id) / "repo.yaml"


def _repo_config_path(root: Path, repo_id: str) -> Path:
    return _repo_file(root, repo_id)


def _repo_not_found_message(root: Path, repo_id: str) -> str:
    return f"Repo registry file not found: {_repo_file(root, repo_id)}"


def _repo_context_template(repo_id: str) -> str:
    return (
        f"# {repo_id} Context\n\n"
        "## Overview\n\n"
        "Add repo-specific background that should travel with every issue in this target repo.\n\n"
        "## Commands\n\n"
        "Record common setup, test, lint, and release commands here.\n\n"
        "## Gotchas\n\n"
        "Capture repo-specific traps, constraints, or conventions as they are learned.\n\n"
        "## Notes\n\n"
    )


def _read_repo(root: Path, repo_id: str) -> dict[str, object]:
    repo_file = _repo_config_path(root, repo_id)
    if not repo_file.exists():
        raise FileNotFoundError(_repo_not_found_message(root, _safe_id(repo_id)))
    return _parse_mapping(repo_file.read_text())


def _resolve_repo_path(root: Path, value: object) -> Path:
    if not isinstance(value, str):
        raise ValueError("Repo path must be a string")
    path = Path(value)
    return path if path.is_absolute() else (root / path).resolve()


def _ensure_git_repo(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Target repo does not exist: {path}")
    _git(path, "rev-parse", "--is-inside-work-tree")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        command = " ".join(("git", "-C", str(repo), *args))
        raise GoShipitError(f"{command} failed: {detail}")
    return result.stdout


def _remove_worktree(target_repo: Path, worktree: Path) -> None:
    try:
        _git(target_repo, "worktree", "remove", "--force", str(worktree))
    except GoShipitError:
        shutil.rmtree(worktree, ignore_errors=True)


def _delete_branch(target_repo: Path, branch: str) -> None:
    try:
        _git(target_repo, "branch", "-D", branch)
    except GoShipitError:
        pass


def _is_managed_worktree(root: Path, worktree: Path) -> bool:
    managed_root = (root / "worktrees").resolve()
    resolved_worktree = worktree.resolve()
    try:
        resolved_worktree.relative_to(managed_root)
    except ValueError:
        return False
    return True


def _logs_dir(run_dir: Path) -> Path:
    return run_dir / "logs"


def _events_file(run_dir: Path) -> Path:
    return _logs_dir(run_dir) / "events.jsonl"


def _append_event(
    run_dir: Path,
    kind: str,
    detail: str,
    *,
    timestamp: str | None = None,
    **fields: object,
) -> str:
    created_at = timestamp or _now_iso()
    payload = {
        "timestamp": created_at,
        "kind": kind,
        "detail": detail,
        **{key: value for key, value in fields.items() if value is not None},
    }
    events_file = _events_file(run_dir)
    events_file.parent.mkdir(parents=True, exist_ok=True)
    with events_file.open("a") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return created_at


def _append_note_to_notes(notes: Path, *, section: str, note: str, phase: str | None) -> str:
    title = section.strip()
    if not title:
        raise ValueError("section must not be empty")
    body = note.strip()
    if not body:
        raise ValueError("note must not be empty")

    timestamp = _now_iso()
    lines = [f"\n## {title}", "", f"Timestamp: {timestamp}"]
    if phase is not None:
        lines.append(f"Phase: {phase}")
    lines.extend(["", body, ""])
    with notes.open("a") as handle:
        handle.write("\n".join(lines))
    return timestamp


def _append_cleanup_note(notes: Path, *, destination: str, note: str) -> None:
    with notes.open("a") as handle:
        handle.write(f"\n## Cleanup\n\nDestination: {destination}\n\n{note.strip()}\n")


def _write_run_cleanup(
    run_file: Path,
    *,
    destination: str,
    note: str,
    branch: str | None,
    timestamp: str,
) -> None:
    run = _parse_mapping(run_file.read_text()) if run_file.exists() else {}
    run["phase"] = "cleanup"
    run["cleanup_destination"] = destination
    run["cleanup_note"] = note.strip()
    run["closed_at"] = timestamp
    if branch is not None:
        run["closed_branch"] = branch
    run_file.write_text(_render_mapping(run))


def _remove_empty_directory(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        pass


def _required_string(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _validate_phase(phase: str) -> str:
    safe_phase = phase.strip().lower()
    if safe_phase not in ALLOWED_PHASES:
        allowed = ", ".join(sorted(ALLOWED_PHASES))
        raise ValueError(f"phase must be one of: {allowed}")
    return safe_phase


def _timestamp_slug(timestamp: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "-", timestamp).strip("-")


def _tail(value: str, *, limit: int = 4000) -> str:
    return value[-limit:]


def _parse_mapping(text: str) -> dict[str, object]:
    loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise ValueError("YAML file must contain a mapping")
    return {str(key): value for key, value in loaded.items()}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _render_mapping(values: dict[str, object]) -> str:
    return yaml.safe_dump(values, sort_keys=False, default_flow_style=False)
