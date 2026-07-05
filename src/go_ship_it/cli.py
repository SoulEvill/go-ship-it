from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from go_ship_it.doctor import run_doctor
from go_ship_it.package_assets import package_root
from go_ship_it.portable import portable_path_value, portable_text, relative_to_root
from go_ship_it.pull_request import prepare_pull_request, publish_pull_request
from go_ship_it.state import (
    CheckFailedError,
    GoShipitError,
    add_issue,
    append_note,
    cleanup_issue,
    ensure_layout,
    export_run,
    list_issues,
    read_repo_config,
    register_feedback_repo,
    register_repo,
    render_handoff,
    resolve_current_run,
    run_check,
    run_timeline,
    set_phase,
    show_issue,
    show_run,
    start_issue,
    update_repo_config,
    write_handoff,
    workspace_status,
)
from go_ship_it.verify import verify_run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="go-ship-it",
        description="GoShipit local issue lifecycle manager.",
        epilog=(
            "Normal path:\n"
            "  init --repo-id <id> --repo-source <path-or-git-url> [--test-command <cmd>]\n"
            "  add-issue --repo <id> --title <title> --problem <problem>\n"
            "  start-issue <repo>/<issue-id>\n"
            "  status\n"
            "  run-check <repo>/<issue-id> --check test    # or run-check --current --check test from the worktree\n"
            "  cleanup-issue <repo>/<issue-id> --destination archive --note <note> --remove-worktree\n\n"
            "Advanced/support:\n"
            "  show-issue, show-run, handoff, append-note, set-phase,\n"
            "  export-run, prepare-pr, publish-pr, verify-run, doctor, package-root, update-repo\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", default=".", help="GoShipit repo root. Defaults to current directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser(
        "init",
        help="Create state folders, optionally registering the first target repo.",
        description="Create the local GoShipit state folders. Optionally register the first target repo.",
    )
    init.add_argument("--repo-id", default=None, help="Optional target repo id to register during init.")
    init.add_argument("--repo-source", default=None, help="Optional target repo path or Git URL to register during init.")
    init.add_argument("--default-branch", default="main")
    init.add_argument("--setup-command", default=None)
    init.add_argument("--test-command", default=None)
    init.add_argument("--lint-command", default=None)
    init.add_argument("--worktree-setup-command", default=None)
    init.add_argument(
        "--feedback-repo-source",
        default=None,
        help="Optional GoShipit repo path or Git URL to register as the go-ship-it product feedback target.",
    )
    init.add_argument(
        "--feedback-test-command",
        default=None,
        help="Optional test command for the go-ship-it feedback repo.",
    )
    subparsers.add_parser("package-root", help="Print the bundled GoShipit agent package root.")

    register = subparsers.add_parser("register-repo", help="Register a target repository from a local path or Git URL.")
    register.add_argument("repo_id")
    register.add_argument("source")
    register.add_argument("--default-branch", default="main")
    register.add_argument("--setup-command", default=None)
    register.add_argument("--test-command", default=None)
    register.add_argument("--lint-command", default=None)
    register.add_argument("--worktree-setup-command", default=None)

    show_repo = subparsers.add_parser("show-repo", help="Print a registered repo configuration.")
    show_repo.add_argument("repo_id")

    update_repo = subparsers.add_parser("update-repo", help="Update a registered repo configuration.")
    update_repo.add_argument("repo_id")
    update_repo.add_argument("--path", default=None)
    update_repo.add_argument("--default-branch", default=None)
    update_repo.add_argument("--worktree-root", default=None)
    update_repo.add_argument("--setup-command", default=None)
    update_repo.add_argument("--test-command", default=None)
    update_repo.add_argument("--lint-command", default=None)
    update_repo.add_argument("--worktree-setup-command", default=None)
    update_repo.add_argument("--pr-provider", default=None)
    update_repo.add_argument("--pr-remote", default=None)
    update_repo.add_argument("--pr-auto-publish", action=argparse.BooleanOptionalAction, default=None)
    update_repo.add_argument("--clear-setup-command", action="store_true")
    update_repo.add_argument("--clear-test-command", action="store_true")
    update_repo.add_argument("--clear-lint-command", action="store_true")
    update_repo.add_argument("--clear-worktree-setup-command", action="store_true")

    issue = subparsers.add_parser("add-issue", help="Create a todo issue.")
    issue.add_argument("--repo", required=True)
    issue.add_argument("--title", required=True)
    issue.add_argument("--problem", required=True)
    issue.add_argument("--context", default="")
    issue.add_argument("--acceptance", action="append", default=[])

    start = subparsers.add_parser("start-issue", help="Claim a todo issue and create its worktree.")
    start.add_argument("issue_id")
    start.add_argument("--claimed-by", default=None)

    cleanup = subparsers.add_parser("cleanup-issue", help="Return an execution issue to todo or archive it.")
    cleanup.add_argument("issue_id", nargs="?")
    cleanup.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    cleanup.add_argument("--destination", choices=["todo", "archive"], required=True)
    cleanup.add_argument("--note", required=True)
    cleanup.add_argument(
        "--remove-worktree",
        action="store_true",
        help="Remove the managed worktree. Required when returning to todo.",
    )

    note = subparsers.add_parser("append-note", help="Append an authored note for an active issue.")
    note.add_argument("issue_id", nargs="?")
    note.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    note.add_argument("--section", required=True)
    note.add_argument("--note", required=True)
    note.add_argument("--phase", default=None)

    phase = subparsers.add_parser("set-phase", help="Set the current workflow phase for an active issue.")
    phase.add_argument("issue_id", nargs="?")
    phase.add_argument("phase", nargs="?")
    phase.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    phase.add_argument("--note", required=True)

    check = subparsers.add_parser("run-check", help="Run a registered repo check and record evidence.")
    check.add_argument("issue_id", nargs="?")
    check.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    check.add_argument("--check", choices=["setup", "test", "lint"], required=True)

    list_cmd = subparsers.add_parser("list-issues", help="List issues.")
    list_cmd.add_argument("--state", choices=["todo", "execution", "archive", "all"], default="all")
    list_cmd.add_argument("--repo", default=None)

    show_issue_cmd = subparsers.add_parser("show-issue", help="Show one issue.")
    show_issue_cmd.add_argument("issue_id", nargs="?")
    show_issue_cmd.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")

    show_run_cmd = subparsers.add_parser("show-run", help="Show one run.")
    show_run_cmd.add_argument("issue_id", nargs="?")
    show_run_cmd.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    show_run_cmd.add_argument("--commands", action="store_true")
    show_run_cmd.add_argument("--trace", action="store_true", help="Show generated chronological event logs.")
    show_run_cmd.add_argument("--handoff", action="store_true", help="Show copy-pasteable resume context.")

    handoff = subparsers.add_parser("handoff", help="Print or write resume context for one run.")
    handoff.add_argument("issue_id", nargs="?")
    handoff.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    handoff.add_argument(
        "--write",
        action="store_true",
        help="Write state/repos/<repo>/issues/<state>/<issue-id>/handoff.md.",
    )
    handoff.add_argument("--output", default=None, help="Write handoff markdown to a custom path.")

    status = subparsers.add_parser("status", help="Show workspace status.")
    status.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    doctor = subparsers.add_parser("doctor", help="Check local GoShipit workspace health.")
    doctor.add_argument("--repo", default=None)
    doctor.add_argument("--strict", action="store_true", help="Exit non-zero when warnings exist.")
    doctor.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    verify = subparsers.add_parser("verify-run", help="Verify one run's evidence structure.")
    verify.add_argument("issue_id", nargs="?")
    verify.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    verify.add_argument("--strict", action="store_true", help="Exit non-zero when warnings exist.")
    verify.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

    export = subparsers.add_parser("export-run", help="Export run evidence to Markdown.")
    export.add_argument("issue_id", nargs="?")
    export.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    export.add_argument("--output", default=None, help="Defaults to evidence.md inside the issue folder.")

    prepare_pr = subparsers.add_parser("prepare-pr", help="Write a local PR preview markdown file.")
    prepare_pr.add_argument("issue_id", nargs="?")
    prepare_pr.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    prepare_pr.add_argument("--branch", default=None, help="PR branch name to publish later.")
    prepare_pr.add_argument("--title", default=None, help="PR title. Defaults to the issue title.")
    prepare_pr.add_argument("--output", default=None, help="Defaults to pr.md inside the issue folder.")

    publish_pr = subparsers.add_parser("publish-pr", help="Push the PR branch and create a GitHub PR.")
    publish_pr.add_argument("issue_id", nargs="?")
    publish_pr.add_argument("--current", action="store_true", help="Use the managed worktree's current run context.")
    publish_pr.add_argument("--branch", default=None, help="Override the PR branch name before publishing.")
    publish_pr.add_argument("--title", default=None, help="Override the PR title before publishing.")
    return parser


