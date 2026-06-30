#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import re
import shlex
import shutil
import subprocess
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


@dataclasses.dataclass(frozen=True)
class CommandRecord:
    step: str
    command: list[str]
    cwd: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def command_text(self) -> str:
        return shlex.join(self.command)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a disposable GoShipit e2e flow against an explicit target repo clone.")
    parser.add_argument("--target-id", required=True, help="GoShipit target id to register for this run.")
    parser.add_argument("--target-path", required=True, help="Path to the source target repo to clone.")
    parser.add_argument("--setup-command", required=True, type=non_empty_command, help="Setup command to register for the target clone.")
    parser.add_argument("--test-command", required=True, type=non_empty_command, help="Test command to register for the target clone.")
    parser.add_argument("--default-branch", default="main", help="Default branch for generated worktrees.")
    parser.add_argument("--run-root", help="Optional run root. Defaults to a temp directory.")
    parser.add_argument("--cleanup-worktree", action="store_true", help="Run GoShipit cleanup at the end.")
    parser.add_argument("--remove-run-root", action="store_true", help="Delete the temp run root after a successful run.")
    return parser.parse_args(argv)


def non_empty_command(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("command must not be empty")
    return value


def validate_target_id(target_id: str) -> None:
    if not TARGET_ID_RE.match(target_id):
        raise ValueError("target id must use only letters, numbers, dot, underscore, or dash, and cannot contain path separators")


def make_run_root() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(tempfile.mkdtemp(prefix=f"go-ship-it-target-e2e-{timestamp}-"))


def checked(records: list[CommandRecord], step: str, command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    records.append(
        CommandRecord(
            step=step,
            command=command,
            cwd=str(cwd),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{step} failed with exit code {completed.returncode}")
    return completed


def go_ship_it_argv(paths: RunPaths, *args: str) -> list[str]:
    return ["uv", "run", "go-ship-it", "--root", str(paths.state_root), *args]


def write_report(
    *,
    paths: RunPaths,
    target_id: str,
    source_target: Path,
    issue_id: str,
    worktree: str,
    records: list[CommandRecord],
    result: str,
    notes: list[str],
    started_at: str | None = None,
    finished_at: str | None = None,
    final_state: str | None = None,
    exported_run: Path | None = None,
) -> None:
    lines = [
        "# GoShipit Target E2E Report",
        "",
        f"- Target id: `{target_id}`",
        f"- Source target: `{source_target}`",
        f"- Run root: `{paths.run_root}`",
        f"- State root: `{paths.state_root}`",
        f"- Target clone: `{paths.target_clone}`",
        f"- Issue id: `{issue_id}`",
        f"- Worktree: `{worktree}`",
        f"- Started at: `{started_at or 'unknown'}`",
        f"- Finished at: `{finished_at or 'unknown'}`",
        f"- Result: `{result}`",
        "",
        "## Commands",
        "",
        "| Step | Command | Cwd | Exit |",
        "| --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(f"| {record.step} | `{record.command_text}` | `{record.cwd}` | {record.exit_code} |")
    if records:
        lines.extend(["", "## Command Output", ""])
        for record in records:
            lines.extend(
                [
                    f"### {record.step}",
                    "",
                    "Stdout:",
                    "",
                    "```text",
                    record.stdout.rstrip(),
                    "```",
                    "",
                    "Stderr:",
                    "",
                    "```text",
                    record.stderr.rstrip(),
                    "```",
                    "",
                ]
            )
    lines.extend(["", "## Final State", ""])
    if final_state:
        lines.extend(["```text", final_state.rstrip(), "```", ""])
    else:
        lines.extend(["No final state captured.", ""])
    lines.extend(["## Exported Issue", ""])
    if exported_run is not None:
        lines.append(f"- Path: `{exported_run}`")
        lines.append(f"- Exists: `{'yes' if exported_run.exists() else 'no'}`")
    else:
        lines.append("No exported issue path captured.")
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in notes)
    lines.append("")
    paths.report.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    validate_target_id(args.target_id)
    source_target = Path(args.target_path).resolve()
    if not source_target.exists():
        raise SystemExit(f"target path does not exist: {source_target}")
    if not (source_target / ".git").exists():
        raise SystemExit(f"target path is not a git repo: {source_target}")

    run_root = Path(args.run_root).resolve() if args.run_root else make_run_root()
    paths = RunPaths.from_root(run_root, args.target_id)
    paths.run_root.mkdir(parents=True, exist_ok=True)
    paths.state_root.mkdir(parents=True, exist_ok=True)
    paths.target_clone.parent.mkdir(parents=True, exist_ok=True)

    records: list[CommandRecord] = []
    issue_id = "issue-001"
    worktree = ""
    result = "failure"
    started_at = datetime.now(timezone.utc).isoformat()
    final_state = ""
    exported_run = paths.run_root / "exported-run.md"
    notes: list[str] = []

    try:
        checked(records, "clone target", ["git", "clone", str(source_target), str(paths.target_clone)], cwd=run_root)
        checked(
            records,
            "register target",
            go_ship_it_argv(
                paths,
                "register-repo",
                args.target_id,
                str(paths.target_clone),
                "--default-branch",
                args.default_branch,
                "--setup-command",
                args.setup_command,
                "--test-command",
                args.test_command,
            ),
            cwd=ROOT,
        )
        add = checked(
            records,
            "add issue",
            go_ship_it_argv(
                paths,
                "add-issue",
                "--repo",
                args.target_id,
                "--title",
                "Run disposable target e2e",
                "--problem",
                "Exercise GoShipit lifecycle against an isolated target clone.",
                "--context",
                "Created by scripts/run-target-e2e.py.",
                "--acceptance",
                "Configured setup and test checks pass.",
            ),
            cwd=ROOT,
        )
        issue_path = Path(add.stdout.strip())
        if issue_path.name:
            issue_id = issue_path.stem
        start = checked(records, "start issue", go_ship_it_argv(paths, "start-issue", issue_id, "--claimed-by", "target-e2e"), cwd=ROOT)
        worktree = start.stdout.strip()
        worktree_path = Path(worktree)
        if not worktree_path.is_absolute():
            worktree_path = paths.state_root / worktree_path
        marker_dir = worktree_path / ".go-ship-it-e2e"
        marker_dir.mkdir(parents=True, exist_ok=True)
        (marker_dir / f"{issue_id}.txt").write_text("GoShipit disposable target e2e marker.\n")
        checked(records, "git add marker", ["git", "add", ".go-ship-it-e2e"], cwd=worktree_path)
        checked(
            records,
            "git commit marker",
            [
                "git",
                "-c",
                "user.name=GoShipit E2E",
                "-c",
                "user.email=go-ship-it-e2e@example.test",
                "commit",
                "-m",
                "test: add go ship it e2e marker",
            ],
            cwd=worktree_path,
        )
        checked(
            records,
            "note investigation",
            go_ship_it_argv(
                paths,
                "append-note",
                issue_id,
                "--section",
                "Investigation",
                "--phase",
                "investigate",
                "--note",
                "Disposable target clone and worktree were created successfully.",
            ),
            cwd=ROOT,
        )
        checked(
            records,
            "note proposal",
            go_ship_it_argv(
                paths,
                "append-note",
                issue_id,
                "--section",
                "Proposal",
                "--phase",
                "propose",
                "--note",
                "Use a harmless marker file to prove implementation and check execution.",
            ),
            cwd=ROOT,
        )
        checked(records, "run setup check", go_ship_it_argv(paths, "run-check", issue_id, "--check", "setup"), cwd=ROOT)
        checked(records, "run test check", go_ship_it_argv(paths, "run-check", issue_id, "--check", "test"), cwd=ROOT)
        checked(
            records,
            "note review",
            go_ship_it_argv(
                paths,
                "append-note",
                issue_id,
                "--section",
                "Review",
                "--phase",
                "test",
                "--note",
                "Configured setup and test checks passed in the disposable target clone.",
            ),
            cwd=ROOT,
        )
        checked(
            records,
            "export run",
            go_ship_it_argv(paths, "export-run", issue_id, "--output", str(exported_run)),
            cwd=ROOT,
        )
        if args.cleanup_worktree:
            checked(
                records,
                "cleanup issue",
                go_ship_it_argv(
                    paths,
                    "cleanup-issue",
                    issue_id,
                    "--destination",
                    "archive",
                    "--note",
                    "Disposable target e2e complete.",
                    "--remove-worktree",
                ),
                cwd=ROOT,
            )
        status = checked(records, "status", go_ship_it_argv(paths, "status"), cwd=ROOT)
        doctor = checked(records, "doctor", go_ship_it_argv(paths, "doctor"), cwd=ROOT)
        final_state = "\n\n".join(part for part in (status.stdout.rstrip(), doctor.stdout.rstrip()) if part)
        result = "success"
        notes.append("Preserved run root for inspection." if not args.remove_run_root else "Removed run root after success.")
        return_code = 0
    except Exception as exc:
        notes.append(str(exc))
        return_code = 1
    finally:
        write_report(
            paths=paths,
            target_id=args.target_id,
            source_target=source_target,
            issue_id=issue_id,
            worktree=worktree,
            records=records,
            result=result,
            notes=notes,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            final_state=final_state,
            exported_run=exported_run,
        )
        print(f"Report: {paths.report}")
        if args.remove_run_root and result == "success":
            shutil.rmtree(paths.run_root)
            print("Removed run root after successful run.")
        else:
            print(f"Preserved run root: {paths.run_root}")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
