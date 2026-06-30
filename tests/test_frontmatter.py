from go_ship_it.frontmatter import parse_frontmatter, render_frontmatter


def test_frontmatter_round_trip():
    text = render_frontmatter(
        {
            "id": "issue-001",
            "repo": "parawave",
            "status": "todo",
            "phase": "setup",
            "worktree": None,
        },
        "## Problem\n\nDo the thing.\n",
    )

    metadata, body = parse_frontmatter(text)

    assert metadata == {
        "id": "issue-001",
        "repo": "parawave",
        "status": "todo",
        "phase": "setup",
        "worktree": None,
    }
    assert body == "## Problem\n\nDo the thing.\n"
