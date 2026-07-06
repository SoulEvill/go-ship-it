from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from go_ship_it.frontmatter import parse_frontmatter
from go_ship_it.package_assets import package_root
from go_ship_it.state import ISSUE_STATES, STATE_DIRS, repo_config_exists, repo_config_files, repo_config_id


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
    findings.extend(_check_package(package_root()))
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
    repo_files = repo_config_files(root, repo_id=repo_id)
    findings: list[DoctorFinding] = []
    for repo_file in repo_files:
        registry_id = repo_config_id(repo_file)
        subject = f"repo/{registry_id}"
        try:
            config = _parse_mapping(repo_file.read_text())
        except Exception as exc:
            findings.append(DoctorFinding("error", "repo.invalid_yaml", subject, str(exc)))
            continue

        for field in ("id", "path", "default_branch", "worktree_root"):
            if not isinstance(config.get(field), str) or not str(config.get(field)).strip():
                findings.append(DoctorFinding("error", f"repo.{field}_missing", subject, f"{field} must be set"))

        if config.get("id") != registry_id:
            findings.append(
                DoctorFinding("error", "repo.id_mismatch", subject, "repo id must match registry filename")
            )

        if repo_file.name == "repo.yaml":
            context_file = repo_file.parent / "context.md"
            if context_file.exists():
                findings.append(DoctorFinding("ok", "repo.context_exists", subject, "Repo context file exists"))
            else:
                findings.append(
                    DoctorFinding("warning", "repo.context_missing", subject, "Repo context file is missing")
                )
            for issue_state in ISSUE_STATES:
                issue_dir = repo_file.parent / "issues" / issue_state
                if issue_dir.is_dir():
                    findings.append(
                        DoctorFinding("ok", f"repo.issues_{issue_state}_exists", subject, f"{issue_state} issue folder exists")
                    )
                else:
                    findings.append(
                        DoctorFinding(
                            "error",
                            f"repo.issues_{issue_state}_missing",
                            subject,
                            f"Missing repo issue folder: issues/{issue_state}",
                        )
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

        configured_commands = []
        for command in ("setup_command", "test_command", "lint_command"):
            if isinstance(config.get(command), str) and str(config[command]).strip():
                configured_commands.append(command)
                findings.append(DoctorFinding("ok", f"repo.{command}_configured", subject, f"{command} is configured"))
        if not configured_commands:
            findings.append(
                DoctorFinding(
                    "warning",
                    "repo.no_checks_configured",
                    subject,
                    "No setup, test, or lint command is configured",
                )
            )

        worktree_setup = config.get("worktree_setup")
        if worktree_setup is not None:
            if not isinstance(worktree_setup, dict):
                findings.append(
                    DoctorFinding("error", "repo.worktree_setup_invalid", subject, "worktree_setup must be a mapping")
                )
            else:
                command = worktree_setup.get("command")
                if command is None:
                    pass
                elif isinstance(command, str) and command.strip():
                    findings.append(
                        DoctorFinding(
                            "ok",
                            "repo.worktree_setup_command_configured",
                            subject,
                            "worktree_setup.command is configured",
                        )
                    )
                else:
                    findings.append(
                        DoctorFinding(
                            "error",
                            "repo.worktree_setup_command_invalid",
                            subject,
                            "worktree_setup.command must be a non-empty string or null",
                        )
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
    by_id: dict[tuple[str, str], list[tuple[str, Path, dict[str, object]]]] = {}

    for repo, state, issue_file in _issue_files(root):
        issue_dir = issue_file.parent
        subject = f"issue/{repo}/{issue_dir.name}"
        try:
            metadata, _body = parse_frontmatter(issue_file.read_text())
        except Exception as exc:
            findings.append(DoctorFinding("error", "issue.invalid_frontmatter", subject, str(exc)))
            continue

        issue_id = metadata.get("id")
        if not isinstance(issue_id, str) or not issue_id.strip():
            findings.append(DoctorFinding("error", "issue.id_missing", subject, "issue id must be set"))
            continue

        by_id.setdefault((repo, issue_id), []).append((state, issue_file, metadata))
        if issue_id != issue_dir.name:
            findings.append(
                DoctorFinding("error", "issue.id_mismatch", subject, "issue id must match issue filename")
            )

        if "status" in metadata:
            findings.append(
                DoctorFinding("error", "issue.status_redundant", subject, "status is path-derived and must not be set")
            )

        if "repo" in metadata:
            findings.append(
                DoctorFinding("error", "issue.repo_redundant", subject, "repo is path-derived and must not be set")
            )

        if not repo_config_exists(root, repo):
            findings.append(
                DoctorFinding("error", "issue.repo_unregistered", subject, f"repo is not registered: {repo}")
            )

        if state == "execution":
            run_file = issue_dir / "run.yaml"
            if not run_file.exists():
                findings.append(
                    DoctorFinding(
                        "error",
                        "run.missing_metadata",
                        f"run/{repo}/{issue_id}",
                        "execution issue has no run.yaml",
                    )
                )
            else:
                findings.extend(_check_active_run_metadata(root, repo, issue_id, metadata, run_file))

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

    for (repo, issue_id), occurrences in by_id.items():
        if len(occurrences) > 1:
            locations = ", ".join(path.relative_to(root).as_posix() for _state, path, _metadata in occurrences)
            findings.append(
                DoctorFinding(
                    "error",
                    "issue.duplicate_id",
                    f"issue/{repo}/{issue_id}",
                    f"issue id appears in multiple files: {locations}",
                )
            )

    return findings


def _check_active_run_metadata(
    root: Path,
    repo: str,
    issue_id: str,
    issue_metadata: dict[str, object],
    run_file: Path,
) -> list[DoctorFinding]:
    subject = f"run/{repo}/{issue_id}"
    try:
        run = _parse_mapping(run_file.read_text())
    except Exception as exc:
        return [DoctorFinding("error", "run.invalid_yaml", subject, str(exc))]

    findings: list[DoctorFinding] = []
    if run.get("repo") != repo:
        findings.append(DoctorFinding("error", "run.repo_mismatch", subject, "run repo must match repo folder"))
    if run.get("worktree") != issue_metadata.get("worktree"):
        findings.append(
            DoctorFinding("error", "run.worktree_mismatch", subject, "run worktree must match active issue metadata")
        )
    if run.get("branch") != issue_metadata.get("branch"):
        findings.append(
            DoctorFinding("error", "run.branch_mismatch", subject, "run branch must match active issue metadata")
        )
    if (run_file.parent / "claim.lock").exists():
        findings.append(
            DoctorFinding("ok", "claim.exists", f"claim/{repo}/{issue_id}", "claim lock exists for active issue")
        )
    return findings


def _check_runs_and_worktrees(root: Path) -> list[DoctorFinding]:
    findings: list[DoctorFinding] = []
    issue_keys = {(repo, path.parent.name) for repo, _state, path in _issue_files(root)}
    active_issue_keys = {(repo, path.parent.name) for repo, state, path in _issue_files(root) if state == "execution"}

    repos_root = root / "state" / "repos"
    for repo_dir in sorted(path for path in repos_root.iterdir() if path.is_dir()) if repos_root.exists() else []:
        repo = repo_dir.name
        for issue_state in ISSUE_STATES:
            issues_dir = repo_dir / "issues" / issue_state
            for issue_dir in sorted(issues_dir.glob("issue-*")) if issues_dir.exists() else []:
                if not issue_dir.is_dir():
                    continue
                issue_id = issue_dir.name
                key = (repo, issue_id)
                if (issue_dir / "run.yaml").exists() and key not in issue_keys:
                    findings.append(
                        DoctorFinding(
                            "warning",
                            "run.without_issue",
                            f"run/{repo}/{issue_id}",
                            "run metadata has no issue.md file",
                        )
                    )
                claim = issue_dir / "claim.lock"
                if not claim.exists() or key in active_issue_keys:
                    continue
                findings.append(
                    DoctorFinding(
                        "error",
                        "claim.stale_lock",
                        f"claim/{repo}/{issue_id}",
                        "claim lock exists without an active execution issue",
                    )
                )

    worktrees_root = root / "worktrees"
    for worktree in _managed_worktree_dirs(worktrees_root):
        repo = worktree.parent.name
        issue_id = worktree.name
        subject = f"worktree/{worktree.relative_to(worktrees_root).as_posix()}"
        key = (repo, issue_id)
        if key not in issue_keys:
            findings.append(
                DoctorFinding(
                    "warning",
                    "worktree.preserved_without_issue",
                    subject,
                    "preserved worktree has no matching issue file",
                )
            )
        elif key not in active_issue_keys:
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


def _check_package(root: Path) -> list[DoctorFinding]:
    findings: list[DoctorFinding] = []
    manifests = {
        ".claude-plugin/plugin.json": {"skills": None, "hooks": None},
        ".codex-plugin/plugin.json": {"skills": "./skills/", "hooks": None},
        ".cursor-plugin/plugin.json": {"skills": "./skills/", "hooks": "./hooks/hooks-cursor.json"},
    }

    project_version = _project_version(root)

    for relative, expected in manifests.items():
        path = root / relative
        subject = f"package/{relative}"
        if not path.exists():
            findings.append(DoctorFinding("warning", "package.manifest_missing", subject, "plugin manifest is missing"))
            continue

        try:
            manifest = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            findings.append(DoctorFinding("error", "package.manifest_invalid", subject, str(exc)))
            continue

        findings.append(DoctorFinding("ok", "package.manifest_ok", subject, "plugin manifest exists"))

        if manifest.get("name") != "go-ship-it":
            findings.append(
                DoctorFinding("warning", "package.name_mismatch", subject, "manifest name should be go-ship-it")
            )

        if project_version and manifest.get("version") != project_version:
            findings.append(
                DoctorFinding(
                    "warning",
                    "package.version_mismatch",
                    subject,
                    f"manifest version should match pyproject.toml: {project_version}",
                )
            )

        expected_skills = expected["skills"]
        if expected_skills is not None:
            if manifest.get("skills") != expected_skills:
                findings.append(
                    DoctorFinding(
                        "warning",
                        "package.skills_mismatch",
                        subject,
                        f"skills should be {expected_skills}",
                    )
                )
            elif not (root / str(expected_skills).rstrip("/")).exists():
                findings.append(
                    DoctorFinding("warning", "package.skills_missing", subject, "manifest skills path is missing")
                )

        expected_hooks = expected["hooks"]
        if expected_hooks is not None:
            if manifest.get("hooks") != expected_hooks:
                findings.append(
                    DoctorFinding(
                        "warning",
                        "package.hooks_mismatch",
                        subject,
                        f"hooks should be {expected_hooks}",
                    )
                )
            elif not (root / expected_hooks).exists():
                findings.append(
                    DoctorFinding("warning", "package.hooks_missing", subject, "manifest hooks path is missing")
                )

    bootstrap = root / "skills" / "using-go-ship-it" / "SKILL.md"
    if bootstrap.exists():
        findings.append(DoctorFinding("ok", "package.bootstrap_ok", "package/bootstrap", "bootstrap skill exists"))
    else:
        findings.append(
            DoctorFinding("warning", "package.bootstrap_missing", "package/bootstrap", "using-go-ship-it skill is missing")
        )

    for relative in ("hooks/session-start", "hooks/run-hook.cmd", "hooks/hooks-cursor.json"):
        path = root / relative
        if path.exists():
            findings.append(DoctorFinding("ok", "package.hook_ok", f"package/{relative}", "hook file exists"))
        else:
            findings.append(
                DoctorFinding("warning", "package.hook_missing", f"package/{relative}", "hook file is missing")
            )

    return findings


def _project_version(root: Path) -> str | None:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return None
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), flags=re.MULTILINE)
    if match:
        return match.group(1)
    return None


def _issue_files(root: Path) -> list[tuple[str, str, Path]]:
    files: list[tuple[str, str, Path]] = []
    repos_root = root / "state" / "repos"
    if not repos_root.exists():
        return files
    for repo_dir in sorted(path for path in repos_root.iterdir() if path.is_dir()):
        for state in ISSUE_STATES:
            directory = repo_dir / "issues" / state
            if directory.exists():
                files.extend(
                    (repo_dir.name, state, path / "issue.md")
                    for path in sorted(directory.glob("issue-*"))
                    if path.is_dir() and (path / "issue.md").exists()
                )
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
