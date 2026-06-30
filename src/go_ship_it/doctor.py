from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

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
