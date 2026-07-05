from pathlib import Path
import subprocess

import yaml
import pytest

from go_ship_it.frontmatter import parse_frontmatter
from go_ship_it.state import (
    GoShipitError,
    add_issue,
    cleanup_issue,
    ensure_layout,
    next_issue_id,
    read_repo_config,
    register_feedback_repo,
    register_repo,
    render_handoff,
    resolve_current_run,
    start_issue,
    write_handoff,
)


def test_ensure_layout_creates_state_directories(tmp_path):
    ensure_layout(tmp_path)

    assert (tmp_path / "state" / "repos").is_dir()
    assert (tmp_path / "worktrees").is_dir()
    assert not (tmp_path / "state" / "issues").exists()
    assert not (tmp_path / "state" / "runs").exists()


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

    assert repo_file == tmp_path / "state" / "repos" / "sample" / "repo.yaml"
    assert repo_file.read_text() == (
        "id: sample\n"
        f"path: {target}\n"
        f"source: {target}\n"
        "source_type: local\n"
        "default_branch: main\n"
        "worktree_root: worktrees/sample\n"
        "context_file: state/repos/sample/context.md\n"
        "setup_command: uv sync\n"
        "test_command: uv run pytest\n"
        "lint_command: null\n"
        "pull_request:\n"
        "  provider: github\n"
        "  remote: origin\n"
        "  auto_publish: false\n"
    )
    context_file = tmp_path / "state" / "repos" / "sample" / "context.md"
    assert context_file.exists()
    assert context_file.read_text().startswith("# sample Context\n")
    assert (tmp_path / "state" / "repos" / "sample" / "issues" / "todo").is_dir()
    assert (tmp_path / "state" / "repos" / "sample" / "issues" / "execution").is_dir()
    assert (tmp_path / "state" / "repos" / "sample" / "issues" / "archive").is_dir()
    assert not (tmp_path / "state" / "repos" / "sample" / "runs").exists()


def test_register_repo_clones_git_url_into_repo_worktree_source(tmp_path):
    source = _create_git_repo(tmp_path / "source")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "--bare", str(source), str(remote)], check=True, capture_output=True, text=True)
    control = tmp_path / "control"

    repo_file = register_repo(
        control,
        repo_id="sample",
        path=remote.as_uri(),
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )

    data = yaml.safe_load(repo_file.read_text())
    assert data["path"] == "worktrees/sample/_source"
    assert data["source"] == remote.as_uri()
    assert data["source_type"] == "git_url"
    assert (control / "worktrees" / "sample" / "_source" / "README.md").exists()
    assert _git_output(control / "worktrees" / "sample" / "_source", "config", "--get", "remote.origin.url").strip() == remote.as_uri()