def _repo_updates(args: argparse.Namespace) -> tuple[dict[str, object], set[str]]:
    pairs = {
        "path": args.path,
        "default_branch": args.default_branch,
        "worktree_root": args.worktree_root,
        "setup_command": args.setup_command,
        "test_command": args.test_command,
        "lint_command": args.lint_command,
    }
    updates = {key: value for key, value in pairs.items() if value is not None}
    pr_updates = {
        key: value
        for key, value in {
            "provider": args.pr_provider,
            "remote": args.pr_remote,
            "auto_publish": args.pr_auto_publish,
        }.items()
        if value is not None
    }
    if pr_updates:
        updates["pull_request"] = pr_updates
    if args.worktree_setup_command is not None and args.clear_worktree_setup_command:
        raise ValueError("Cannot set and clear --worktree-setup-command")
    if args.worktree_setup_command is not None:
        updates["worktree_setup"] = {"command": args.worktree_setup_command}
    elif args.clear_worktree_setup_command:
        updates["worktree_setup"] = {"command": None}
    clears = {
        field
        for field, flag in {
            "setup_command": args.clear_setup_command,
            "test_command": args.clear_test_command,
            "lint_command": args.clear_lint_command,
        }.items()
        if flag
    }
    conflicts = sorted(set(updates) & clears)
    if conflicts:
        flags = ", ".join(f"--clear-{field.replace('_', '-')}" for field in conflicts)
        raise ValueError(f"Cannot set and clear the same command field: {flags}")
    return updates, clears


