from pathlib import Path

from go_ship_it.frontmatter import parse_frontmatter
from go_ship_it.state import add_issue, ensure_layout, register_repo


def test_ensure_layout_creates_state_directories(tmp_path):
    ensure_layout(tmp_path)

    assert (tmp_path / "state" / "repos").is_dir()
    assert (tmp_path / "state" / "issues" / "todo").is_dir()
    assert (tmp_path / "state" / "issues" / "execution").is_dir()
    assert (tmp_path / "state" / "issues" / "archive").is_dir()
    assert (tmp_path / "state" / "runs").is_dir()
    assert (tmp_path / "worktrees").is_dir()


def test_register_repo_writes_simple_registry_file(tmp_path):
    target = tmp_path / "target"
    target.mkdir()

    repo_file = register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command="uv sync",
        test_command="uv run pytest",
        lint_command=None,
    )

    assert repo_file == tmp_path / "state" / "repos" / "sample.yaml"
    assert repo_file.read_text() == (
        "id: sample\n"
        f"path: {target}\n"
        "default_branch: main\n"
        "worktree_root: worktrees/sample\n"
        "setup_command: uv sync\n"
        "test_command: uv run pytest\n"
        "lint_command: null\n"
    )


def test_add_issue_creates_todo_markdown(tmp_path):
    ensure_layout(tmp_path)

    issue_file = add_issue(
        tmp_path,
        repo_id="parawave",
        title="Add resume example coverage",
        problem="The README mentions resume behavior but examples do not cover it.",
        context="Use the sibling parawave repo.",
        acceptance_criteria=["A focused test exists.", "The test passes."],
    )

    assert issue_file == tmp_path / "state" / "issues" / "todo" / "issue-001.md"
    metadata, body = parse_frontmatter(issue_file.read_text())
    assert metadata["id"] == "issue-001"
    assert metadata["repo"] == "parawave"
    assert metadata["status"] == "todo"
    assert metadata["phase"] == "setup"
    assert isinstance(metadata["created_at"], str)
    assert metadata["worktree"] is None
    assert metadata["branch"] is None
    assert "## Problem" in body
    assert "- A focused test exists." in body