def test_start_issue_uses_managed_source_clone_for_git_url_repo(tmp_path):
    source = _create_git_repo(tmp_path / "source")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "--bare", str(source), str(remote)], check=True, capture_output=True, text=True)
    control = tmp_path / "control"
    register_repo(
        control,
        repo_id="sample",
        path=remote.as_uri(),
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(control)

    run = start_issue(control, "sample/issue-001", claimed_by="test-thread")

    assert run.worktree == control / "worktrees" / "sample" / "issue-001"
    assert (run.worktree / "README.md").exists()
    assert (control / "worktrees" / "sample" / "_source").exists()


def test_register_feedback_repo_writes_product_context(tmp_path):
    target = tmp_path / "go-ship-it"
    target.mkdir()

    repo_file = register_feedback_repo(
        tmp_path,
        path=target,
        test_command="uv run pytest -q",
    )

    assert repo_file == tmp_path / "state" / "repos" / "go-ship-it" / "repo.yaml"
    text = repo_file.read_text()
    assert "id: go-ship-it\n" in text
    assert f"path: {target}\n" in text
    assert "test_command: uv run pytest -q\n" in text
    context = (tmp_path / "state" / "repos" / "go-ship-it" / "context.md").read_text()
    assert "Use this registered repo for GoShipit product feedback" in context
    assert "Do not add a separate feedback, learning, or observation subsystem" in context


def test_read_repo_config_rejects_flat_registry_file(tmp_path):
    ensure_layout(tmp_path)
    flat_file = tmp_path / "state" / "repos" / "flat.yaml"
    flat_file.write_text(
        "id: flat\n"
        "path: ../flat\n"
        "default_branch: main\n"
        "worktree_root: worktrees/flat\n"
        "setup_command: null\n"
        "test_command: null\n"
        "lint_command: null\n"
    )

    with pytest.raises(FileNotFoundError, match="state/repos/flat/repo.yaml"):
        read_repo_config(tmp_path, "flat")


def test_add_issue_creates_todo_markdown(tmp_path):
    register_repo(
        tmp_path,
        repo_id="parawave",
        path=tmp_path / "parawave",
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )

    issue_file = add_issue(
        tmp_path,
        repo_id="parawave",
        title="Add resume example coverage",
        problem="The README mentions resume behavior but examples do not cover it.",
        context="Use the sibling parawave repo.",
        acceptance_criteria=["A focused test exists.", "The test passes."],
    )

    assert issue_file == tmp_path / "state" / "repos" / "parawave" / "issues" / "todo" / "issue-001" / "issue.md"
    metadata, body = parse_frontmatter(issue_file.read_text())
    assert metadata["id"] == "issue-001"
    assert "repo" not in metadata
    assert "status" not in metadata
    assert metadata["phase"] == "setup"
    assert isinstance(metadata["created_at"], str)
    assert metadata["worktree"] is None
    assert metadata["branch"] is None
    assert "## Problem" in body
    assert "- A focused test exists." in body


def test_add_issue_rejects_unregistered_repo(tmp_path):
    ensure_layout(tmp_path)

    with pytest.raises(FileNotFoundError, match="Repo registry file not found"):
        add_issue(
            tmp_path,
            repo_id="typo",
            title="Unknown repo issue",
            problem="This repo id is not registered.",
            context="",
            acceptance_criteria=["No issue should be created."],
        )

    assert not list((tmp_path / "state" / "repos").glob("*/issues/todo/issue-*/issue.md"))


def test_explicit_issue_refs_require_exactly_repo_and_issue(tmp_path):
    ensure_layout(tmp_path)

    with pytest.raises(ValueError, match="<repo>/<issue-id>"):
        start_issue(tmp_path, "issue-001")
    with pytest.raises(ValueError, match="<repo>/<issue-id>"):
        start_issue(tmp_path, "sample/team/issue-001")


def test_next_issue_id_counts_preserved_managed_worktrees(tmp_path):
    register_repo(
        tmp_path,
        repo_id="sample",
        path=tmp_path / "sample",
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    (tmp_path / "worktrees" / "sample" / "issue-001").mkdir(parents=True)

    assert next_issue_id(tmp_path, "sample") == "issue-002"


def test_next_issue_id_is_repo_local(tmp_path):
    for repo_id in ("alpha", "beta"):
        register_repo(
            tmp_path,
            repo_id=repo_id,
            path=tmp_path / repo_id,
            default_branch="main",
            setup_command=None,
            test_command=None,
            lint_command=None,
        )

    first = add_issue(
        tmp_path,
        repo_id="alpha",
        title="Alpha issue",
        problem="Alpha problem.",
        context="",
        acceptance_criteria=["Alpha done."],
    )
    second = add_issue(
        tmp_path,
        repo_id="beta",
        title="Beta issue",
        problem="Beta problem.",
        context="",
        acceptance_criteria=["Beta done."],
    )

    assert first == tmp_path / "state" / "repos" / "alpha" / "issues" / "todo" / "issue-001" / "issue.md"
    assert second == tmp_path / "state" / "repos" / "beta" / "issues" / "todo" / "issue-001" / "issue.md"
    assert next_issue_id(tmp_path, "alpha") == "issue-002"
    assert next_issue_id(tmp_path, "beta") == "issue-002"


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True)


def _git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True, text=True)
    return result.stdout


def _create_git_repo(path: Path) -> Path:
    path.mkdir()
    _run_git(path, "init", "-b", "main")
    _run_git(path, "config", "user.email", "test@example.com")
    _run_git(path, "config", "user.name", "Test User")
    (path / "README.md").write_text("# Sample\n")
    _run_git(path, "add", "README.md")
    _run_git(path, "commit", "-m", "initial commit")
    return path


def _add_sample_issue(root: Path, *, title: str = "Change README") -> Path:
    return add_issue(
        root,
        repo_id="sample",
        title=title,
        problem="README needs another line.",
        context="Use the test repo.",
        acceptance_criteria=["README changes."],
    )