def _resolve_issue_target(root: Path, args: argparse.Namespace) -> tuple[Path, str]:
    issue_ref = getattr(args, "issue_id", None)
    if getattr(args, "current", False):
        current = resolve_current_run(Path.cwd())
        if issue_ref is not None and issue_ref != current.issue_ref:
            raise ValueError(
                f"--current resolved {current.issue_ref}, but command specified {issue_ref}. "
                "Use one issue ref or switch to the matching worktree."
            )
        return current.control_root, current.issue_ref
    if issue_ref is None:
        try:
            current = resolve_current_run(Path.cwd())
        except GoShipitError as exc:
            raise ValueError(
                "issue ref is required unless --current is used or the command is run from a managed worktree"
            ) from exc
        return current.control_root, current.issue_ref
    return root, issue_ref


def _resolve_phase_target(root: Path, args: argparse.Namespace) -> tuple[Path, str, str]:
    issue_id = args.issue_id
    phase = args.phase
    if phase is None and issue_id is not None and (args.current or _can_resolve_current_run()):
        phase = issue_id
        issue_id = None
    if phase is None:
        raise ValueError("phase is required")

    target_args = argparse.Namespace(issue_id=issue_id, current=args.current)
    resolved_root, resolved_issue = _resolve_issue_target(root, target_args)
    return resolved_root, resolved_issue, phase


def _can_resolve_current_run() -> bool:
    try:
        resolve_current_run(Path.cwd())
    except GoShipitError:
        return False
    return True


def _status_context(root: Path, args: argparse.Namespace) -> tuple[Path, object | None]:
    current = _maybe_current_run()
    if current is not None:
        if args.root == "." or current.control_root == root:
            return current.control_root, current
    if args.root != ".":
        return root, None
    return root, None


