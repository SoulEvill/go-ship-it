from pathlib import Path


SKILLS = {
    "add-issue",
    "start-issue",
    "investigate-issue",
    "propose-fix",
    "implement-fix",
    "test-and-review",
    "cleanup-issue",
}


def test_expected_skill_folders_exist():
    root = Path(__file__).resolve().parents[1]
    for skill in SKILLS:
        skill_file = root / "skills" / skill / "SKILL.md"
        assert skill_file.exists(), f"missing {skill_file}"
        text = skill_file.read_text()
        assert "## When To Use" in text
        assert "## Allowed State Writes" in text
        assert "## Failure Behavior" in text


def test_shared_lifecycle_reference_exists():
    root = Path(__file__).resolve().parents[1]
    reference = root / "references" / "lifecycle.md"
    assert reference.exists()
    assert "todo -> execution -> archive" in reference.read_text()
