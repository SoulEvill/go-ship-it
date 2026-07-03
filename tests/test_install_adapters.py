from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_claude_installer_copies_skill_folders(tmp_path):
    target = tmp_path / ".claude" / "skills"

    result = subprocess.run(
        [str(ROOT / "scripts" / "install-claude-skills.sh"), "--target", str(target)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (target / "using-go-ship-it" / "SKILL.md").exists()
    assert (target / "manage-issues" / "references" / "state-lifecycle.md").exists()
    assert (target / "work-issue" / "references" / "workflow-notes-template.md").exists()


def test_cursor_installer_writes_rule_and_agents_file(tmp_path):
    result = subprocess.run(
        [str(ROOT / "scripts" / "install-cursor-adapter.sh"), "--target", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    rule = tmp_path / ".cursor" / "rules" / "go-ship-it.mdc"
    agents = tmp_path / "AGENTS.md"
    assert rule.exists()
    assert agents.exists()
    assert "go-ship-it doctor" in rule.read_text()
    assert "skills/using-go-ship-it/SKILL.md" in agents.read_text()
    assert "skills/manage-issues/SKILL.md" in agents.read_text()
    assert "skills/work-issue/SKILL.md" in agents.read_text()