def _maybe_current_run() -> object | None:
    try:
        return resolve_current_run(Path.cwd())
    except GoShipitError:
        return None


def _format_issue_list(items: list[object]) -> str:
    if not items:
        return "No issues found."
    return "\n".join(f"{_summary_ref(item)} [{item.status}] - {item.title}" for item in items)


def _format_issue_detail(detail: object, root: Path) -> str:
    summary = detail.summary
    branch = detail.metadata.get("branch")
    worktree = detail.metadata.get("worktree")
    lines = [
        f"# {_summary_ref(summary)}",
        "",
        f"Title: {summary.title}",
        f"Repo: {summary.repo}",
        f"Status: {summary.status}",
        f"Phase: {summary.phase}",
        f"Branch: {_display_value(branch)}",
        f"Worktree: {_display_value(worktree)}",
        f"Issue File: {relative_to_root(root, summary.issue_file)}",
        "",
        detail.body or "No issue body found.",
    ]
    return "\n".join(lines).rstrip()


def _format_run_detail(detail: object, root: Path, *, include_commands: bool) -> str:
    lines = [
        f"# Run: {detail.issue_ref}",
        "",
        f"Run File: {relative_to_root(root, detail.run_file)}",
        f"Phase: {_display_value(detail.run.get('phase'))}",
        f"Branch: {_display_value(detail.run.get('branch'))}",
        f"Worktree: {_display_value(detail.run.get('worktree'))}",
        f"Claimed By: {_display_value(detail.run.get('claimed_by'))}",
        f"Claim ID: {_display_value(detail.run.get('claim_id'))}",
        "",
        "## Command Summary",
    ]
    if detail.commands:
        for command in detail.commands:
            check = _display_value(command.get("check"))
            exit_code = _display_value(command.get("exit_code"))
            command_text = portable_text(root, command.get("command"))
            lines.append(f"- {check} exit {exit_code}: {command_text}")
    else:
        lines.append("No command records found.")

    notes = portable_text(root, detail.notes).strip()
    lines.extend(["", "## Notes", "", notes or "No notes found."])

    if include_commands and detail.commands:
        lines.extend(["", "## Command Records"])
        for command in detail.commands:
            lines.extend(_format_command_record(command, root))

    return "\n".join(lines).rstrip()


def _format_timeline(issue_id: str, events: list[object]) -> str:
    lines = [f"# Trace: {issue_id}", ""]
    if not events:
        lines.append("No trace events found.")
        return "\n".join(lines)
    for event in events:
        lines.append(f"- {event.timestamp} {event.kind} {event.detail}".rstrip())
    return "\n".join(lines)


def _format_command_record(command: dict[str, object], root: Path) -> list[str]:
    record_file = command.get("record_file")
    record_label = relative_to_root(root, record_file) if isinstance(record_file, Path) else str(record_file)
    return [
        "",
        f"### {record_label}",
        "",
        f"- Check: `{_display_value(command.get('check'))}`",
        f"- Command: `{portable_text(root, command.get('command'))}`",
        f"- CWD: `{portable_path_value(root, command.get('cwd'))}`",
        f"- Exit Code: `{_display_value(command.get('exit_code'))}`",
        f"- Started: `{_display_value(command.get('started_at'))}`",
        f"- Ended: `{_display_value(command.get('ended_at'))}`",
        "",
        "Stdout tail:",
        "",
        "```text",
        portable_text(root, command.get("stdout_tail")).strip(),
        "```",
        "",
        "Stderr tail:",
        "",
        "```text",
        portable_text(root, command.get("stderr_tail")).strip(),
        "```",
    ]


