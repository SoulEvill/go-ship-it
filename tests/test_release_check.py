from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_check_runs_lightweight_gate_in_order(monkeypatch):
    module = _load_script()
    commands: list[list[str]] = []

    def fake_run(command: list[str]) -> object:
        commands.append(command)
        return module.CommandResult(command=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module, "_run_command", fake_run)

    report = module.run_release_check()

    assert report.failed_count == 0
    assert commands == [
        ["uv", "run", "pytest", "-q"],
        ["uv", "run", "go-ship-it", "doctor"],
        ["uv", "build"],
        ["scripts/validate-packaged-install.py", "--wheel", "dist/go_ship_it-0.1.0-py3-none-any.whl"],
        ["scripts/validate-agent-cli-integration.py"],
    ]


def test_release_check_stops_after_failed_step(monkeypatch):
    module = _load_script()
    commands: list[list[str]] = []

    def fake_run(command: list[str]) -> object:
        commands.append(command)
        if command == ["uv", "run", "go-ship-it", "doctor"]:
            return module.CommandResult(command=command, returncode=1, stdout="", stderr="doctor failed")
        return module.CommandResult(command=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module, "_run_command", fake_run)

    report = module.run_release_check()

    assert report.failed_count == 1
    assert commands == [
        ["uv", "run", "pytest", "-q"],
        ["uv", "run", "go-ship-it", "doctor"],
    ]


def test_justfile_exposes_release_check():
    text = (ROOT / "Justfile").read_text()

    assert "release-check:" in text
    assert "scripts/release-check.py" in text


def _load_script():
    path = ROOT / "scripts" / "release-check.py"
    spec = importlib.util.spec_from_file_location("release_check", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
