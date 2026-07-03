from pathlib import Path
import subprocess


def test_generated_state_files_are_gitignored():
    root = Path(__file__).resolve().parents[1]

    assert (root / "state" / "repos" / ".gitkeep").exists()
    assert _is_ignored(root, "state/repos/example/repo.yaml")
    assert _is_ignored(root, "state/repos/example/context.md")
    assert not _is_ignored(root, "state/repos/example.yaml")
    assert _is_ignored(root, "state/issues/todo/issue-999.md")
    assert _is_ignored(root, "state/issues/execution/issue-999.md")
    assert _is_ignored(root, "state/issues/archive/issue-999.md")
    assert _is_ignored(root, "state/runs/issue-999/run.yaml")
    assert _is_ignored(root, "worktrees/sample/issue-999/README.md")


def _is_ignored(root: Path, path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--no-index", path],
        check=False,
    )
    return result.returncode == 0