def _format_status(status: object, root: Path, *, current: object | None = None) -> str:
    branch_path = current.worktree if current is not None else root
    branch = _current_branch(branch_path)
    lines = [
        "# GoShipit Status",
        "",
        f"Control Root: {root}",
        f"Package Root: {package_root()}",
        f"Current Git Branch: {branch or 'not a git worktree'}",
    ]
    if current is not None:
        lines.extend(
            [
                f"Current Issue: {current.issue_ref}",
                f"Current Worktree: {relative_to_root(root, current.worktree)}",
                f"Current Run Branch: {current.branch}",
                f"Current Claim ID: {current.claim_id}",
            ]
        )
    lines.extend(
        [
            "",
            f"Repos: {status.repo_count}",
            f"Todo: {status.todo_count}",
            f"Execution: {status.execution_count}",
            f"Archive: {status.archive_count}",
            f"Runs: {status.run_count}",
            f"Managed Worktrees: {len(status.worktrees)}",
        ]
    )
    lines.extend(_status_next_steps(status))
    lines.extend(_format_todo_status(root))
    lines.extend(["", "## Active Issues"])
    if status.active:
        for item in status.active:
            lines.append(f"- {_summary_ref(item)} {item.title}")
            lines.append(f"  Phase: {item.phase or 'unknown'}")
            try:
                detail = show_issue(root, _summary_ref(item))
                worktree = detail.metadata.get("worktree")
            except (OSError, ValueError):
                worktree = None
            if isinstance(worktree, str) and worktree:
                lines.append(f"  Worktree: {worktree}")
            try:
                run_detail = show_run(root, _summary_ref(item))
                claimed_by = run_detail.run.get("claimed_by")
                claim_id = run_detail.run.get("claim_id")
            except (OSError, ValueError):
                claimed_by = None
                claim_id = None
            if isinstance(claimed_by, str) and claimed_by:
                lines.append(f"  Claimed By: {claimed_by}")
            if isinstance(claim_id, str) and claim_id:
                lines.append(f"  Claim ID: {claim_id}")
            lines.append("  Next useful commands:")
            lines.extend(f"    {command}" for command in _active_issue_next_commands(root, item))
    else:
        lines.append("No active issues.")

    lines.extend(["", "## Preserved Worktrees"])
    if status.worktrees:
        lines.extend(f"- {item}" for item in status.worktrees)
    else:
        lines.append("No preserved worktrees.")
    return "\n".join(lines)


def _status_next_steps(status: object) -> list[str]:
    if status.repo_count == 0:
        return [
            "",
            "## Next Steps",
            "No target repos are registered yet.",
            "",
            "```sh",
            "go-ship-it register-repo <repo-id> <local-path-or-git-url> --test-command \"<cmd>\"",
            "go-ship-it add-issue --repo <repo-id> --title \"<title>\" --problem \"<problem>\"",
            "```",
        ]
    if status.todo_count == 0 and status.execution_count == 0:
        return [
            "",
            "## Next Steps",
            "No todo or active issues yet.",
            "",
            "```sh",
            "go-ship-it add-issue --repo <repo-id> --title \"<title>\" --problem \"<problem>\"",
            "```",
        ]
    return []


def _format_todo_status(root: Path) -> list[str]:
    todo = list_issues(root, state="todo")
    lines = ["", "## Todo Issues"]
    if not todo:
        lines.append("No todo issues.")
        return lines
    for item in todo:
        lines.append(f"- {_summary_ref(item)} {item.title}")
        lines.append("  Next useful command:")
        lines.append(f"    go-ship-it start-issue {_summary_ref(item)}")
    return lines


def _format_doctor_report(report: object) -> str:
    lines = [
        "# GoShipit Doctor",
        "",
        f"Summary: {report.error_count} errors, {report.warning_count} warnings, {report.ok_count} ok",
        "",
    ]
    for title, items in (("Errors", report.errors), ("Warnings", report.warnings), ("OK", report.ok)):
        lines.extend([f"## {title}"])
        if items:
            lines.extend(f"- {item.subject}: {item.message} ({item.code})" for item in items)
        else:
            lines.append("None.")
        lines.append("")
    return "\n".join(lines).rstrip()


def _format_verify_report(issue_id: str, report: object) -> str:
    lines = [
        f"# GoShipit Run Verification: {issue_id}",
        "",
        f"Summary: {report.error_count} errors, {report.warning_count} warnings, {report.ok_count} ok",
        "",
    ]
    for title, items in (("Errors", report.errors), ("Warnings", report.warnings), ("OK", report.ok)):
        lines.append(f"## {title}")
        if items:
            lines.extend(f"- {item.subject}: {item.message} ({item.code})" for item in items)
        else:
            lines.append("None.")
        lines.append("")
    return "\n".join(lines).rstrip()


