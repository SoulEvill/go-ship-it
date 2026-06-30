from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import yaml

from go_ship_it.frontmatter import render_frontmatter


STATE_DIRS = (
    "state/repos",
    "state/issues/todo",
    "state/issues/execution",
    "state/issues/archive",
    "state/runs",
    "worktrees",
)


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
    issue_id = next_issue_id(root)
    issue_file = root / "state" / "issues" / "todo" / f"{issue_id}.md"
    metadata = {
        "id": issue_id,
        "repo": _safe_id(repo_id),
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


def _render_mapping(values: dict[str, object]) -> str:
    return yaml.safe_dump(values, sort_keys=False, default_flow_style=False)
