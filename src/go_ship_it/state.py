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
    existing.extend(_collect_issue_dirs(root / "state" / "runs"))
    existing.extend(_collect_worktree_issue_dirs(root / "worktrees"))
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


def read_repo_config(root: Path, repo_id: str) -> dict[str, object]:
    return _read_repo(root, repo_id)


def update_repo_config(
    root: Path,
    repo_id: str,
    *,
    updates: dict[str, object],
    clears: set[str],
) -> Path:
    safe_repo_id = _safe_id(repo_id)
    repo_file = root / "state" / "repos" / f"{safe_repo_id}.yaml"
    if not repo_file.exists():
        raise FileNotFoundError(f"Repo registry file not found: {repo_file}")

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


def run_check(root: Path, issue_id: str, *, check: str) -> Path:
    safe_issue_id = _safe_id(issue_id)
    safe_check = check.strip().lower()
    if safe_check not in {"setup", "test", "lint"}:
        raise ValueError("check must be one of: setup, test, lint")

    issue_file = _active_issue_file(root, safe_issue_id)
    run_dir = _run_dir(root, safe_issue_id)
    metadata, _body = parse_frontmatter(issue_file.read_text())
    repo_id = _required_string(metadata, "repo")
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

    commands_dir = run_dir / "commands"
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

    note = f"Command: `{command}`\n\nExit code: {result.returncode}\n\nEvidence: `{record_file}`"
    _append_note_to_journal(run_dir / "journal.md", section=f"Check: {safe_check}", note=note, phase="test")

    if result.returncode != 0:
        raise CheckFailedError(safe_check, result.returncode, record_file)
    return record_file


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


def export_run(root: Path, issue_id: str, *, output: Path) -> Path:
    safe_issue_id = _safe_id(issue_id)
    issue_file = _find_issue_file(root, safe_issue_id)
    run_dir = root / "state" / "runs" / safe_issue_id
    if issue_file is None and not run_dir.exists():
        raise FileNotFoundError(f"No issue or run evidence found for {safe_issue_id}")

    output = output if output.is_absolute() else root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    run_file = run_dir / "run.yaml"
    sections = [f"# GoShipit Run Evidence: {safe_issue_id}", ""]
    sections.extend(_issue_export_section(root, issue_file))
    sections.extend(_run_metadata_export_section(root, run_file))
    sections.extend(_journal_export_section(root, run_dir / "journal.md"))
    sections.extend(_command_records_export_section(root, run_dir / "commands"))
    sections.extend(_worktree_export_section(issue_file, run_file))
    sections.extend(_notes_export_section())
    output.write_text("\n".join(sections).rstrip() + "\n")
    return output


def _find_issue_file(root: Path, issue_id: str) -> Path | None:
    for status in ("todo", "execution", "archive"):
        path = root / "state" / "issues" / status / f"{issue_id}.md"
        if path.exists():
            return path
    return None


def _issue_export_section(root: Path, issue_file: Path | None) -> list[str]:
    if issue_file is None:
        return ["## Issue", "", "No issue file found.", ""]
    return [
        "## Issue",
        "",
        f"Source: `{_relative_to_root(root, issue_file)}`",
        "",
        "```markdown",
        _portable_text(root, issue_file.read_text()).strip(),
        "```",
        "",
    ]


def _run_metadata_export_section(root: Path, run_file: Path) -> list[str]:
    if not run_file.exists():
        return ["## Run Metadata", "", "No run metadata found.", ""]
    return ["## Run Metadata", "", "```yaml", _portable_text(root, run_file.read_text()).strip(), "```", ""]


def _journal_export_section(root: Path, journal: Path) -> list[str]:
    if not journal.exists():
        return ["## Journal", "", "No journal found.", ""]
    return ["## Journal", "", _portable_text(root, journal.read_text()).strip(), ""]


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
                f"- Command: `{_portable_text(root, data.get('command'))}`",
                f"- CWD: `{_portable_path_value(root, data.get('cwd'))}`",
                f"- Exit Code: `{data.get('exit_code')}`",
                f"- Started: `{data.get('started_at')}`",
                f"- Ended: `{data.get('ended_at')}`",
                "",
                "Stdout tail:",
                "",
                "```text",
                _portable_text(root, data.get("stdout_tail")).strip(),
                "```",
                "",
                "Stderr tail:",
                "",
                "```text",
                _portable_text(root, data.get("stderr_tail")).strip(),
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


def _notes_export_section() -> list[str]:
    return [
        "## Notes",
        "",
        "Generated by `go-ship-it export-run`. Command records preserve recorded exit codes.",
        "",
    ]


def _relative_to_root(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _portable_path_value(root: Path, value: object) -> str:
    if not isinstance(value, str):
        return str(value)
    path = Path(value)
    if path.is_absolute():
        return _relative_to_root(root, path)
    return _portable_text(root, value)


def _portable_text(root: Path, value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    root_text = str(root)
    return (
        text.replace(f"file://{root_text}/", "file://go-ship-it-root/")
        .replace(f"{root_text}/", "")
        .replace(root_text, ".")
    )


def _safe_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    if not normalized:
        raise ValueError("Identifier must contain at least one letter or number")
    return normalized


def _collect_issue_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob("issue-*.md"))


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
    match = re.fullmatch(r"issue-(\d+)(?:\.md)?", path.name)
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
