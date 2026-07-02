# Plugin Packaging Dogfood

Date: 2026-07-02

## Results

- Added bundled package metadata for Claude, Codex, and Cursor.
- Added `using-go-ship-it` as the package bootstrap skill.
- Added session-start hook files for harnesses that support hook context injection.
- Added doctor package checks.
- Verified package manifests and hook output with pytest.

## Commands

```sh
uv run pytest tests/test_plugin_packaging.py tests/test_doctor.py tests/test_install_adapters.py tests/test_skills.py -v
# 22 passed

uv run pytest -v
# 102 passed

uv run go-ship-it doctor
# 0 errors, 0 warnings, 16 ok
# Package manifests, bootstrap skill, and hook files reported ok.
```

## Distribution Decision

GoShipit skills are installed as one bundled package per harness. Individual skill folders remain modular workflow units, but they are not distributed as independent packages.

## Remaining Human Checks

- Test a clean Claude Code session with the local plugin package.
- Test a clean Codex session with the local plugin package.
- Test a clean Cursor session with the local plugin package.
- Record whether each harness loads `using-go-ship-it` automatically.

## Lessons To Promote

- Package health belongs in `doctor` because distribution drift can break user e2e before lifecycle state breaks.
- The bootstrap skill is part of the product, not optional prose.
- Fallback copy scripts are useful for dogfood but should not be described as the long-term install model.
