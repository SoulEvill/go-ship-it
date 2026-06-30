from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from go_ship_it.frontmatter import parse_frontmatter, render_frontmatter


STATE_DIRS = (
    "state/repos",
    "state/issues/todo",
    "state/issues/execution",
    "state/issues/archive",
    "state/runs",
    "worktrees",
)

ALLOWED_PHASES = {"setup", "investigate", "propose", "implement", "test", "cleanup"}


class GoShipitError(RuntimeError):
    pass


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
    branch: str
    worktree: Path
    issue_file: Path
    run_file: Path


def ensure_layout(root: Path) -> None:
    for relative in STATE_DIRS:
        (root / relative).mkdir(parents=True, exist_ok=True)


def next_issue_id(root: Path) -> str:
    issue_dirs = (
        root / "state" / "issues" / "todo",
        root / "state" / "issues" / "execution",
        root / "state" / "issues" / "archive",
    )
    existing = [path for directory in issue_dirs for path in _collect_issue_files(directory)]
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
    repo_file = root / "state" / "repos" / f"{safe_repo_id}.yaml"
    values = {
        "id": safe_repo_id,
        "path": str(path),
        "default_branch": default_branch,
        "worktree_root": f"worktrees/{safe_repo_id}",
        "setup_command": setup_command,
        "test_command": test_command,
        "lint_command": lint_command,
    }
    repo_file.write_text(_render_mapping(values))
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
    issue_id = next_issue_id(root)
    issue_file = root / "state" / "issues" / "todo" / f"{issue_id}.md"
    metadata = {
        "id": issue_id,
        "repo": safe_repo_id,
        "status": "todo",
        "phase": "setup",
        "title": title,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
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
    return issue_file


def start_issue(root: Path, issue_id: str, *, claimed_by: str | None = None) -> StartedRun:
    ensure_layout(root)
    safe_issue_id = _safe_id(issue_id)
    todo_file = root / "state" / "issues" / "todo" / f"{safe_issue_id}.md"
    execution_file = root / "state" / "issues" / "execution" / f"{safe_issue_id}.md"
    run_dir = root / "state" / "runs" / safe_issue_id
    claim_dir = run_dir / "claim.lock"

    if execution_file.exists() or claim_dir.exists():
        raise _active_run_error(safe_issue_id, execution_file, run_dir)
    if not todo_file.exists():
        raise FileNotFoundError(f"No todo issue found at {todo_file}")

    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        claim_dir.mkdir()
    except FileExistsError as exc:
        raise _active_run_error(safe_issue_id, execution_file, run_dir) from exc

    worktree_created = False
    target_repo: Path | None = None
    branch: str | None = None
    worktree: Path | None = None
    try:
        metadata, body = parse_frontmatter(todo_file.read_text())
        repo_id = _required_string(metadata, "repo")
        repo = _read_repo(root, repo_id)
        target_repo = _resolve_repo_path(root, repo.get("path"))
        _ensure_git_repo(target_repo)

        branch = f"go-ship-it/{safe_issue_id}"
        worktree_relative = Path(_required_string(repo, "worktree_root")) / safe_issue_id
        worktree = root / worktree_relative
        if worktree.exists():
            raise FileExistsError(f"Worktree path already exists: {worktree}")
        worktree.parent.mkdir(parents=True, exist_ok=True)
        _git(target_repo, "worktree", "add", "-b", branch, str(worktree), _required_string(repo, "default_branch"))
        worktree_created = True

        timestamp = _now_iso()
        metadata["status"] = "execution"
        metadata["phase"] = "investigate"
        metadata["branch"] = branch
        metadata["worktree"] = worktree_relative.as_posix()
        metadata["claimed_by"] = claimed_by
        metadata["started_at"] = timestamp
        metadata["last_activity_at"] = timestamp
        execution_file.write_text(render_frontmatter(metadata, body))
        todo_file.unlink()

        run_file = run_dir / "run.yaml"
        run_file.write_text(
            _render_mapping(
                {
                    "issue_id": safe_issue_id,
                    "repo": repo_id,
                    "branch": branch,
                    "worktree": worktree_relative.as_posix(),
                    "claimed_by": claimed_by,
                    "phase": "investigate",
                    "started_at": timestamp,
                    "last_activity_at": timestamp,
                }
            )
        )
        return StartedRun(safe_issue_id, branch, worktree, execution_file, run_file)
    except Exception:
        if worktree_created and target_repo is not None and worktree is not None:
            _remove_worktree(target_repo, worktree)
        if worktree_created and target_repo is not None and branch is not None:
            _delete_branch(target_repo, branch)
        shutil.rmtree(claim_dir, ignore_errors=True)
        _remove_empty_directory(run_dir)
        raise


def append_note(root: Path, issue_id: str, *, section: str, note: str, phase: str | None = None) -> Path:
    safe_issue_id = _safe_id(issue_id)
    if phase is not None:
        _validate_phase(phase)
    _active_issue_file(root, safe_issue_id)
    run_dir = _run_dir(root, safe_issue_id)

    journal = run_dir / "journal.md"
    _append_note_to_journal(journal, section=section, note=note, phase=phase)
    return journal


def set_phase(root: Path, issue_id: str, phase: str, *, note: str) -> Path:
    safe_issue_id = _safe_id(issue_id)
    safe_phase = _validate_phase(phase)
    issue_file = _active_issue_file(root, safe_issue_id)
    run_dir = _run_dir(root, safe_issue_id)
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

    _append_note_to_journal(run_dir / "journal.md", section=f"Phase: {safe_phase}", note=note, phase=safe_phase)
    return issue_file


def cleanup_issue(
    root: Path,
    issue_id: str,
    *,
    destination: str,
    note: str,
    remove_worktree: bool,
) -> Path:
    ensure_layout(root)
    safe_issue_id = _safe_id(issue_id)
    if destination not in {"todo", "archive"}:
        raise ValueError("destination must be 'todo' or 'archive'")
    if destination == "todo" and not remove_worktree:
        raise ValueError("returning an issue to todo requires remove_worktree=True")

    execution_file = root / "state" / "issues" / "execution" / f"{safe_issue_id}.md"
    if not execution_file.exists():
        raise FileNotFoundError(f"No execution issue found at {execution_file}")

    metadata, body = parse_frontmatter(execution_file.read_text())
    repo = _read_repo(root, _required_string(metadata, "repo"))
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
        metadata["status"] = "todo"
        metadata["phase"] = "setup"
        metadata["worktree"] = None
        metadata["branch"] = None
        metadata.pop("claimed_by", None)
        metadata.pop("started_at", None)
        metadata["last_activity_at"] = timestamp
        target_file = root / "state" / "issues" / "todo" / f"{safe_issue_id}.md"
    else:
        metadata["status"] = "archive"
        metadata["phase"] = "cleanup"
        metadata["last_activity_at"] = timestamp
        target_file = root / "state" / "issues" / "archive" / f"{safe_issue_id}.md"
        body = f"{body.rstrip()}\n\n## Final Note\n\n{note.strip()}\n"

    run_dir = root / "state" / "runs" / safe_issue_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _append_journal(run_dir / "journal.md", destination=destination, note=note)
    _write_run_cleanup(
        run_dir / "run.yaml",
        destination=destination,
        note=note,
        branch=branch_value if isinstance(branch_value, str) else None,
        timestamp=timestamp,
    )

    target_file.write_text(render_frontmatter(metadata, body))
    execution_file.unlink()
    shutil.rmtree(run_dir / "claim.lock", ignore_errors=True)
    return target_file


def _safe_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    if not normalized:
        raise ValueError("Identifier must contain at least one letter or number")
    return normalized


def _collect_issue_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob("issue-*.md"))


