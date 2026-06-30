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

PHASE_SKILL_TEMPLATES = {
    "investigate-issue": "references/investigation-template.md",
    "propose-fix": "references/proposal-template.md",
    "implement-fix": "references/implementation-notes-template.md",
    "test-and-review": "references/test-review-template.md",
    "cleanup-issue": "references/cleanup-template.md",
}

PHASE_SKILL_COMMANDS = {
    "investigate-issue": ("go-ship-it set-phase", "go-ship-it append-note"),
    "propose-fix": ("go-ship-it set-phase", "go-ship-it append-note"),
    "implement-fix": ("go-ship-it set-phase", "go-ship-it append-note"),
    "test-and-review": ("go-ship-it set-phase", "go-ship-it run-check", "go-ship-it append-note"),
    "cleanup-issue": ("go-ship-it set-phase", "go-ship-it cleanup-issue"),
}

ORIENTATION_COMMANDS = {
    "add-issue": ("go-ship-it status",),
    "start-issue": ("go-ship-it list-issues --state todo", "go-ship-it show-issue"),
    "investigate-issue": ("go-ship-it show-issue", "go-ship-it show-run"),
    "propose-fix": ("go-ship-it show-issue", "go-ship-it show-run"),
    "implement-fix": ("go-ship-it show-run",),
    "test-and-review": ("go-ship-it show-run",),
    "cleanup-issue": ("go-ship-it doctor", "go-ship-it show-run"),
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


def test_phase_skill_templates_exist():
    root = Path(__file__).resolve().parents[1]
    for skill, template in PHASE_SKILL_TEMPLATES.items():
        path = root / "skills" / skill / template
        assert path.exists(), f"missing {path}"
        assert path.read_text().startswith("# ")


def test_phase_skills_reference_evidence_commands():
    root = Path(__file__).resolve().parents[1]
    for skill, commands in PHASE_SKILL_COMMANDS.items():
        text = (root / "skills" / skill / "SKILL.md").read_text()
        for command in commands:
            assert command in text, f"{skill} should mention {command}"


def test_skills_include_orientation_commands():
    root = Path(__file__).resolve().parents[1]
    for skill, commands in ORIENTATION_COMMANDS.items():
        text = (root / "skills" / skill / "SKILL.md").read_text()
        assert "## Orientation" in text
        for command in commands:
            assert command in text, f"{skill} should mention {command}"