def _status_payload(status: object, root: Path, *, current: object | None = None) -> dict[str, object]:
    current_payload = None
    if current is not None:
        current_payload = {
            "issue_id": current.issue_id,
            "repo": current.repo_id,
            "issue_ref": current.issue_ref,
            "worktree": relative_to_root(root, current.worktree),
            "branch": current.branch,
            "claim_id": current.claim_id,
            "claimed_by": current.claimed_by,
        }
    return {
        "control_root": str(root),
        "package_root": str(package_root()),
        "current_branch": _current_branch(current.worktree if current is not None else root),
        "current": current_payload,
        "summary": {
            "repos": status.repo_count,
            "todo": status.todo_count,
            "execution": status.execution_count,
            "archive": status.archive_count,
            "runs": status.run_count,
            "managed_worktrees": len(status.worktrees),
        },
        "todo": [_issue_summary_payload(item) for item in list_issues(root, state="todo")],
        "active": [_active_issue_payload(root, item) for item in status.active],
        "worktrees": list(status.worktrees),
    }


def _active_issue_payload(root: Path, item: object) -> dict[str, object]:
    payload = _issue_summary_payload(item)
    try:
        detail = show_issue(root, _summary_ref(item))
        worktree = detail.metadata.get("worktree")
    except (OSError, ValueError):
        worktree = None
    try:
        run_detail = show_run(root, _summary_ref(item))
        claimed_by = run_detail.run.get("claimed_by")
        claim_id = run_detail.run.get("claim_id")
    except (OSError, ValueError):
        claimed_by = None
        claim_id = None
    payload.update(
        {
            "worktree": worktree,
            "claimed_by": claimed_by,
            "claim_id": claim_id,
            "next_commands": _active_issue_next_commands(root, item),
        }
    )
    return payload


def _issue_summary_payload(item: object) -> dict[str, object]:
    return {
        "issue_id": item.issue_id,
        "issue_ref": _summary_ref(item),
        "status": item.status,
        "repo": item.repo,
        "title": item.title,
        "phase": item.phase,
        "issue_file": str(item.issue_file),
    }


def _report_payload(report: object) -> dict[str, object]:
    return {
        "summary": {
            "errors": report.error_count,
            "warnings": report.warning_count,
            "ok": report.ok_count,
        },
        "findings": {
            "errors": [_finding_payload(item) for item in report.errors],
            "warnings": [_finding_payload(item) for item in report.warnings],
            "ok": [_finding_payload(item) for item in report.ok],
        },
    }


def _finding_payload(item: object) -> dict[str, str]:
    return {
        "level": item.level,
        "code": item.code,
        "subject": item.subject,
        "message": item.message,
    }


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _display_value(value: object) -> str:
    return "" if value is None else str(value)


def _current_branch(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(root), "branch", "--show-current"],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch or None


def _configured_checks(root: Path, repo_id: str) -> list[str]:
    try:
        config = read_repo_config(root, repo_id)
    except (OSError, ValueError):
        return []
    checks = []
    for check, field in (("setup", "setup_command"), ("test", "test_command"), ("lint", "lint_command")):
        value = config.get(field)
        if isinstance(value, str) and value.strip():
            checks.append(check)
    return checks