def _issue_number(path: Path) -> int:
    match = re.fullmatch(r"issue-(\d+)\.md", path.name)
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


def _active_issue_file(root: Path, issue_id: str) -> Path:
    issue_file = root / "state" / "issues" / "execution" / f"{_safe_id(issue_id)}.md"
    if not issue_file.exists():
        raise FileNotFoundError(f"No execution issue found at {issue_file}")
    return issue_file


def _run_dir(root: Path, issue_id: str) -> Path:
    run_dir = root / "state" / "runs" / _safe_id(issue_id)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")
    return run_dir


def _load_run(run_file: Path) -> dict[str, object]:
    if not run_file.exists():
        raise FileNotFoundError(f"Run file not found: {run_file}")
    return _parse_mapping(run_file.read_text())


def _read_repo(root: Path, repo_id: str) -> dict[str, object]:
    repo_file = root / "state" / "repos" / f"{_safe_id(repo_id)}.yaml"
    if not repo_file.exists():
        raise FileNotFoundError(f"Repo registry file not found: {repo_file}")
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


def _append_note_to_journal(journal: Path, *, section: str, note: str, phase: str | None) -> None:
    title = section.strip()
    if not title:
        raise ValueError("section must not be empty")
    body = note.strip()
    if not body:
        raise ValueError("note must not be empty")

    lines = [f"\n## {title}", "", f"Timestamp: {_now_iso()}"]
    if phase is not None:
        lines.append(f"Phase: {phase}")
    lines.extend(["", body, ""])
    with journal.open("a") as handle:
        handle.write("\n".join(lines))


def _append_journal(journal: Path, *, destination: str, note: str) -> None:
    with journal.open("a") as handle:
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


def _parse_mapping(text: str) -> dict[str, object]:
    loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise ValueError("YAML file must contain a mapping")
    return {str(key): value for key, value in loaded.items()}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _render_mapping(values: dict[str, object]) -> str:
    return yaml.safe_dump(values, sort_keys=False, default_flow_style=False)
