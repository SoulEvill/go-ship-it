# Daily Navigation Dogfood

## Commands

Ran from the GoShipit repository root on 2026-06-30:

```bash
uv run go-ship-it list-issues
uv run go-ship-it list-issues --state archive --repo parawave
uv run go-ship-it show-issue issue-002
uv run go-ship-it show-run issue-002
uv run go-ship-it show-run issue-002 --commands
uv run go-ship-it status
```

## Output Excerpts

`list-issues`:

```text
issue-002 [archive] parawave - Validate Parawave command configuration
```

`show-issue issue-002`:

```text
# issue-002

Title: Validate Parawave command configuration
Repo: parawave
Status: archive
Phase: cleanup
Branch: go-ship-it/issue-002
Worktree: worktrees/parawave/issue-002
Issue File: state/issues/archive/issue-002.md
```

`show-run issue-002`:

```text
# Run: issue-002

Run File: state/runs/issue-002/run.yaml
Phase: cleanup
Branch: go-ship-it/issue-002
Worktree: worktrees/parawave/issue-002

## Command Summary
- setup exit 0: env -u VIRTUAL_ENV uv sync --extra dev
- test exit 0: env -u VIRTUAL_ENV uv run --extra dev pytest -q
```

`show-run issue-002 --commands`:

```text
## Command Records

### state/runs/issue-002/commands/2026-06-30T11-21-30-07-00-setup.yaml

- Check: `setup`
- Command: `env -u VIRTUAL_ENV uv sync --extra dev`
- CWD: `worktrees/parawave/issue-002`
- Exit Code: `0`
```

`status`:

```text
# GoShipit Status

Repos: 1
Todo: 0
Execution: 0
Archive: 1
Runs: 1
Managed Worktrees: 2

## Active Issues
No active issues.

## Preserved Worktrees
- parawave/issue-001
- parawave/issue-002
```

## What Worked

- The commands produced stable, root-relative paths.
- `show-run` kept command tails out of the default output.
- `status` made it clear there were no active issues but preserved worktrees remained.

## What Felt Weak

- `show-run --commands` is intentionally verbose once tails are included.
- The command record section is useful, but most daily use should start with the summary output.

## Recommended Next Step

Keep this milestone limited to read-only navigation. A future `doctor` command can separately check stale worktrees, missing repos, and command configuration health.
