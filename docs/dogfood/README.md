# Dogfood Reports

Dogfood reports are committed maintainer notes for GoShipit contributors. They capture what happened while dogfooding the harness and what the harness should learn.

Normal user runs should not write here by default. `go-ship-it export-run` writes an issue-local `evidence.md` inside `state/repos/<repo>/issues/.../<issue-id>/` unless the user explicitly chooses another output path.

Every report should include:

## Results

Concrete command results, evidence paths, branch/worktree state, and final status.

## Rough Edges Observed

Friction seen while using GoShipit, including issue id handling, worktree discovery, phase/evidence commands, check/export behavior, cleanup, and target integration.

## Lessons To Promote

Each lesson should map to one of:

- update a skill
- update docs
- add verifier check
- defer as product question

This section is the bridge from one dogfood run to a better next run.
