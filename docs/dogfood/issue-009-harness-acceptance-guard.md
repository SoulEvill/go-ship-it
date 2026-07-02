# Harness Acceptance Guard

Date: 2026-07-02

## Results

- Added a working-directory guard to `skills/using-go-ship-it/SKILL.md`.
- Updated session-start hook context to include the concrete GoShipit package root.
- Made `go-ship-it status` fail loudly when run outside an initialized GoShipit control repo.
- Added tests for the hook package-root context, bootstrap root guard language, and wrong-root `status` behavior.

## Commands

```sh
uv run pytest tests/test_cli_smoke.py::test_main_status_rejects_uninitialized_root tests/test_plugin_packaging.py::test_session_start_hook_outputs_cursor_context tests/test_plugin_packaging.py::test_session_start_hook_outputs_claude_context tests/test_plugin_packaging.py::test_session_start_hook_outputs_generic_context tests/test_plugin_packaging.py::test_bootstrap_skill_includes_control_root_guard -v
# 5 passed

bash hooks/run-hook.cmd session-start
# emitted bootstrap JSON with GoShipit package root and --root guidance
```

## What This Solves

The main harness risk is not whether an agent can invoke the exact skill automatically. A user can explicitly invoke or reference `using-go-ship-it`.

The higher-risk failure is an agent operating from the wrong directory:

- treating a target repo as the control repo
- running `go-ship-it status` in the wrong checkout
- seeing an empty-looking workspace and making bad assumptions
- editing target code from the control repo instead of the managed worktree

This guard makes the failure visible and gives the agent an explicit recovery path: change to the control root or pass `--root <control-root>`.

## Remaining Human Checks

- Open a clean Claude Code session from the GoShipit repo and verify it can follow the guard.
- Open a clean Codex session from the GoShipit repo and verify it can follow the guard.
- Open a clean Cursor session from the GoShipit repo and verify it can follow the guard.
- Repeat at least one session from the wrong directory and confirm the agent recovers by using the control root.

## Lessons To Promote

- Harness acceptance should focus first on root safety and worktree boundaries.
- Skill auto-discovery is useful, but explicit invocation is acceptable if the guardrails are clear.
- Wrong-root commands should fail loudly when they can otherwise produce misleading empty output.
