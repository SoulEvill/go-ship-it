from pathlib import Path

from go_ship_it.state import INNER_LOOPS, PHASES, REVIEW_PIPELINES, TRACKS

ROOT = Path(__file__).resolve().parents[1]

PHASE_DOCS = {
    "investigate": "skills/work-issue/references/phases/investigate.md",
    "propose": "skills/work-issue/references/phases/propose.md",
    "implement": "skills/work-issue/references/phases/implement.md",
    "review": "skills/work-issue/references/phases/review.md",
    "prepare-pr": "skills/close-out/references/phases/write-pr.md",
    "publish": "skills/close-out/references/phases/publish.md",
    "archived": "skills/close-out/references/phases/archive.md",
}


def test_every_lifecycle_phase_has_exactly_one_contract_doc():
    assert set(PHASE_DOCS) == set(PHASES) - {"setup"}


def test_phase_docs_follow_the_contract_template():
    for _phase, relative in sorted(PHASE_DOCS.items()):
        text = (ROOT / relative).read_text()
        for heading in ("## Inputs", "## Outputs", "## Evidence", "## Gate"):
            assert heading in text, f"{relative} missing {heading}"


def test_implement_doc_names_the_pluggable_inner_loops():
    text = (ROOT / PHASE_DOCS["implement"]).read_text()
    for loop in INNER_LOOPS:
        assert loop in text


def test_review_doc_names_the_pluggable_pipelines():
    text = (ROOT / PHASE_DOCS["review"]).read_text()
    for pipeline in REVIEW_PIPELINES:
        assert pipeline in text
    assert "plugin:" in text


def test_propose_doc_pins_the_acceptance_test_gate():
    text = (ROOT / PHASE_DOCS["propose"]).read_text()
    assert "acceptance-level failing test" in text


def test_archive_doc_warns_terminal():
    text = (ROOT / PHASE_DOCS["archived"]).read_text()
    assert "terminal" in text
    assert "--confirm" in text


def test_lifecycle_reference_matches_the_phase_enum():
    text = (ROOT / "references" / "lifecycle.md").read_text()
    assert " -> ".join(PHASES) in text
    for track in TRACKS:
        assert track in text
