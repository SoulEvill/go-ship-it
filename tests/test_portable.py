from pathlib import Path

from go_ship_it.portable import portable_path_value, portable_text, relative_to_root


def test_relative_to_root_returns_posix_relative_path(tmp_path):
    root = tmp_path / "go-ship-it"
    target = root / "state" / "runs" / "issue-001" / "run.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("x")

    assert relative_to_root(root, target) == "state/runs/issue-001/run.yaml"


def test_relative_to_root_keeps_external_absolute_path(tmp_path):
    root = tmp_path / "go-ship-it"
    outside = tmp_path / "outside.txt"

    assert relative_to_root(root, outside) == str(outside)


def test_portable_text_removes_local_root(tmp_path):
    root = tmp_path / "go-ship-it"
    text = f"Evidence: {root}/state/runs/issue-001/run.yaml"

    assert portable_text(root, text) == "Evidence: state/runs/issue-001/run.yaml"


def test_portable_text_rewrites_file_urls(tmp_path):
    root = tmp_path / "go-ship-it"
    text = f"file://{root}/docs/dogfood/report.md"

    assert portable_text(root, text) == "file://go-ship-it-root/docs/dogfood/report.md"


def test_portable_path_value_handles_none(tmp_path):
    assert portable_path_value(tmp_path, None) == ""
