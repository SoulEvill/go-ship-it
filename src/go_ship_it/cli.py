from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from go_ship_it.state import (
    GoShipitError,
    add_issue,
    append_note,
    cleanup_issue,
    ensure_layout,
    register_repo,
    set_phase,
    start_issue,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="go-ship-it",
        description="GoShipit local issue lifecycle manager.",
    )
    parser.add_argument("--root", default=".", help="GoShipit repo root. Defaults to current directory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create the local GoShipit state folders.")

    register = subparsers.add_parser("register-repo", help="Register a target repository.")
    register.add_argument("repo_id")
    register.add_argument("path")
    register.add_argument("--default-branch", default="main")
    register.add_argument("--setup-command", default=None)
    register.add_argument("--test-command", default=None)
    register.add_argument("--lint-command", default=None)

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
    cleanup.add_argument("issue_id")
    cleanup.add_argument("--destination", choices=["todo", "archive"], required=True)
    cleanup.add_argument("--note", required=True)
    cleanup.add_argument(
        "--remove-worktree",
        action="store_true",
        help="Remove the managed worktree. Required when returning to todo.",
    )

    note = subparsers.add_parser("append-note", help="Append a journal note for an active issue.")
    note.add_argument("issue_id")
    note.add_argument("--section", required=True)
    note.add_argument("--note", required=True)
    note.add_argument("--phase", default=None)

    phase = subparsers.add_parser("set-phase", help="Set the current workflow phase for an active issue.")
    phase.add_argument("issue_id")
    phase.add_argument("phase")
    phase.add_argument("--note", required=True)

    check = subparsers.add_parser("run-check", help="Run a registered repo check and record evidence.")
    check.add_argument("issue_id")
    check.add_argument("--check", choices=["setup", "test", "lint"], required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    root = Path(args.root).resolve()

    try:
        if args.command == "init":
            ensure_layout(root)
            print(f"Initialized GoShipit state at {root}")
            return 0

        if args.command == "register-repo":
            repo_file = register_repo(
                root,
                repo_id=args.repo_id,
                path=Path(args.path),
                default_branch=args.default_branch,
                setup_command=args.setup_command,
                test_command=args.test_command,
                lint_command=args.lint_command,
            )
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
            print(run.worktree)
            return 0

        if args.command == "cleanup-issue":
            issue_file = cleanup_issue(
                root,
                args.issue_id,
                destination=args.destination,
                note=args.note,
                remove_worktree=args.remove_worktree,
            )
            print(issue_file)
            return 0

        if args.command == "append-note":
            journal = append_note(root, args.issue_id, section=args.section, note=args.note, phase=args.phase)
            print(journal)
            return 0

        if args.command == "set-phase":
            issue_file = set_phase(root, args.issue_id, args.phase, note=args.note)
            print(issue_file)
            return 0
    except (GoShipitError, OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    parser.error(f"Unhandled command: {args.command}")
    return 2
