# Issue 014: Skill Surface Consolidation

## Problem

The package had seven lifecycle skill folders plus the bootstrap skill. That matched the internal phase model, but it made the agent-facing surface feel larger than the product should be for first use.

## Decision

Consolidate the agent-facing surface to three skills:

- `using-go-ship-it`: package/control-root orientation and routing.
- `manage-issues`: setup, todo creation, start/status, and cleanup.
- `work-issue`: investigation, proposal, implementation, test/review, and evidence capture.

The CLI remains richer because it is state plumbing. A new CLI verb should not automatically become a new skill.

## Structure

Each skill owns local references only when they help:

- `skills/using-go-ship-it/references/command-surface.md`
- `skills/manage-issues/references/state-lifecycle.md`
- `skills/work-issue/references/workflow-notes-template.md`

Shared package scripts stay at root `scripts/` because they operate across the whole package.

## Verification

Focused validation:

```sh
uv run pytest tests/test_skills.py tests/test_plugin_packaging.py tests/test_install_adapters.py tests/test_doctor.py tests/test_cli_smoke.py -q
```

Result: `62 passed`.
