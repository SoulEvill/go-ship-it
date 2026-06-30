from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from go_ship_it.frontmatter import parse_frontmatter
from go_ship_it.state import STATE_DIRS


@dataclass(frozen=True)
class DoctorFinding:
    level: str
    code: str
    subject: str
    message: str


@dataclass(frozen=True)
class DoctorReport:
    errors: list[DoctorFinding]
    warnings: list[DoctorFinding]
    ok: list[DoctorFinding]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def ok_count(self) -> int:
        return len(self.ok)


def run_doctor(root: Path, *, repo_id: str | None = None) -> DoctorReport:
    findings: list[DoctorFinding] = []
    findings.extend(_check_layout(root))
    findings.extend(_check_repos(root, repo_id=repo_id))
    findings.extend(_check_issues(root))
    findings.extend(_check_runs_and_worktrees(root))
    findings.extend(_check_skills(root))
    return _report(findings)


def _check_layout(root: Path) -> list[DoctorFinding]:
    missing = [relative for relative in STATE_DIRS if not (root / relative).exists()]
    if missing:
        return [
            DoctorFinding(
                "error",
                "layout.missing",
                "layout",
                f"Missing required directories: {', '.join(missing)}",
            )
        ]
    return [DoctorFinding("ok", "layout.exists", "layout", "Required state directories exist")]


def _check_repos(root: Path, *, repo_id: str | None) -> list[DoctorFinding]:
    repo_dir = root / "state" / "repos"
    repo_files = sorted(repo_dir.glob("*.yaml")) if repo_dir.exists() else []
    if repo_id is not None:
        repo_files = [path for path in repo_files if path.stem == _safe_id(repo_id)]
    findings: list[DoctorFinding] = []
    for repo_file in repo_files:
        subject = f"repo/{repo_file.stem}"
        try:
            config = _parse_mapping(repo_file.read_text())
        except Exception as exc:
            findings.append(DoctorFinding("error", "repo.invalid_yaml", subject, str(exc)))
            continue

        for field in ("id", "path", "default_branch", "worktree_root"):
            if not isinstance(config.get(field), str) or not str(config.get(field)).strip():
                findings.append(DoctorFinding("error", f"repo.{field}_missing", subject, f"{field} must be set"))

        if config.get("id") != repo_file.stem:
            findings.append(
                DoctorFinding("error", "repo.id_mismatch", subject, "repo id must match registry filename")
            )

        path_value = config.get("path")
        if isinstance(path_value, str):
            target_repo = Path(path_value)
            if not target_repo.is_absolute():
                target_repo = (root / target_repo).resolve()
            if not target_repo.exists():
                findings.append(DoctorFinding("error", "repo.path_missing", subject, f"Missing path: {target_repo}"))
            elif not _git_ok(target_repo, "rev-parse", "--is-inside-work-tree"):
                findings.append(DoctorFinding("error", "repo.not_git", subject, f"Not a git worktree: {target_repo}"))
            elif isinstance(config.get("default_branch"), str) and not _git_ok(
                target_repo,
                "rev-parse",
                "--verify",
                str(config["default_branch"]),
            ):
                findings.append(
                    DoctorFinding(
                        "error",
                        "repo.default_branch_missing",
                        subject,
                        f"Default branch not found: {config['default_branch']}",
                    )
                )
            else:
                findings.append(DoctorFinding("ok", "repo.path_ok", subject, "Target repo exists and is git-backed"))

        worktree_root = config.get("worktree_root")
        if isinstance(worktree_root, str):
            resolved = (root / worktree_root).resolve()
            try:
                resolved.relative_to((root / "worktrees").resolve())
            except ValueError:
                findings.append(
                    DoctorFinding(
                        "error",
                        "repo.worktree_root_unmanaged",
                        subject,
                        "worktree_root must stay under worktrees/",
                    )
                )

        for command in ("setup_command", "test_command", "lint_command"):
            if isinstance(config.get(command), str) and str(config[command]).strip():
                findings.append(DoctorFinding("ok", f"repo.{command}_configured", subject, f"{command} is configured"))
            else:
                findings.append(
                    DoctorFinding("warning", f"repo.{command}_missing", subject, f"{command} is not configured")
                )
    return findings


