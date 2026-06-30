from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from go_ship_it.state import add_issue, ensure_layout, register_repo


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    root = Path(args.root).resolve()

    if args.command == "init":
        ensure_layout(root)
        print(f"Initialized GoShipit state at {root}")
        return 0

    if args.command == "register-repo":
        repo_file = register_repo(
            root,
            repo_id=args.repo_id,
            path=Path(args.path).resolve(),
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

    parser.error(f"Unhandled command: {args.command}")
    return 2
