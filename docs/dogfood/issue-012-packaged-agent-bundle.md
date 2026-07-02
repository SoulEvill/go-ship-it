# Packaged Agent Bundle Dogfood

Date: 2026-07-02

## Problem

The source repo had one bundled skill package, but the built Python wheel only contained the `go_ship_it` Python module. A user installing the wheel would get the CLI without `.claude-plugin/`, `.cursor-plugin/`, `.codex-plugin/`, `skills/`, `hooks/`, or `references/`.

That breaks the intended user experience: install GoShipit once, then point each agent harness at the bundled package. Users should not install every skill independently.

## Changes

- Added `go-ship-it package-root`.
- Packaged agent assets into the wheel under `go_ship_it/package/`.
- Made `doctor` check package health from the bundled package root.
- Clarified package root vs control root in docs, skills, and session-start hook output.
- Added a wheel-content regression test.

## User Model

- Package root: skills, hooks, plugin manifests, references, docs.
- Control root: lifecycle state, run evidence, managed worktrees.

In clone-based development they can be the same directory. In package-install mode they are normally different.

## Example

```sh
go-ship-it package-root
claude --plugin-dir "$(go-ship-it package-root)" --help
cursor-agent --plugin-dir "$(go-ship-it package-root)" --help
```

Then run lifecycle commands from the control root:

```sh
go-ship-it status
go-ship-it doctor
```

or explicitly:

```sh
go-ship-it --root <control-root> status
go-ship-it --root <control-root> doctor
```
