#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


@dataclasses.dataclass(frozen=True)
class RunPaths:
    run_root: Path
    state_root: Path
    target_clone: Path
    report: Path

    @classmethod
    def from_root(cls, run_root: Path, target_id: str) -> "RunPaths":
        return cls(
            run_root=run_root,
            state_root=run_root / "go-ship-it-state",
            target_clone=run_root / "target" / target_id,
            report=run_root / "report.md",
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a disposable GoShipit e2e flow against an explicit target repo clone.")
    parser.add_argument("--target-id", required=True, help="GoShipit target id to register for this run.")
    parser.add_argument("--target-path", required=True, help="Path to the source target repo to clone.")
    parser.add_argument("--setup-command", required=True, help="Setup command to register for the target clone.")
    parser.add_argument("--test-command", required=True, help="Test command to register for the target clone.")
    parser.add_argument("--default-branch", default="main", help="Default branch for generated worktrees.")
    parser.add_argument("--run-root", help="Optional run root. Defaults to a temp directory.")
    parser.add_argument("--cleanup-worktree", action="store_true", help="Run GoShipit cleanup at the end.")
    parser.add_argument("--remove-run-root", action="store_true", help="Delete the temp run root after a successful run.")
    return parser.parse_args(argv)


def validate_target_id(target_id: str) -> None:
    if not TARGET_ID_RE.match(target_id):
        raise ValueError("target id must use only letters, numbers, dot, underscore, or dash, and cannot contain path separators")


def make_run_root() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(tempfile.mkdtemp(prefix=f"go-ship-it-target-e2e-{timestamp}-"))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    validate_target_id(args.target_id)
    run_root = Path(args.run_root).resolve() if args.run_root else make_run_root()
    paths = RunPaths.from_root(run_root, args.target_id)
    paths.run_root.mkdir(parents=True, exist_ok=True)
    print(f"Run root: {paths.run_root}")
    print(f"Report: {paths.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
