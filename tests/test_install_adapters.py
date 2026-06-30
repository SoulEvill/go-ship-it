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
    assert (target / "add-issue" / "SKILL.md").exists()
    assert (target / "test-and-review" / "references" / "test-review-template.md").exists()


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
    assert "skills/<skill-name>/SKILL.md" in agents.read_text()