def _report(findings: list[DoctorFinding]) -> DoctorReport:
    return DoctorReport(
        errors=[item for item in findings if item.level == "error"],
        warnings=[item for item in findings if item.level == "warning"],
        ok=[item for item in findings if item.level == "ok"],
    )


def _check_issues(root: Path) -> list[DoctorFinding]:
    findings: list[DoctorFinding] = []
    by_id: dict[str, list[tuple[str, Path, dict[str, object]]]] = {}

    for state, issue_file in _issue_files(root):
        subject = f"issue/{issue_file.stem}"
        try:
            metadata, _body = parse_frontmatter(issue_file.read_text())
        except Exception as exc:
            findings.append(DoctorFinding("error", "issue.invalid_frontmatter", subject, str(exc)))
            continue

        issue_id = metadata.get("id")
        if not isinstance(issue_id, str) or not issue_id.strip():
            findings.append(DoctorFinding("error", "issue.id_missing", subject, "issue id must be set"))
            continue

        by_id.setdefault(issue_id, []).append((state, issue_file, metadata))
        if issue_id != issue_file.stem:
            findings.append(
                DoctorFinding("error", "issue.id_mismatch", subject, "issue id must match issue filename")
            )

        status = metadata.get("status")
        if status != state:
            findings.append(
                DoctorFinding("error", "issue.status_mismatch", subject, f"status must match folder: {state}")
            )

        repo = metadata.get("repo")
        if not isinstance(repo, str) or not repo.strip():
            findings.append(DoctorFinding("error", "issue.repo_missing", subject, "repo must be set"))
        elif not (root / "state" / "repos" / f"{_safe_id(repo)}.yaml").exists():
            findings.append(
                DoctorFinding("error", "issue.repo_unregistered", subject, f"repo is not registered: {repo}")
            )

        if state == "execution":
            run_file = root / "state" / "runs" / issue_id / "run.yaml"
            if not run_file.exists():
                findings.append(
                    DoctorFinding("error", "run.missing_metadata", f"run/{issue_id}", "execution issue has no run.yaml")
                )
            else:
                findings.extend(_check_active_run_metadata(root, issue_id, metadata, run_file))

            worktree = metadata.get("worktree")
            if isinstance(worktree, str) and not (root / worktree).exists():
                findings.append(
                    DoctorFinding(
                        "error",
                        "worktree.missing",
                        f"worktree/{worktree}",
                        "active issue worktree path is missing",
                    )
                )

    for issue_id, occurrences in by_id.items():
        if len(occurrences) > 1:
            locations = ", ".join(path.relative_to(root).as_posix() for _state, path, _metadata in occurrences)
            findings.append(
                DoctorFinding(
                    "error",
                    "issue.duplicate_id",
                    f"issue/{issue_id}",
                    f"issue id appears in multiple files: {locations}",
                )
            )

    return findings


def _check_active_run_metadata(
    root: Path,
    issue_id: str,
    issue_metadata: dict[str, object],
    run_file: Path,
) -> list[DoctorFinding]:
    subject = f"run/{issue_id}"
    try:
        run = _parse_mapping(run_file.read_text())
    except Exception as exc:
        return [DoctorFinding("error", "run.invalid_yaml", subject, str(exc))]

    findings: list[DoctorFinding] = []
    if run.get("worktree") != issue_metadata.get("worktree"):
        findings.append(
            DoctorFinding("error", "run.worktree_mismatch", subject, "run worktree must match active issue metadata")
        )
    if run.get("branch") != issue_metadata.get("branch"):
        findings.append(
            DoctorFinding("error", "run.branch_mismatch", subject, "run branch must match active issue metadata")
        )
    if (root / "state" / "runs" / issue_id / "claim.lock").exists():
        findings.append(DoctorFinding("ok", "claim.exists", f"claim/{issue_id}", "claim lock exists for active issue"))
    return findings


