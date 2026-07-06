from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from go_ship_it.state import (
    TRACK_REQUIRED_NOTE_SECTIONS,
    pull_request_config,
    read_repo_config,
    show_issue,
    show_run,
)


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


def _check_run_metadata(findings: list[VerificationFinding], run: dict[str, object]) -> None:
    for field in ("branch", "worktree"):
        if isinstance(run.get(field), str) and str(run[field]).strip():
            findings.append(_ok(f"run.{field}", f"run/{field}", f"{field} is recorded"))
        else:
            findings.append(_error(f"run.{field}_missing", f"run/{field}", f"{field} is missing"))


def _check_notes(findings: list[VerificationFinding], notes: str, track: str) -> None:
    for section in TRACK_REQUIRED_NOTE_SECTIONS[track]:
        if f"## {section}" in notes:
            findings.append(_ok(f"notes.{section.lower()}", f"notes/{section}", f"{section} note exists"))
        else:
            findings.append(
                _warning(f"notes.{section.lower()}_missing", f"notes/{section}", f"{section} note is missing")
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


def _check_acceptance_criteria(
    findings: list[VerificationFinding],
    issue_body: str,
    notes: str,
    commands: list[dict[str, object]],
) -> None:
    criteria = _acceptance_criteria(issue_body)
    if not criteria:
        findings.append(_warning("acceptance.criteria_missing", "acceptance", "No acceptance criteria found"))
        return

    evidence = _normalize_evidence_text(
        "\n".join(
            [
                notes,
                *(
                    "\n".join(
                        str(command.get(field) or "")
                        for field in ("check", "command", "stdout_tail", "stderr_tail")
                    )
                    for command in commands
                ),
            ]
        )
    )
    for index, criterion in enumerate(criteria, start=1):
        subject = f"acceptance/{index}"
        if _normalize_evidence_text(criterion) in evidence:
            findings.append(_ok("acceptance.criteria_covered", subject, f"Acceptance criterion has evidence: {criterion}"))
        else:
            findings.append(
                _warning(
                    "acceptance.criteria_missing_evidence",
                    subject,
                    f"Acceptance criterion lacks explicit evidence: {criterion}",
                )
            )


def _acceptance_criteria(issue_body: str) -> list[str]:
    match = re.search(r"^## Acceptance Criteria\s*$([\s\S]*?)(?=^## |\Z)", issue_body, flags=re.MULTILINE)
    if match is None:
        return []
    criteria = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            value = stripped[2:].strip()
            if value:
                criteria.append(value)
    return criteria


def _normalize_evidence_text(value: str) -> str:
    return re.sub(r"\W+", " ", value.casefold()).strip()


def _check_active_handoff(findings: list[VerificationFinding], root: Path, run_file: Path, issue_status: str) -> None:
    if issue_status != "execution":
        return
    handoff = run_file.parent / "handoff.md"
    if handoff.exists():
        findings.append(_ok("handoff.present", "handoff", "Active run handoff exists"))
    else:
        findings.append(_warning("handoff.missing", "handoff", "Active run has no handoff file"))


def _check_cleanup_and_exports(
    findings: list[VerificationFinding],
    root: Path,
    issue_id: str,
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
        findings.append(
            _ok("publish.not_required", "publish", "Repo has no publish target; local pr.md sign-off is the gate")
        )
        return
    record = run.get("pull_request")
    if isinstance(record, dict) and isinstance(record.get("published_url"), str) and record["published_url"].strip():
        findings.append(_ok("publish.recorded", "publish", f"Published: {record['published_url']}"))
    else:
        findings.append(_warning("publish.missing", "publish", "Archived without a published PR"))


def _export_is_stale(export: dict[object, object], closed_at: object) -> bool:
    if export.get("issue_status") != "archive" or export.get("run_phase") != "archived":
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
