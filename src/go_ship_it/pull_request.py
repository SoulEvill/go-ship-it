from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from go_ship_it.portable import portable_text, relative_to_root
from go_ship_it.state import (
    GoShipitError,
    _append_event,
    _parse_mapping,
    _render_mapping,
    _write_active_phase,
    pull_request_config,
    read_repo_config,
    show_issue,
    show_run,
)
from go_ship_it.verify import verify_run


@dataclass(frozen=True)
class PullRequestPreview:
    issue_ref: str
    path: Path
    title: str
    provider: str
    remote: str
    base: str
    local_branch: str
    branch: str
    auto_publish: bool


@dataclass(frozen=True)
class PullRequestPublish:
    issue_ref: str
    branch: str
    remote: str
    base: str
    url: str


def prepare_pull_request(
    root: Path,
    issue_ref: str,
    *,
    branch: str | None = None,
    title: str | None = None,
    output: Path | None = None,
) -> PullRequestPreview:
    issue = show_issue(root, issue_ref)
    run = show_run(root, issue_ref)
    repo = read_repo_config(root, issue.summary.repo)
    pr_config = pull_request_config(repo)
    worktree = _worktree_path(root, run.run.get("worktree"))
    local_branch = _required_run_string(run.run, "branch")
    base = _required_repo_string(repo, "default_branch")
    pr_branch = branch or _existing_pr_branch(run.run)
    if pr_branch is None:
        raise ValueError("PR branch is required the first time; pass --branch <team-branch-name>")
    _validate_branch_name(worktree, pr_branch)

    pr_title = (title or issue.summary.title).strip()
    if not pr_title:
        raise ValueError("PR title must not be empty")

    output_path = output if output is not None else run.run_file.parent / "pr.md"
    output_path = output_path if output_path.is_absolute() else root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = _render_pr_body(
        root=root,
        issue_ref=run.issue_ref,
        title=pr_title,
        issue_body=issue.body,
        commands=run.commands,
        notes=run.notes,
        worktree=worktree,
        provider=str(pr_config["provider"]),
        remote=str(pr_config["remote"]),
        base=base,
        local_branch=local_branch,
        pr_branch=pr_branch,
        auto_publish=bool(pr_config["auto_publish"]),
    )
    output_path.write_text(body)

    prepared_at = _now_iso()
    _record_pull_request(
        run.run_file,
        {
            "provider": str(pr_config["provider"]),
            "remote": str(pr_config["remote"]),
            "base": base,
            "local_branch": local_branch,
            "branch": pr_branch,
            "title": pr_title,
            "body_file": relative_to_root(root, output_path),
            "auto_publish": bool(pr_config["auto_publish"]),
            "prepared_at": prepared_at,
        },
    )
    _append_event(
        run.run_file.parent,
        "pull_request.prepared",
        f"branch={pr_branch}",
        timestamp=prepared_at,
        branch=pr_branch,
        local_branch=local_branch,
        body_file=relative_to_root(root, output_path),
    )
    if issue.summary.status == "execution":
        _write_active_phase(issue.summary.issue_file, run.run_file, "prepare-pr")
    return PullRequestPreview(
        issue_ref=run.issue_ref,
        path=output_path,
        title=pr_title,
        provider=str(pr_config["provider"]),
        remote=str(pr_config["remote"]),
        base=base,
        local_branch=local_branch,
        branch=pr_branch,
        auto_publish=bool(pr_config["auto_publish"]),
    )


