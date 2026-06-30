---
name: add-issue
description: Create a GoShipit todo issue for a registered target repo.
---

# Add Issue

## When To Use

Use when the user wants to capture new work before starting implementation.

## Required Inputs

- Target repo id
- Title
- Problem statement
- Context
- Acceptance criteria

## Orientation

Before adding an issue, run:

```sh
go-ship-it status
```

If repo setup is uncertain, also run `go-ship-it doctor` and confirm the target repo is registered.

## Allowed State Reads

- `state/repos/<repo>.yaml`
- `state/issues/todo/`
- `state/issues/execution/`
- `state/issues/archive/`

## Allowed State Writes

- Create one issue file in `state/issues/todo/`

## Allowed Target Repo Writes

None.

## Scripts Or Commands

Run:

```sh
go-ship-it add-issue --repo <repo> --title <title> --problem <problem> --context <context> --acceptance <criterion>
```

## Human Approval Gates

Ask the user when the target repo, title, or acceptance criteria are unclear.

## Evidence To Write

The created issue file is the evidence.

## Next Recommended Skill

`start-issue`

## Failure Behavior

Report the CLI error and do not create or edit target repo files.
