from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from go_ship_it.state import show_issue, show_run


@dataclass(frozen=True)
class VerificationFinding:
    level: str
    code: str
    subject: str
    message: str


@dataclass(frozen=True)
class VerificationReport:
    errors: list[VerificationFinding]
    warnings: list[VerificationFinding]
    ok: list[VerificationFinding]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def ok_count(self) -> int:
        return len(self.ok)


def verify_run(root: Path, issue_id: str) -> VerificationReport:
    findings: list[VerificationFinding] = []
    try:
        issue = show_issue(root, issue_id)
        findings.append(_ok("issue.exists", "issue/file", f"Issue file exists in {issue.summary.status}"))
    except FileNotFoundError as exc:
        findings.append(_error("issue.missing", "issue/file", str(exc)))
        issue = None

    try:
        run = show_run(root, issue_id)
        findings.append(_ok("run.exists", "run/file", "Run metadata exists"))
    except FileNotFoundError as exc:
        findings.append(_error("run.missing", "run/file", str(exc)))
        return _report(findings)

    _check_run_metadata(findings, run.run)
    _check_journal(findings, run.journal)
    _check_commands(findings, run.commands)
    if issue is not None:
        _check_cleanup_and_exports(findings, issue.summary.status, issue.metadata, run.run)
    return _report(findings)


def _check_run_metadata(findings: list[VerificationFinding], run: dict[str, object]) -> None:
    for field in ("branch", "worktree"):
        if isinstance(run.get(field), str) and str(run[field]).strip():
            findings.append(_ok(f"run.{field}", f"run/{field}", f"{field} is recorded"))
        else:
            findings.append(_error(f"run.{field}_missing", f"run/{field}", f"{field} is missing"))


def _check_journal(findings: list[VerificationFinding], journal: str) -> None:
    required_sections = ("Investigation", "Proposal", "Implementation", "Review")
    for section in required_sections:
        if f"## {section}" in journal:
            findings.append(_ok(f"journal.{section.lower()}", f"journal/{section}", f"{section} evidence exists"))
        else:
            findings.append(
                _warning(f"journal.{section.lower()}_missing", f"journal/{section}", f"{section} evidence is missing")
            )


def _check_commands(findings: list[VerificationFinding], commands: list[dict[str, object]]) -> None:
    if not commands:
        findings.append(_warning("commands.missing", "commands", "No command records found"))
        return
    checks = {str(command.get("check")) for command in commands}
    if "test" in checks:
        findings.append(_ok("commands.test_present", "commands/test", "Test check was recorded"))
    else:
        findings.append(_warning("commands.test_missing", "commands/test", "No test check record found"))
    for command in commands:
        exit_code = command.get("exit_code")
        check = str(command.get("check"))
        if exit_code == 0:
            findings.append(_ok(f"command.{check}_passed", f"commands/{check}", f"{check} command exited 0"))
        else:
            findings.append(_error("command.failed", f"commands/{check}", f"{check} command exited {exit_code}"))


def _check_cleanup_and_exports(
    findings: list[VerificationFinding],
    issue_status: str,
    metadata: dict[str, object],
    run: dict[str, object],
) -> None:
    if issue_status != "archive":
        return
    if run.get("cleanup_destination") == "archive" and isinstance(run.get("closed_at"), str):
        findings.append(_ok("run.cleanup_recorded", "run/cleanup", "Archive cleanup is recorded"))
    else:
        findings.append(_warning("run.cleanup_missing", "run/cleanup", "Archived issue is missing cleanup metadata"))

    exports = run.get("exports")
    latest_export = exports[-1] if isinstance(exports, list) and exports and isinstance(exports[-1], dict) else None
    closed_at = run.get("closed_at")
    if latest_export is None:
        findings.append(_warning("run.export_missing", "export/latest", "No export metadata found"))
    elif _export_is_stale(latest_export, closed_at):
        findings.append(_warning("run.export_stale", "export/latest", "Latest export was written before cleanup"))
    else:
        findings.append(_ok("run.export_fresh", "export/latest", "Latest export reflects cleanup timing"))

    if isinstance(metadata.get("worktree"), str):
        findings.append(
            _warning(
                "worktree.preserved_after_archive",
                "worktree/preserved",
                "Archived issue still has a preserved worktree for review",
            )
        )


def _export_is_stale(export: dict[object, object], closed_at: object) -> bool:
    if export.get("issue_status") != "archive" or export.get("run_phase") != "cleanup":
        return True
    exported_at = export.get("exported_at")
    return isinstance(closed_at, str) and isinstance(exported_at, str) and exported_at < closed_at


def _report(findings: list[VerificationFinding]) -> VerificationReport:
    return VerificationReport(
        errors=[item for item in findings if item.level == "error"],
        warnings=[item for item in findings if item.level == "warning"],
        ok=[item for item in findings if item.level == "ok"],
    )


def _error(code: str, subject: str, message: str) -> VerificationFinding:
    return VerificationFinding("error", code, subject, message)


def _warning(code: str, subject: str, message: str) -> VerificationFinding:
    return VerificationFinding("warning", code, subject, message)


def _ok(code: str, subject: str, message: str) -> VerificationFinding:
    return VerificationFinding("ok", code, subject, message)
