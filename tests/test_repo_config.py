from pathlib import Path

import pytest
import yaml

from go_ship_it.state import read_repo_config, register_repo, update_repo_config


def test_read_repo_config_returns_registered_yaml(tmp_path):
    register_repo(
        tmp_path,
        repo_id="sample",
        path=Path("../sample"),
        default_branch="main",
        setup_command="uv sync",
        test_command="uv run pytest",
        lint_command=None,
    )

    config = read_repo_config(tmp_path, "sample")

    assert config["id"] == "sample"
    assert config["path"] == "../sample"
    assert config["default_branch"] == "main"
    assert config["setup_command"] == "uv sync"
    assert config["test_command"] == "uv run pytest"
    assert config["lint_command"] is None


def test_update_repo_config_updates_one_command_and_preserves_relative_path(tmp_path):
    register_repo(
        tmp_path,
        repo_id="sample",
        path=Path("../sample"),
        default_branch="main",
        setup_command="uv sync",
        test_command="uv run pytest",
        lint_command=None,
    )

    repo_file = update_repo_config(
        tmp_path,
        "sample",
        updates={"test_command": "env -u VIRTUAL_ENV uv run --extra dev pytest -q"},
        clears=set(),
    )

    data = yaml.safe_load(repo_file.read_text())
    assert data["path"] == "../sample"
    assert data["setup_command"] == "uv sync"
    assert data["test_command"] == "env -u VIRTUAL_ENV uv run --extra dev pytest -q"
    assert data["lint_command"] is None


def test_update_repo_config_clears_optional_command(tmp_path):
    register_repo(
        tmp_path,
        repo_id="sample",
        path=Path("../sample"),
        default_branch="main",
        setup_command="uv sync",
        test_command="uv run pytest",
        lint_command="ruff check .",
    )

    update_repo_config(tmp_path, "sample", updates={}, clears={"lint_command"})

    data = read_repo_config(tmp_path, "sample")
    assert data["lint_command"] is None


def test_update_repo_config_rejects_empty_required_field(tmp_path):
    register_repo(
        tmp_path,
        repo_id="sample",
        path=Path("../sample"),
        default_branch="main",
        setup_command=None,
        test_command=None,
        lint_command=None,
    )

    with pytest.raises(ValueError, match="default_branch"):
        update_repo_config(tmp_path, "sample", updates={"default_branch": ""}, clears=set())