def _check_runs_and_worktrees(root: Path) -> list[DoctorFinding]:
    findings: list[DoctorFinding] = []
    issue_ids = {path.stem for _state, path in _issue_files(root)}
    active_issue_ids = {path.stem for state, path in _issue_files(root) if state == "execution"}

    runs_root = root / "state" / "runs"
    for run_dir in sorted(runs_root.glob("issue-*")) if runs_root.exists() else []:
        if not run_dir.is_dir():
            continue
        issue_id = run_dir.name
        if issue_id not in issue_ids:
            findings.append(
                DoctorFinding("warning", "run.without_issue", f"run/{issue_id}", "run directory has no issue file")
            )
        claim = run_dir / "claim.lock"
        if claim.exists() and issue_id not in active_issue_ids:
            findings.append(
                DoctorFinding(
                    "error",
                    "claim.stale_lock",
                    f"claim/{issue_id}",
                    "claim lock exists without an active execution issue",
                )
            )

    worktrees_root = root / "worktrees"
    for worktree in _managed_worktree_dirs(worktrees_root):
        issue_id = worktree.name
        subject = f"worktree/{worktree.relative_to(worktrees_root).as_posix()}"
        if issue_id not in issue_ids:
            findings.append(
                DoctorFinding(
                    "warning",
                    "worktree.preserved_without_issue",
                    subject,
                    "preserved worktree has no matching issue file",
                )
            )
        elif issue_id not in active_issue_ids:
            findings.append(
                DoctorFinding(
                    "warning",
                    "worktree.preserved_without_active_issue",
                    subject,
                    "preserved worktree has no active execution issue",
                )
            )
    return findings


def _check_skills(root: Path) -> list[DoctorFinding]:
    skills_root = root / "skills"
    findings: list[DoctorFinding] = []
    if not skills_root.exists():
        return findings

    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        subject = f"skill/{skill_dir.name}"
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            findings.append(DoctorFinding("error", "skill.missing", subject, "SKILL.md is missing"))
            continue

        findings.append(DoctorFinding("ok", "skill.exists", subject, "SKILL.md exists"))
        for reference in _mentioned_references(skill_file.read_text()):
            if not (skill_dir / reference).exists():
                findings.append(
                    DoctorFinding(
                        "warning",
                        "skill.reference_missing",
                        subject,
                        f"Referenced file does not exist: {reference}",
                    )
                )
    return findings


def _issue_files(root: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for state in ("todo", "execution", "archive"):
        directory = root / "state" / "issues" / state
        if directory.exists():
            files.extend((state, path) for path in sorted(directory.glob("issue-*.md")))
    return files


def _managed_worktree_dirs(worktrees_root: Path) -> list[Path]:
    if not worktrees_root.exists():
        return []
    issue_dirs: list[Path] = []
    for repo_dir in sorted(path for path in worktrees_root.iterdir() if path.is_dir()):
        issue_dirs.extend(sorted(path for path in repo_dir.glob("issue-*") if path.is_dir()))
    return issue_dirs


def _mentioned_references(text: str) -> list[str]:
    references: list[str] = []
    for match in re.findall(r"references/[A-Za-z0-9._/-]+", text):
        reference = match.rstrip(".,);:`'\"")
        if reference != "references/":
            references.append(reference)
    return sorted(set(references))


def _git_ok(repo: Path, *args: str) -> bool:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False, text=True)
    return result.returncode == 0


def _parse_mapping(text: str) -> dict[str, object]:
    loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise ValueError("YAML file must contain a mapping")
    return {str(key): value for key, value in loaded.items()}


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value.strip().lower()).strip("-")