def test_start_issue_claims_issue_and_creates_worktree(tmp_path):
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command="pytest",
        lint_command=None,
    )
    _add_sample_issue(tmp_path)

    run = start_issue(tmp_path, "sample/issue-001", claimed_by="test-thread")

    assert run.issue_id == "issue-001"
    assert run.repo_id == "sample"
    assert run.issue_ref == "sample/issue-001"
    assert run.branch == "go-ship-it/issue-001"
    assert run.worktree == tmp_path / "worktrees" / "sample" / "issue-001"
    assert run.claimed_by == "test-thread"
    assert run.claim_id.startswith("claim-issue-001-")
    assert run.already_active is False
    assert run.context_file == run.worktree / ".go-ship-it" / "context.yaml"
    assert (run.worktree / "README.md").exists()
    assert not (tmp_path / "state" / "repos" / "sample" / "issues" / "todo" / "issue-001").exists()
    execution_file = tmp_path / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "issue.md"
    metadata, _body = parse_frontmatter(execution_file.read_text())
    assert "status" not in metadata
    assert "repo" not in metadata
    assert metadata["phase"] == "investigate"
    assert metadata["branch"] == "go-ship-it/issue-001"
    assert metadata["worktree"] == "worktrees/sample/issue-001"
    assert (tmp_path / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "claim.lock").is_dir()
    run_file = tmp_path / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "run.yaml"
    assert run_file.exists()
    assert "claimed_by: test-thread\n" in run_file.read_text()
    assert f"claim_id: {run.claim_id}\n" in run_file.read_text()
    context = yaml.safe_load((run.worktree / ".go-ship-it" / "context.yaml").read_text())
    assert context["issue_id"] == "issue-001"
    assert context["repo_id"] == "sample"
    assert context["control_root"] == str(tmp_path)
    assert context["run_dir"] == "state/repos/sample/issues/execution/issue-001"
    assert context["issue_file"] == "state/repos/sample/issues/execution/issue-001/issue.md"
    assert context["worktree"] == "worktrees/sample/issue-001"
    assert context["branch"] == "go-ship-it/issue-001"
    assert context["claimed_by"] == "test-thread"
    assert context["claim_id"] == run.claim_id
    assert ".go-ship-it/" in _git_output(run.worktree, "status", "--ignored", "--short")


def test_resolve_current_run_uses_worktree_context_and_run_claim(tmp_path):
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path)
    run = start_issue(tmp_path, "sample/issue-001", claimed_by="test-thread")
    nested = run.worktree / "src" / "package"
    nested.mkdir(parents=True)

    current = resolve_current_run(nested)

    assert current.issue_id == "issue-001"
    assert current.repo_id == "sample"
    assert current.control_root == tmp_path.resolve()
    assert current.worktree == run.worktree.resolve()
    assert current.run_file == (
        tmp_path / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "run.yaml"
    ).resolve()
    assert current.context_file == (run.worktree / ".go-ship-it" / "context.yaml").resolve()
    assert current.claim_id == run.claim_id
    assert current.claimed_by == "test-thread"


def test_resolve_current_run_rejects_claim_mismatch(tmp_path):
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path)
    run = start_issue(tmp_path, "sample/issue-001", claimed_by="test-thread")
    context_file = run.worktree / ".go-ship-it" / "context.yaml"
    context = yaml.safe_load(context_file.read_text())
    context["claim_id"] = "claim-issue-001-wrong"
    context_file.write_text(yaml.safe_dump(context, sort_keys=False))

    with pytest.raises(GoShipitError, match="claim mismatch"):
        resolve_current_run(run.worktree)


def test_start_issue_auto_claim_is_stable_for_same_control_root_and_cwd(tmp_path, monkeypatch):
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path)
    monkeypatch.setenv("GO_SHIP_IT_AGENT", "codex")
    monkeypatch.setenv("USER", "tester")
    monkeypatch.chdir(tmp_path)

    run = start_issue(tmp_path, "sample/issue-001")

    assert run.claimed_by is not None
    assert run.claimed_by.startswith("codex:tester@")
    assert "claimed_by: " in run.run_file.read_text()


def test_start_issue_reuses_duplicate_active_run(tmp_path):
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path)
    first = start_issue(tmp_path, "sample/issue-001", claimed_by="first-thread")

    second = start_issue(tmp_path, "sample/issue-001", claimed_by="second-thread")

    assert second.already_active is True
    assert second.issue_id == first.issue_id
    assert second.worktree == first.worktree
    assert second.claim_id == first.claim_id
    assert second.claimed_by == "first-thread"
    assert "second-thread" not in second.run_file.read_text()


def test_start_issue_supports_two_active_issues_for_same_repo(tmp_path):
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path, title="First")
    _add_sample_issue(tmp_path, title="Second")

    first = start_issue(tmp_path, "sample/issue-001", claimed_by="first-thread")
    second = start_issue(tmp_path, "sample/issue-002", claimed_by="second-thread")

    assert first.worktree == tmp_path / "worktrees" / "sample" / "issue-001"
    assert second.worktree == tmp_path / "worktrees" / "sample" / "issue-002"
    assert first.worktree.exists()
    assert second.worktree.exists()