def publish_pull_request(
    root: Path,
    issue_ref: str,
    *,
    branch: str | None = None,
    title: str | None = None,
    approved: bool = False,
) -> PullRequestPublish:
    run = show_run(root, issue_ref)
    record = run.run.get("pull_request")
    if branch is not None or title is not None or not isinstance(record, dict) or not record.get("body_file"):
        preview = prepare_pull_request(root, issue_ref, branch=branch, title=title)
        run = show_run(root, issue_ref)
        record = run.run.get("pull_request")
    if not isinstance(record, dict):
        raise GoShipitError("Pull request preview is missing; run prepare-pr first")
    if not bool(record.get("auto_publish")) and not approved:
        raise GoShipitError("Publishing requires explicit approval; rerun with --approved or enable pull_request.auto_publish")

    provider = _required_record_string(record, "provider")
    if provider == "none":
        raise GoShipitError(
            "This repo has no publish target (pull_request.provider: none); "
            "archive after local pr.md sign-off instead"
        )
    if provider != "github":
        raise GoShipitError(f"Unsupported pull_request.provider: {provider}")
    remote = _required_record_string(record, "remote")
    base = _required_record_string(record, "base")
    pr_branch = _required_record_string(record, "branch")
    local_branch = _required_record_string(record, "local_branch")
    body_file = root / _required_record_string(record, "body_file")
    worktree = _worktree_path(root, run.run.get("worktree"))
    _validate_branch_name(worktree, pr_branch)
    _require_clean_worktree(worktree)
    _require_commits_ahead(worktree, base)

    report = verify_run(root, run.issue_ref)
    blockers = [*report.errors, *report.warnings]
    if blockers:
        sample = "; ".join(f"{item.code}: {item.message}" for item in blockers[:5])
        raise GoShipitError(
            f"Cannot publish: verify-run found {report.error_count} errors and "
            f"{report.warning_count} warnings. Fix the evidence and rerun. First findings: {sample}"
        )

    _run_command(["git", "-C", str(worktree), "push", remote, f"{local_branch}:{pr_branch}"])
    gh = _run_command(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base,
            "--head",
            pr_branch,
            "--title",
            _required_record_string(record, "title"),
            "--body-file",
            str(body_file),
        ],
        cwd=worktree,
    )
    url = _last_non_empty_line(gh.stdout)
    if not url:
        raise GoShipitError("gh pr create did not return a PR URL")

    published_at = _now_iso()
    _record_pull_request(run.run_file, {"published_url": url, "published_at": published_at})
    _append_event(
        run.run_file.parent,
        "pull_request.published",
        url,
        timestamp=published_at,
        branch=pr_branch,
        remote=remote,
        base=base,
        url=url,
    )
    issue = show_issue(root, issue_ref)
    if issue.summary.status == "execution":
        _write_active_phase(issue.summary.issue_file, run.run_file, "publish")
    return PullRequestPublish(issue_ref=run.issue_ref, branch=pr_branch, remote=remote, base=base, url=url)


