from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("flag", ["--setup-command", "--test-command"])
def test_parser_rejects_empty_required_commands(flag):
    harness = load_harness()
    argv = [
        "--target-id",
        "sample",
        "--target-path",
        "/tmp/sample",
        "--setup-command",
        "python -c 'print(\"setup\")'",
        "--test-command",
        "python -c 'print(\"test\")'",
    ]
    argv[argv.index(flag) + 1] = "   "

    with pytest.raises(SystemExit):
        harness.parse_args(argv)


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


def test_report_writer_quotes_commands_and_includes_output(tmp_path):
    harness = load_harness()
    paths = harness.RunPaths.from_root(tmp_path, "sample")
    records = [
        harness.CommandRecord(
            step="register target",
            command=["go-ship-it", "register-repo", "--setup-command", "env -u VIRTUAL_ENV uv sync --extra dev"],
            cwd=str(ROOT),
            exit_code=2,
            stdout="partial stdout",
            stderr="argument error",
        )
    ]

    harness.write_report(
        paths=paths,
        target_id="sample",
        source_target=Path("/tmp/sample"),
        issue_id="issue-001",
        worktree="",
        records=records,
        result="failure",
        notes=["register target failed with exit code 2"],
    )

    text = paths.report.read_text()
    assert "`go-ship-it register-repo --setup-command 'env -u VIRTUAL_ENV uv sync --extra dev'`" in text
    assert "partial stdout" in text
    assert "argument error" in text


def test_report_writer_includes_run_metadata_final_state_and_export(tmp_path):
    harness = load_harness()
    paths = harness.RunPaths.from_root(tmp_path, "sample")
    exported_run = tmp_path / "exported-run.md"

    harness.write_report(
        paths=paths,
        target_id="sample",
        source_target=Path("/tmp/sample"),
        issue_id="issue-001",
        worktree="worktrees/sample/issue-001",
        records=[],
        result="success",
        notes=[],
        started_at="2026-06-30T00:00:00+00:00",
        finished_at="2026-06-30T00:00:01+00:00",
        final_state="No active issues.",
        exported_run=exported_run,
    )

    text = paths.report.read_text()
    assert "- Started at: `2026-06-30T00:00:00+00:00`" in text
    assert "- Finished at: `2026-06-30T00:00:01+00:00`" in text
    assert "## Final State" in text
    assert "No active issues." in text
    assert "## Exported Issue" in text
    assert f"- Path: `{exported_run}`" in text


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


def test_dev_parawave_wrapper_is_explicit_about_target_values():
    wrapper = ROOT / "scripts" / "dev" / "run-parawave-e2e.sh"
    text = wrapper.read_text()

    assert "run-target-e2e.py" in text
    assert "--target-id parawave" in text
    assert '--target-path "$ROOT/../parawave"' in text
    assert "uv sync --extra dev" in text
    assert "uv run --extra dev pytest -q" in text


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
