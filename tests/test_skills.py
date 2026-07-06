from pathlib import Path

import yaml


SKILLS = {
    "using-go-ship-it",
    "manage-issues",
    "work-issue",
}

DEPRECATED_SKILLS = {
    "add-issue",
    "start-issue",
    "investigate-issue",
    "propose-fix",
    "implement-fix",
    "test-and-review",
    "cleanup-issue",
}

SKILL_REFERENCES = {
    "using-go-ship-it": ("references/command-surface.md",),
    "manage-issues": ("references/state-lifecycle.md",),
    "work-issue": ("references/workflow-notes-template.md",),
}

ORIENTATION_COMMANDS = {
    "using-go-ship-it": ("go-ship-it status", "go-ship-it doctor"),
    "manage-issues": ("go-ship-it status", "go-ship-it list-issues", "go-ship-it show-issue"),
    "work-issue": ("go-ship-it show-issue", "go-ship-it show-run"),
}

SKILL_COMMANDS = {
    "manage-issues": (
        "go-ship-it init",
        "go-ship-it add-issue",
        "go-ship-it start-issue",
        "go-ship-it cleanup-issue",
    ),
    "work-issue": (
        "go-ship-it set-phase",
        "go-ship-it append-note",
        "go-ship-it run-check",
        "go-ship-it handoff",
        "go-ship-it prepare-pr",
    ),
}


def test_expected_skill_folders_exist():
    root = Path(__file__).resolve().parents[1]
    for skill in SKILLS:
        skill_file = root / "skills" / skill / "SKILL.md"
        assert skill_file.exists(), f"missing {skill_file}"
        text = skill_file.read_text()
        assert "## When To Use" in text


def test_repo_scoped_codex_skill_shims_point_to_canonical_skills():
    root = Path(__file__).resolve().parents[1]
    for skill in SKILLS:
        shim = root / ".agents" / "skills" / skill
        assert shim.exists(), f"missing {shim}"
        assert (shim / "SKILL.md").resolve() == (root / "skills" / skill / "SKILL.md").resolve()


def test_repo_scoped_codex_marketplace_points_to_local_plugin():
    root = Path(__file__).resolve().parents[1]
    marketplace = root / ".agents" / "plugins" / "marketplace.json"
    assert marketplace.exists()
    data = yaml.safe_load(marketplace.read_text())
    assert data["name"] == "go-ship-it-local"
    assert data["plugins"][0]["name"] == "go-ship-it"
    assert data["plugins"][0]["source"] == {"source": "local", "path": "."}


def test_deprecated_lifecycle_skill_folders_are_removed():
    root = Path(__file__).resolve().parents[1]
    for skill in DEPRECATED_SKILLS:
        assert not (root / "skills" / skill).exists(), f"{skill} should be consolidated"


def test_skill_frontmatter_is_trigger_focused():
    root = Path(__file__).resolve().parents[1]
    for skill in SKILLS:
        text = (root / "skills" / skill / "SKILL.md").read_text()
        assert text.startswith("---\n")
        _start, raw_frontmatter, _body = text.split("---", 2)
        metadata = yaml.safe_load(raw_frontmatter)
        assert metadata["name"] == skill
        assert metadata["description"].startswith("Use when ")
        assert len(metadata["description"]) < 500


def test_shared_lifecycle_reference_exists():
    root = Path(__file__).resolve().parents[1]
    reference = root / "references" / "lifecycle.md"
    assert reference.exists()
    assert "todo -> execution -> archive" in reference.read_text()


def test_skill_references_are_local_to_skill_folders():
    root = Path(__file__).resolve().parents[1]
    for skill, references in SKILL_REFERENCES.items():
        for reference in references:
            path = root / "skills" / skill / reference
            assert path.exists(), f"missing {path}"
            assert path.read_text().startswith("# ")


def test_consolidated_skills_reference_their_cli_plumbing():
    root = Path(__file__).resolve().parents[1]
    for skill, commands in SKILL_COMMANDS.items():
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


def test_bootstrap_skill_routes_to_two_operational_skills():
    root = Path(__file__).resolve().parents[1]
    text = (root / "skills" / "using-go-ship-it" / "SKILL.md").read_text()

    assert "`manage-issues`" in text
    assert "`work-issue`" in text
    for deprecated in DEPRECATED_SKILLS:
        assert f"`{deprecated}`" not in text


def test_bootstrap_skill_names_natural_invocation_phrases():
    root = Path(__file__).resolve().parents[1]
    text = (root / "skills" / "using-go-ship-it" / "SKILL.md").read_text()

    assert "use GoShipit" in text
    assert "Go Ship It" in text
    assert "go ship it this project" in text


def test_work_issue_skill_names_readiness_gate_and_acceptance_evidence():
    root = Path(__file__).resolve().parents[1]
    text = (root / "skills" / "work-issue" / "SKILL.md").read_text()
    template = (root / "skills" / "work-issue" / "references" / "workflow-notes-template.md").read_text()

    assert "go-ship-it verify-run" in text
    assert "--strict" in text
    assert "acceptance criteria" in text
    assert "sub-agent" in text
    assert "semantic done/not-done judgment" in text
    assert "Acceptance criteria matched to evidence" in template
    assert "Independent checker verdict" in template
    assert "Decision record" in template


def test_command_surface_mentions_json_and_strict_readiness():
    root = Path(__file__).resolve().parents[1]
    text = (root / "skills" / "using-go-ship-it" / "references" / "command-surface.md").read_text()

    assert "go-ship-it status --json" in text
    assert "go-ship-it doctor --json" in text
    assert "go-ship-it verify-run <repo>/<issue-id> --strict" in text
    assert "go-ship-it prepare-pr <repo>/<issue-id>" in text


def test_first_issue_docs_explain_what_gets_created():
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text()
    user_e2e = (root / "docs" / "user-e2e.md").read_text()

    for text in (readme, user_e2e):
        assert "What Gets Created" in text
        assert "state/repos/<repo>/issues/execution/<issue-id>/run.yaml" in text
        assert ".go-ship-it/context.yaml" in text


def test_maintainer_notes_require_pressure_scenarios_for_skill_changes():
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "maintainers.md").read_text()

    assert "pressure scenario" in text
    assert "dogfood" in text
    assert "new skills" in text