def _render_pr_body(
    *,
    root: Path,
    issue_ref: str,
    title: str,
    issue_body: str,
    commands: list[dict[str, object]],
    notes: str,
    worktree: Path,
    provider: str,
    remote: str,
    base: str,
    local_branch: str,
    pr_branch: str,
    auto_publish: bool,
) -> str:
    problem = _section(issue_body, "Problem") or title
    status = _git_output(worktree, "status", "--short")
    commits = _git_output(worktree, "log", "--oneline", f"{base}..HEAD")
    committed_diff = _git_output(worktree, "diff", "--stat", f"{base}...HEAD")
    unstaged_diff = _git_output(worktree, "diff", "--stat")
    staged_diff = _git_output(worktree, "diff", "--cached", "--stat")
    validation = _validation_lines(commands)
    notes_tail = _last_notes_section(notes)

    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        f"- Issue: `{issue_ref}`",
        f"- Problem: {problem}",
        "",
        "## Publish Plan",
        "",
        f"- Provider: `{provider}`",
        f"- Remote: `{remote}`",
        f"- Base branch: `{base}`",
        f"- Local work branch: `{local_branch}`",
        f"- PR branch: `{pr_branch}`",
        f"- Auto publish allowed by repo config: `{str(auto_publish).lower()}`",
        "",
        "## Validation",
        "",
        *validation,
        "",
        "## Commits",
        "",
        _fenced_or_empty(portable_text(root, commits), "No commits ahead of base yet."),
        "",
        "## Diff Stat",
        "",
        "Committed diff:",
        "",
        _fenced_or_empty(portable_text(root, committed_diff), "No committed diff found."),
        "",
        "Staged diff:",
        "",
        _fenced_or_empty(portable_text(root, staged_diff), "No staged diff found."),
        "",
        "Unstaged diff:",
        "",
        _fenced_or_empty(portable_text(root, unstaged_diff), "No unstaged diff found."),
        "",
        "## Working Tree Status",
        "",
        _fenced_or_empty(portable_text(root, status), "Clean."),
        "",
        "## Latest Notes",
        "",
        notes_tail or "No notes found.",
        "",
    ]
    if status.strip():
        lines.extend(
            [
                "## Publish Blocker",
                "",
                "The worktree has uncommitted changes. Commit or discard them before publishing this PR.",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _validation_lines(commands: list[dict[str, object]]) -> list[str]:
    if not commands:
        return ["- No command records found."]
    lines = []
    for command in commands:
        check = command.get("check")
        exit_code = command.get("exit_code")
        command_text = command.get("command")
        lines.append(f"- `{check}` exit `{exit_code}`: `{command_text}`")
    return lines


def _section(markdown: str, title: str) -> str:
    import re

    match = re.search(rf"^## {re.escape(title)}\s*$([\s\S]*?)(?=^## |\Z)", markdown, flags=re.MULTILINE)
    if match is None:
        return ""
    return " ".join(line.strip() for line in match.group(1).splitlines() if line.strip())


def _last_notes_section(notes: str) -> str:
    stripped = notes.strip()
    if not stripped:
        return ""
    marker = "\n## "
    index = stripped.rfind(marker)
    if index == -1:
        return stripped
    return stripped[index + 1 :]


def _fenced_or_empty(value: str, empty: str) -> str:
    text = value.strip()
    if not text:
        return empty
    return f"```text\n{text}\n```"


def _existing_pr_branch(run: dict[str, object]) -> str | None:
    record = run.get("pull_request")
    if not isinstance(record, dict):
        return None
    value = record.get("branch")
    return value if isinstance(value, str) and value.strip() else None


def _validate_branch_name(worktree: Path, branch: str) -> None:
    _run_command(["git", "-C", str(worktree), "check-ref-format", "--branch", branch])


def _require_clean_worktree(worktree: Path) -> None:
    status = _git_output(worktree, "status", "--porcelain")
    if status.strip():
        raise GoShipitError("Cannot publish PR while the worktree has uncommitted changes")


def _require_commits_ahead(worktree: Path, base: str) -> None:
    count = _git_output(worktree, "rev-list", "--count", f"{base}..HEAD").strip()
    if count == "0":
        raise GoShipitError(f"Cannot publish PR because HEAD has no commits ahead of {base}")


def _git_output(worktree: Path, *args: str) -> str:
    return _run_command(["git", "-C", str(worktree), *args]).stdout


def _run_command(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, capture_output=True, check=False, cwd=cwd, text=True)
    except FileNotFoundError as exc:
        raise GoShipitError(f"Command not found: {command[0]}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GoShipitError(f"{' '.join(command)} failed: {detail}")
    return result


def _worktree_path(root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise GoShipitError("Run worktree is missing")
    path = Path(value)
    return path if path.is_absolute() else root / path


def _required_repo_string(repo: dict[str, object], key: str) -> str:
    value = repo.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GoShipitError(f"Repo config missing {key}")
    return value


def _required_run_string(run: dict[str, object], key: str) -> str:
    value = run.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GoShipitError(f"Run metadata missing {key}")
    return value


def _required_record_string(record: dict[object, object], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GoShipitError(f"Pull request preview missing {key}")
    return value


def _record_pull_request(run_file: Path, values: dict[str, object]) -> None:
    run = _parse_mapping(run_file.read_text())
    existing = run.get("pull_request")
    record = dict(existing) if isinstance(existing, dict) else {}
    record.update(values)
    run["pull_request"] = record
    run_file.write_text(_render_mapping(run))


def _last_non_empty_line(value: str) -> str:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
