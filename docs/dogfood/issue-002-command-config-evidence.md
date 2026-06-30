# GoShipit Run Evidence: issue-002

## Issue

Source: `state/issues/archive/issue-002.md`

```markdown
---
id: issue-002
repo: parawave
status: archive
phase: cleanup
title: Validate Parawave command configuration
created_at: '2026-06-30T11:20:58-07:00'
worktree: worktrees/parawave/issue-002
branch: go-ship-it/issue-002
claimed_by: dogfood
started_at: '2026-06-30T11:21:02-07:00'
last_activity_at: '2026-06-30T11:21:55-07:00'
---

## Problem

Parawave's registered GoShipit command configuration should run the target test suite with the dev extras required by storage tests.

## Context

The prior dogfood run showed uv run pytest failed without optional dev/storage dependencies.

## Acceptance Criteria

- show-repo displays the dev-extra test command.
- run-check --check setup records exit 0.
- run-check --check test records exit 0.
- export-run writes a committed Markdown evidence snapshot.

## Final Note

Command configuration validation complete; evidence exported.
```

## Run Metadata

```yaml
issue_id: issue-002
repo: parawave
branch: go-ship-it/issue-002
worktree: worktrees/parawave/issue-002
claimed_by: dogfood
phase: cleanup
started_at: '2026-06-30T11:21:02-07:00'
last_activity_at: '2026-06-30T11:21:26-07:00'
cleanup_destination: archive
cleanup_note: Command configuration validation complete; evidence exported.
closed_at: '2026-06-30T11:21:55-07:00'
closed_branch: go-ship-it/issue-002
```

## Journal

## Phase: investigate

Timestamp: 2026-06-30T11:21:12-07:00
Phase: investigate

Inspecting repo command configuration from the prior dogfood failure.

## Investigation

Timestamp: 2026-06-30T11:21:16-07:00
Phase: investigate

Parawave requires dev extras for the storage tests. The registry now uses env -u VIRTUAL_ENV uv run --extra dev pytest -q.

## Phase: propose

Timestamp: 2026-06-30T11:21:21-07:00
Phase: propose

Validate the updated registered commands through run-check and export the run evidence.

## Phase: test

Timestamp: 2026-06-30T11:21:26-07:00
Phase: test

Running updated Parawave registered setup and test commands.

## Check: setup

Timestamp: 2026-06-30T11:21:30-07:00
Phase: test

Command: `env -u VIRTUAL_ENV uv sync --extra dev`

Exit code: 0

Evidence: `/Users/zhengisamazing/1.python_dir/go_ship_it_working_dir/go-ship-it/state/runs/issue-002/commands/2026-06-30T11-21-30-07-00-setup.yaml`

## Check: test

Timestamp: 2026-06-30T11:21:50-07:00
Phase: test

Command: `env -u VIRTUAL_ENV uv run --extra dev pytest -q`

Exit code: 0

Evidence: `/Users/zhengisamazing/1.python_dir/go_ship_it_working_dir/go-ship-it/state/runs/issue-002/commands/2026-06-30T11-21-35-07-00-test.yaml`

## Cleanup

Destination: archive

Command configuration validation complete; evidence exported.

## Command Records

### 2026-06-30T11-21-30-07-00-setup.yaml

- Check: `setup`
- Command: `env -u VIRTUAL_ENV uv sync --extra dev`
- CWD: `/Users/zhengisamazing/1.python_dir/go_ship_it_working_dir/go-ship-it/worktrees/parawave/issue-002`
- Exit Code: `0`
- Started: `2026-06-30T11:21:30-07:00`
- Ended: `2026-06-30T11:21:30-07:00`

Stdout tail:

```text

```

Stderr tail:

```text
Using CPython 3.13.5
Creating virtual environment at: .venv
Resolved 184 packages in 0.96ms
   Building parawave @ file:///Users/zhengisamazing/1.python_dir/go_ship_it_working_dir/go-ship-it/worktrees/parawave/issue-002
      Built parawave @ file:///Users/zhengisamazing/1.python_dir/go_ship_it_working_dir/go-ship-it/worktrees/parawave/issue-002
Prepared 1 package in 390ms
Installed 82 packages in 108ms
 + aiofiles==25.1.0
 + aiosqlite==0.22.1
 + anyio==4.12.1
 + attrs==25.4.0
 + backports-zstd==1.3.0
 + cachetools==7.0.5
 + certifi==2026.2.25
 + charset-normalizer==3.4.6
 + click==8.3.1
 + colorama==0.4.6
 + coverage==7.13.4
 + distlib==0.4.0
 + docutils==0.22.4
 + entrypoints==0.4
 + fastjsonschema==2.21.2
 + filelock==3.25.2
 + h11==0.16.0
 + hatch==1.16.5
 + hatchling==1.29.0
 + httpcore==1.0.9
 + httpx==0.28.1
 + hyperlink==21.0.0
 + id==1.6.1
 + idna==3.11
 + iniconfig==2.3.0
 + jaraco-classes==3.4.0
 + jaraco-context==6.1.1
 + jaraco-functools==4.4.0
 + jsonschema==4.26.0
 + jsonschema-specifications==2025.9.1
 + jupyter-client==8.8.0
 + jupyter-core==5.9.1
 + keyring==25.7.0
 + markdown-it-py==4.0.0
 + mdurl==0.1.2
 + more-itertools==10.8.0
 + nbclient==0.10.4
 + nbformat==5.10.4
 + nest-asyncio==1.6.0
 + nh3==0.3.3
 + packaging==26.0
 + papermill==2.7.0
 + parawave==0.1.0 (from file:///Users/zhengisamazing/1.python_dir/go_ship_it_working_dir/go-ship-it/worktrees/parawave/issue-002)
 + pathspec==1.0.4
 + pexpect==4.9.0
 + platformdirs==4.9.4
 + pluggy==1.6.0
 + ptyprocess==0.7.0
 + pygments==2.19.2
 + pyproject-api==1.10.0
 + pyproject-hooks==1.2.0
 + pytest==8.4.2
 + pytest-asyncio==0.26.0
 + pytest-cov==7.0.0
 + python-dateutil==2.9.0.post0
 + python-discovery==1.1.3
 + pyyaml==6.0.3
 + pyzmq==27.1.0
 + readme-renderer==44.0
 + referencing==0.37.0
 + requests==2.32.5
 + requests-toolbelt==1.0.0
 + rfc3986==2.0.0
 + rich==14.3.3
 + rpds-py==0.30.0
 + shellingham==1.5.4
 + six==1.17.0
 + tenacity==9.1.4
 + tomli-w==1.2.0
 + tomlkit==0.14.0
 + tornado==6.5.5
 + tox==4.49.1
 + tox-uv==1.33.4
 + tox-uv-bare==1.33.4
 + tqdm==4.67.3
 + traitlets==5.14.3
 + trove-classifiers==2026.1.14.14
 + twine==6.2.0
 + urllib3==2.6.3
 + userpath==1.9.2
 + uv==0.10.10
 + virtualenv==21.2.0
```

### 2026-06-30T11-21-35-07-00-test.yaml

- Check: `test`
- Command: `env -u VIRTUAL_ENV uv run --extra dev pytest -q`
- CWD: `/Users/zhengisamazing/1.python_dir/go_ship_it_working_dir/go-ship-it/worktrees/parawave/issue-002`
- Exit Code: `0`
- Started: `2026-06-30T11:21:35-07:00`
- Ended: `2026-06-30T11:21:50-07:00`

Stdout tail:

```text
........................................................................ [ 16%]
........................................................................ [ 32%]
........................................................................ [ 48%]
........................................................................ [ 64%]
........................................................................ [ 80%]
........................................................................ [ 97%]
.............                                                            [100%]
445 passed in 14.07s
```

Stderr tail:

```text

```

## Worktree

- Repo: `parawave`
- Branch: `go-ship-it/issue-002`
- Worktree: `worktrees/parawave/issue-002`
- Closed Branch: `go-ship-it/issue-002`

## Notes

Generated by `go-ship-it export-run`. Command records preserve recorded exit codes.