def _active_issue_next_commands(root: Path, item: object) -> list[str]:
    ref = _summary_ref(item)
    commands = [
        f"go-ship-it show-run {ref}",
        f"go-ship-it show-run {ref} --trace",
        f"go-ship-it show-run {ref} --handoff",
    ]
    phase = (item.phase or "").strip().casefold()
    if phase in {"", "setup", "investigate"}:
        commands.extend(
            [
                f"go-ship-it append-note {ref} --section \"Investigation\" --phase investigate --note \"<findings>\"",
                f"go-ship-it set-phase {ref} propose --note \"<investigation summary>\"",
            ]
        )
    elif phase == "propose":
        commands.extend(
            [
                f"go-ship-it append-note {ref} --section \"Proposal\" --phase propose --note \"<proposal>\"",
                f"go-ship-it set-phase {ref} implement --note \"<proposal accepted>\"",
            ]
        )
    elif phase == "implement":
        commands.extend(
            [
                f"go-ship-it append-note {ref} --section \"Implementation\" --phase implement --note \"<changed files and decisions>\"",
                f"go-ship-it set-phase {ref} test --note \"<ready for checks>\"",
            ]
        )
    elif phase == "test":
        commands.append(f"go-ship-it append-note {ref} --section \"Review\" --phase test --note \"<readiness review>\"")

    checks = _configured_checks(root, item.repo)
    for check in checks:
        commands.append(f"go-ship-it run-check {ref} --check {check}")
    if phase == "test":
        commands.extend(
            [
                f"go-ship-it handoff {ref} --write",
                f"go-ship-it export-run {ref}",
                f"go-ship-it prepare-pr {ref} --branch <pr-branch>",
            ]
        )
    commands.extend(
        [
            f"go-ship-it verify-run {ref} --strict",
            f"go-ship-it cleanup-issue {ref} --destination archive --note \"<note>\" --remove-worktree",
        ]
    )
    return commands


