# GoShipit

GoShipit is a local-first control repo for agent-assisted software work.

Version 0 manages a simple lifecycle:

```text
todo -> execution -> archive
```

Target repositories stay outside this repo. Each active issue gets its own Git worktree under `worktrees/<repo>/<issue-id>/`.

## Development

```sh
uv run pytest
```
