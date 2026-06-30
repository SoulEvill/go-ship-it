from __future__ import annotations

from collections.abc import Mapping

import yaml


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return {}, text

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            raw_metadata = "".join(lines[1:index])
            loaded = yaml.safe_load(raw_metadata) or {}
            if not isinstance(loaded, dict):
                raise ValueError("Frontmatter must be a mapping")
            body = "".join(lines[index + 1 :])
            return {str(key): value for key, value in loaded.items()}, body

    raise ValueError("Frontmatter is missing closing delimiter")


def render_frontmatter(metadata: Mapping[str, object], body: str) -> str:
    rendered_metadata = yaml.safe_dump(
        dict(metadata),
        sort_keys=False,
        default_flow_style=False,
    )
    return f"---\n{rendered_metadata}---\n{body}"
