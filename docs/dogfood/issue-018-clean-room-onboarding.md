# Issue 018: Clean-Room Onboarding Audit

## Results

Ran a fresh-user rehearsal from a temporary directory with no GoShipit state:

- Temp room: `/tmp/go-ship-it-new-user-wHVFQD`
- Installed package from a locally built wheel into `/tmp/go-ship-it-new-user-wHVFQD/venv`
- Created a new target git repo at `/tmp/go-ship-it-new-user-wHVFQD/target-repo`
- Created a new control root at `/tmp/go-ship-it-new-user-wHVFQD/control-root`
- Registered the target repo with only a `test_command`
- Added an issue, started it, used `--current` from the managed worktree, wrote a handoff, ran the configured test check, and archived with worktree removal

Final clean-room status:

- Repos: 1
- Todo: 0
- Execution: 0
- Archive: 1
- Runs: 1
- Managed Worktrees: 0

Final clean-room doctor:

- 0 errors
- 0 warnings
- 11 ok

Release verification after the audit:

- `uv run pytest -q`: 156 passed
- `uv run go-ship-it doctor`: 0 errors, 0 warnings
- `just release-check`: passed tests, doctor, wheel build, packaged install validation, Claude plugin-dir validation, Cursor Agent plugin-dir validation, Codex command availability, and fallback skill/rule install validation

## Rough Edges Observed

- Running `status` from a blank directory told the user the root was not initialized, but did not clearly point them to `go-ship-it init`.
- The happy-path cleanup examples archived completed work without `--remove-worktree`, which left preserved worktrees and made `doctor` warn in the common case.
- A repo configured with only `test_command` looked less healthy than it should because `doctor` warned about missing optional setup and lint commands.
- The bootstrap skill did not explicitly say that natural requests like "use GoShipit" or "Go Ship It this project" should invoke the orientation skill.

## Lessons To Promote

- Update docs: show completed-work archive cleanup with `--remove-worktree` in the README, command surface, lifecycle skill, and user E2E guide.
- Update skill: make `using-go-ship-it` claim the natural entry phrases a new user is likely to say.
- Update CLI: make uninitialized-root errors tell users to run `go-ship-it init`.
- Update status: show cleanup/archive as a next command for active issues, including `--remove-worktree`.
- Update verifier behavior: treat setup, test, and lint commands as optional individually; warn only when no check commands are configured at all.

## Deferred Product Questions

- Consider a future `quickstart` or interactive `init` only after more real user testing. The current command path is now understandable enough without adding another entry point.
- Real Claude Code and Cursor CLI session behavior still needs live user-side testing later. The package-level and fallback install checks pass, but the human experience of invoking the skill inside each agent should still be observed.