def _summary_ref(item: object) -> str:
    return f"{item.repo}/{item.issue_id}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    root = Path(args.root).resolve()

    try:
        if args.command == "package-root":
            print(package_root())
            return 0

        if args.command == "init":
            ensure_layout(root)
            print(f"Initialized GoShipit state at {root}")
            has_repo_id = args.repo_id is not None
            has_repo_source = args.repo_source is not None
            if has_repo_id != has_repo_source:
                raise ValueError("--repo-id and --repo-source must be provided together")
            if args.feedback_test_command is not None and args.feedback_repo_source is None:
                raise ValueError("--feedback-test-command requires --feedback-repo-source")
            if has_repo_id and has_repo_source:
                repo_file = register_repo(
                    root,
                    repo_id=args.repo_id,
                    path=args.repo_source,
                    default_branch=args.default_branch,
                    setup_command=args.setup_command,
                    test_command=args.test_command,
                    lint_command=args.lint_command,
                    worktree_setup_command=args.worktree_setup_command,
                )
                print(f"Registered repo: {repo_file}")
            if args.feedback_repo_source is not None:
                feedback_file = register_feedback_repo(
                    root,
                    path=args.feedback_repo_source,
                    test_command=args.feedback_test_command,
                )
                print(f"Registered GoShipit feedback repo: {feedback_file}")
            return 0

        if args.command == "register-repo":
            repo_file = register_repo(
                root,
                repo_id=args.repo_id,
                path=args.source,
                default_branch=args.default_branch,
                setup_command=args.setup_command,
                test_command=args.test_command,
                lint_command=args.lint_command,
                worktree_setup_command=args.worktree_setup_command,
            )
            print(repo_file)
            return 0

        if args.command == "show-repo":
            config = read_repo_config(root, args.repo_id)
            print(yaml.safe_dump(config, sort_keys=False, default_flow_style=False), end="")
            return 0

        if args.command == "update-repo":
            updates, clears = _repo_updates(args)
            repo_file = update_repo_config(root, args.repo_id, updates=updates, clears=clears)
            print(repo_file)
            return 0

        if args.command == "add-issue":
            issue_file = add_issue(
                root,
                repo_id=args.repo,
                title=args.title,
                problem=args.problem,
                context=args.context,
                acceptance_criteria=args.acceptance,
            )
            print(issue_file)
            return 0

        if args.command == "start-issue":
            run = start_issue(root, args.issue_id, claimed_by=args.claimed_by)
            if run.already_active:
                print("Active run already exists.")
            print(f"Issue: {run.issue_ref}")
            print(f"Worktree: {run.worktree}")
            print(f"Run File: {run.run_file}")
            print(f"Claimed By: {_display_value(run.claimed_by)}")
            print(f"Claim ID: {run.claim_id}")
            if run.context_file is not None:
                print(f"Context File: {run.context_file}")
            return 0

        if args.command == "cleanup-issue":
            target_root, issue_id = _resolve_issue_target(root, args)
            issue_file = cleanup_issue(
                target_root,
                issue_id,
                destination=args.destination,
                note=args.note,
                remove_worktree=args.remove_worktree,
            )
            print(issue_file)
            return 0

        if args.command == "append-note":
            target_root, issue_id = _resolve_issue_target(root, args)
            notes = append_note(target_root, issue_id, section=args.section, note=args.note, phase=args.phase)
            print(notes)
            return 0

        if args.command == "set-phase":
            target_root, issue_id, phase = _resolve_phase_target(root, args)
            issue_file = set_phase(target_root, issue_id, phase, note=args.note)
            print(issue_file)
            return 0

        if args.command == "run-check":
            target_root, issue_id = _resolve_issue_target(root, args)
            record = run_check(target_root, issue_id, check=args.check)
            print(record)
            return 0

        if args.command == "list-issues":
            print(_format_issue_list(list_issues(root, state=args.state, repo_id=args.repo)))
            return 0

        if args.command == "show-issue":
            target_root, issue_id = _resolve_issue_target(root, args)
            print(_format_issue_detail(show_issue(target_root, issue_id), target_root))
            return 0

        if args.command == "show-run":
            target_root, issue_id = _resolve_issue_target(root, args)
            if args.handoff:
                print(render_handoff(target_root, issue_id), end="")
            elif args.trace:
                print(_format_timeline(issue_id, run_timeline(target_root, issue_id)))
            else:
                print(
                    _format_run_detail(
                        show_run(target_root, issue_id),
                        target_root,
                        include_commands=args.commands,
                    )
                )
            return 0

        if args.command == "handoff":
            target_root, issue_id = _resolve_issue_target(root, args)
            if args.output is not None:
                output = write_handoff(target_root, issue_id, output=Path(args.output))
                print(output)
            elif args.write:
                output = write_handoff(target_root, issue_id)
                print(output)
            else:
                print(render_handoff(target_root, issue_id), end="")
            return 0

        if args.command == "status":
            target_root, current = _status_context(root, args)
            status = workspace_status(target_root)
            if args.json:
                _print_json(_status_payload(status, target_root, current=current))
            else:
                print(_format_status(status, target_root, current=current))
            return 0

        if args.command == "doctor":
            report = run_doctor(root, repo_id=args.repo)
            if args.json:
                _print_json(_report_payload(report))
            else:
                print(_format_doctor_report(report))
            if report.error_count:
                return 1
            if args.strict and report.warning_count:
                return 1
            return 0

        if args.command == "verify-run":
            target_root, issue_id = _resolve_issue_target(root, args)
            report = verify_run(target_root, issue_id)
            if args.json:
                payload = _report_payload(report)
                payload["issue_id"] = issue_id
                _print_json(payload)
            else:
                print(_format_verify_report(issue_id, report))
            if report.error_count:
                return 1
            if args.strict and report.warning_count:
                return 1
            return 0

        if args.command == "export-run":
            target_root, issue_id = _resolve_issue_target(root, args)
            output_path = Path(args.output) if args.output is not None else None
            output = export_run(target_root, issue_id, output=output_path)
            print(output)
            return 0

        if args.command == "prepare-pr":
            target_root, issue_id = _resolve_issue_target(root, args)
            output_path = Path(args.output) if args.output is not None else None
            preview = prepare_pull_request(
                target_root,
                issue_id,
                branch=args.branch,
                title=args.title,
                output=output_path,
            )
            print(preview.path)
            return 0

        if args.command == "publish-pr":
            target_root, issue_id = _resolve_issue_target(root, args)
            published = publish_pull_request(target_root, issue_id, branch=args.branch, title=args.title)
            print(published.url)
            return 0
    except CheckFailedError as exc:
        print(exc, file=sys.stderr)
        return exc.exit_code
    except (GoShipitError, OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    parser.error(f"Unhandled command: {args.command}")
    return 2
