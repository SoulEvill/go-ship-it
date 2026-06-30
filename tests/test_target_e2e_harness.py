from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts" / "run-target-e2e.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("run_target_e2e", HARNESS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parser_requires_explicit_target_arguments():
    harness = load_harness()

    args = harness.parse_args(
        [
            "--target-id",
            "sample",
            "--target-path",
            "/tmp/sample",
            "--setup-command",
            "python -c 'print(\"setup\")'",
            "--test-command",
            "python -c 'print(\"test\")'",
        ]
    )

    assert args.target_id == "sample"
    assert args.target_path == "/tmp/sample"
    assert args.setup_command == "python -c 'print(\"setup\")'"
    assert args.test_command == "python -c 'print(\"test\")'"
    assert args.default_branch == "main"


def test_run_paths_are_target_agnostic(tmp_path):
    harness = load_harness()

    paths = harness.RunPaths.from_root(tmp_path, "sample")

    assert paths.run_root == tmp_path
    assert paths.state_root == tmp_path / "go-ship-it-state"
    assert paths.target_clone == tmp_path / "target" / "sample"
    assert paths.report == tmp_path / "report.md"
