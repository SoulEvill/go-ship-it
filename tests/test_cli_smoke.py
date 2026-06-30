from go_ship_it import __version__
from go_ship_it.cli import build_parser, main


def test_version_is_defined():
    assert __version__ == "0.1.0"


def test_parser_has_init_command():
    parser = build_parser()
    args = parser.parse_args(["init"])
    assert args.command == "init"


def test_main_help_exits_cleanly(capsys):
    exit_code = main(["--help"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "GoShipit" in captured.out


def test_main_init_creates_state_layout(tmp_path):
    exit_code = main(["--root", str(tmp_path), "init"])

    assert exit_code == 0
    assert (tmp_path / "state" / "repos").is_dir()
    assert (tmp_path / "state" / "issues" / "todo").is_dir()


def test_register_repo_cli_preserves_relative_paths(tmp_path):
    exit_code = main(["--root", str(tmp_path), "register-repo", "sample", "../sample-target"])

    assert exit_code == 0
    assert "path: ../sample-target\n" in (tmp_path / "state" / "repos" / "sample.yaml").read_text()
