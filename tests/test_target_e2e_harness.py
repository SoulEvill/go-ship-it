from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts" / "run-target-e2e.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("run_target_e2e", HARNESS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parser_requires_explicit_target_arguments():
    harness = load_harness()

    args = harness.parse_args(
        [
            "--target-id",
            "sample",
            "--target-path",
            "/tmp/sample",
            "--setup-command",
            "python -c 'print(\"setup\")'",
            "--test-command",
            "python -c 'print(\"test\")'",
        ]
    )

    assert args.target_id == "sample"
    assert args.target_path == "/tmp/sample"
    assert args.setup_command == "python -c 'print(\"setup\")'"
    assert args.test_command == "python -c 'print(\"test\")'"
    assert args.default_branch == "main"


def test_run_paths_are_target_agnostic(tmp_path):
    harness = load_harness()

    paths = harness.RunPaths.from_root(tmp_path, "sample")

    assert paths.run_root == tmp_path
    assert paths.state_root == tmp_path / "go-ship-it-state"
    assert paths.target_clone == tmp_path / "target" / "sample"
    assert paths.report == tmp_path / "report.md"


def test_report_writer_includes_command_records(tmp_path):
    harness = load_harness()
    paths = harness.RunPaths.from_root(tmp_path, "sample")
    records = [
        harness.CommandRecord(
            step="status",
            command=["uv", "run", "go-ship-it", "status"],
            cwd=str(ROOT),
            exit_code=0,
            stdout="ok",
            stderr="",
        )
    ]

    harness.write_report(
        paths=paths,
        target_id="sample",
        source_target=Path("/tmp/sample"),
        issue_id="issue-001",
        worktree="worktrees/sample/issue-001",
        records=records,
        result="success",
        notes=["Preserved run root for inspection."],
    )

    text = paths.report.read_text()
    assert "# GoShipit Target E2E Report" in text
    assert "| status | `uv run go-ship-it status` |" in text
    assert "Preserved run root for inspection." in text


def test_harness_runs_against_fake_target_repo(tmp_path):
    harness = load_harness()
    source = _create_fake_target_repo(tmp_path / "source-target")
    run_root = tmp_path / "run"

    exit_code = harness.main(
        [
            "--target-id",
            "fake",
            "--target-path",
            str(source),
            "--setup-command",
            "python -c 'print(\"setup ok\")'",
            "--test-command",
            "python -c 'print(\"test ok\")'",
            "--run-root",
            str(run_root),
            "--cleanup-worktree",
        ]
    )

    assert exit_code == 0
    report = (run_root / "report.md").read_text()
    assert "Result: `success`" in report
    assert "add issue" in report
    assert "start issue" in report
    assert "run test check" in report
    assert "cleanup issue" in report


def _create_fake_target_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / "pyproject.toml").write_text(
        "[project]\n"
        'name = "fake-target"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.11"\n'
    )
    (path / "README.md").write_text("# Fake Target\n")
    _git(path, "init", "-b", "main")
    _git(path, "add", ".")
    _git(
        path,
        "-c",
        "user.name=GoShipit Test",
        "-c",
        "user.email=go-ship-it@example.test",
        "commit",
        "-m",
        "initial fake target",
    )
    return path


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, text=True, capture_output=True)