def test_start_issue_leaves_todo_unmoved_when_target_repo_is_missing(tmp_path):
    register_repo(
        tmp_path,
        repo_id="sample",
        path=tmp_path / "missing",
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path)

    with pytest.raises(FileNotFoundError):
        start_issue(tmp_path, "sample/issue-001", claimed_by="test-thread")

    assert (tmp_path / "state" / "repos" / "sample" / "issues" / "todo" / "issue-001" / "issue.md").exists()
    assert not (tmp_path / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001").exists()
    assert not (tmp_path / "worktrees" / "sample" / "issue-001").exists()


def _started_issue_root(tmp_path: Path) -> Path:
    target = _create_git_repo(tmp_path / "target")
    register_repo(
        tmp_path,
        repo_id="sample",
        path=target,
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )
    _add_sample_issue(tmp_path)
    start_issue(tmp_path, "sample/issue-001", claimed_by="test-thread")
    return tmp_path


def test_cleanup_return_to_todo_moves_issue_back_and_removes_active_worktree(tmp_path):
    root = _started_issue_root(tmp_path)

    active_worktree = root / "worktrees" / "sample" / "issue-001"
    assert active_worktree.exists()

    result = cleanup_issue(root, "sample/issue-001", destination="todo", note="Needs a clearer ask.", remove_worktree=True)

    assert result == root / "state" / "repos" / "sample" / "issues" / "todo" / "issue-001" / "issue.md"
    assert result.exists()
    assert not active_worktree.exists()
    assert not (root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001").exists()
    metadata, _body = parse_frontmatter(result.read_text())
    assert "status" not in metadata
    assert metadata["phase"] == "setup"
    assert metadata["worktree"] is None
    assert metadata["branch"] is None
    assert (root / "state" / "repos" / "sample" / "issues" / "todo" / "issue-001" / "run.yaml").exists()
    assert "cleanup_destination: todo\n" in (
        root / "state" / "repos" / "sample" / "issues" / "todo" / "issue-001" / "run.yaml"
    ).read_text()
    assert "Needs a clearer ask." in (
        root / "state" / "repos" / "sample" / "issues" / "todo" / "issue-001" / "notes.md"
    ).read_text()
    assert not (root / "state" / "repos" / "sample" / "issues" / "todo" / "issue-001" / "claim.lock").exists()
    assert "go-ship-it/issue-001" not in _git_output(root / "target", "branch", "--list", "go-ship-it/issue-001")


def test_cleanup_return_to_todo_requires_worktree_removal(tmp_path):
    root = _started_issue_root(tmp_path)

    with pytest.raises(ValueError, match="returning an issue to todo requires remove_worktree=True"):
        cleanup_issue(root, "sample/issue-001", destination="todo", note="Needs a clearer ask.", remove_worktree=False)

    assert (root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "issue.md").exists()
    assert (root / "worktrees" / "sample" / "issue-001").exists()
    assert (root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "claim.lock").exists()


def test_cleanup_archive_moves_issue_to_archive_and_preserves_worktree(tmp_path):
    root = _started_issue_root(tmp_path)
    active_worktree = root / "worktrees" / "sample" / "issue-001"

    result = cleanup_issue(root, "sample/issue-001", destination="archive", note="Closed after review.", remove_worktree=False)

    assert result == root / "state" / "repos" / "sample" / "issues" / "archive" / "issue-001" / "issue.md"
    assert result.exists()
    assert active_worktree.exists()
    assert not (root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001").exists()
    metadata, body = parse_frontmatter(result.read_text())
    assert "status" not in metadata
    assert metadata["phase"] == "cleanup"
    assert "Closed after review." in body
    assert not (root / "state" / "repos" / "sample" / "issues" / "archive" / "issue-001" / "claim.lock").exists()


def test_cleanup_archive_can_remove_managed_worktree(tmp_path):
    root = _started_issue_root(tmp_path)
    active_worktree = root / "worktrees" / "sample" / "issue-001"

    cleanup_issue(root, "sample/issue-001", destination="archive", note="Closed after review.", remove_worktree=True)

    assert not active_worktree.exists()


def test_render_handoff_includes_resume_context(tmp_path):
    root = _started_issue_root(tmp_path)

    text = render_handoff(root, "sample/issue-001")

    assert "# GoShipit Handoff: sample/issue-001" in text
    assert f"Control Root: `{root}`" in text
    assert "Repo: `sample`" in text
    assert "Status: `execution`" in text
    assert "Phase: `investigate`" in text
    assert "Claimed By: `test-thread`" in text
    assert "Claim ID: `claim-issue-001-" in text
    assert "Worktree: `worktrees/sample/issue-001`" in text
    assert "go-ship-it show-run sample/issue-001 --trace" in text
    assert "go-ship-it verify-run sample/issue-001" in text


def test_write_handoff_defaults_to_run_directory(tmp_path):
    root = _started_issue_root(tmp_path)

    path = write_handoff(root, "sample/issue-001")

    assert path == root / "state" / "repos" / "sample" / "issues" / "execution" / "issue-001" / "handoff.md"
    assert "# GoShipit Handoff: sample/issue-001" in path.read_text()
