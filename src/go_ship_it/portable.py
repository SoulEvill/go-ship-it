from __future__ import annotations

from pathlib import Path


def relative_to_root(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def portable_path_value(root: Path, value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        return str(value)
    path = Path(value)
    if path.is_absolute():
        return relative_to_root(root, path)
    return portable_text(root, value)


def portable_text(root: Path, value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    root_text = str(root)
    return (
        text.replace(f"file://{root_text}/", "file://go-ship-it-root/")
        .replace(f"{root_text}/", "")
        .replace(root_text, ".")
    )
