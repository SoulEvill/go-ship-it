# User E2E Hardening Dogfood

## Commands

```bash
uv run pytest -v
uv run go-ship-it doctor
uv run go-ship-it doctor --strict
uv run go-ship-it status
scripts/install-claude-skills.sh --target <temp>/.claude/skills
scripts/install-cursor-adapter.sh --target <temp>
find <temp> -maxdepth 4 -type f
```

## Output Excerpts

Full test suite:

```text
collected 75 items
75 passed in 2.05s
```

Doctor:

```text
# GoShipit Doctor

Summary: 0 errors, 3 warnings, 11 ok
```

Doctor warnings were expected for the current local state:

```text
- repo/parawave: lint_command is not configured (repo.lint_command_missing)
- worktree/parawave/issue-001: preserved worktree has no matching issue file (worktree.preserved_without_issue)
- worktree/parawave/issue-002: preserved worktree has no active execution issue (worktree.preserved_without_active_issue)
```

`go-ship-it doctor --strict` exited `1` because warnings are present and strict mode treats warnings as failures.

Status:

```text
Execution: 0
Archive: 1
Managed Worktrees: 2
No active issues.
```

Adapter-created files:

```text
<temp>/.cursor/rules/go-ship-it.mdc
<temp>/.claude/skills/add-issue/SKILL.md
<temp>/.claude/skills/cleanup-issue/SKILL.md
<temp>/.claude/skills/implement-fix/SKILL.md
<temp>/.claude/skills/investigate-issue/SKILL.md
<temp>/.claude/skills/propose-fix/SKILL.md
<temp>/.claude/skills/start-issue/SKILL.md
<temp>/.claude/skills/test-and-review/SKILL.md
<temp>/AGENTS.md
```

## Notes

Remote GitHub, PR, and Jira integrations were not exercised in this milestone.
