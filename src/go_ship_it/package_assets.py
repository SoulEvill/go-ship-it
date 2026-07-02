from __future__ import annotations

from pathlib import Path


def package_root() -> Path:
    """Return the directory that contains GoShipit's bundled agent package."""
    source_root = Path(__file__).resolve().parents[2]
    if _looks_like_package_root(source_root):
        return source_root

    installed_root = Path(__file__).resolve().parent / "package"
    if _looks_like_package_root(installed_root):
        return installed_root

    return source_root


def _looks_like_package_root(path: Path) -> bool:
    return (
        (path / "skills" / "using-go-ship-it" / "SKILL.md").exists()
        and (path / ".claude-plugin" / "plugin.json").exists()
        and (path / ".codex-plugin" / "plugin.json").exists()
        and (path / ".cursor-plugin" / "plugin.json").exists()
    )
