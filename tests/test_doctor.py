from pathlib import Path
import subprocess

from go_ship_it.doctor import run_doctor
from go_ship_it.state import register_repo


def test_doctor_passes_minimal_valid_workspace(tmp_path):
    root = _root_with_repo(tmp_path)
    report = run_doctor(root)

    assert report.error_count == 0
    assert any(item.code == "layout.exists" for item in report.ok)


def test_doctor_errors_when_registered_repo_path_is_missing(tmp_path):
    register_repo(
        tmp_path,
        repo_id="missing",
        path=tmp_path / "does-not-exist",
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )

    report = run_doctor(tmp_path)

    assert report.error_count == 1
    assert report.errors[0].code == "repo.path_missing"


def test_doctor_warns_for_missing_optional_commands(tmp_path):
    root = _root_with_repo(tmp_path, setup_command=None, test_command=None, lint_command=None)

    report = run_doctor(root)

    assert report.error_count == 0
    assert {item.code for item in report.warnings} >= {
        "repo.setup_command_missing",
        "repo.test_command_missing",
        "repo.lint_command_missing",
    }


def _root_with_repo(
    tmp_path: Path,
    *,
    setup_command: str | None = "python -c 'print(\"setup\")'",
    test_command: str | None = "python -c 'print(\"test\")'",
    lint_command: str | None = "python -c 'print(\"lint\")'",
) -> Path:
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=setup_command,
        test_command=test_command,
        lint_command=lint_command,
    )
    return tmp_path


def _create_git_repo(path: Path) -> Path:
    path.mkdir()
    _run_git(path, "init", "-b", "main")
    _run_git(path, "config", "user.email", "test@example.com")
    _run_git(path, "config", "user.name", "Test User")
    (path / "README.md").write_text("# Sample\n")
    _run_git(path, "add", "README.md")
    _run_git(path, "commit", "-m", "initial commit")
    return path


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True)
