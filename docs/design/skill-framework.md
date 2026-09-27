# Design: a self-tuning skill framework (successor to GoShipit)

Status: proposal · 2026-09-27
Working name: **whetstone** (you sharpen tools on it over time). The name is a placeholder; see Open questions.

## 1. Why start over

GoShipit is a ~4.9k-line Python CLI built around an 8-phase issue lifecycle, worktree management, and evidence export. Its feedback loop exists, but it routes each piece of friction through that full lifecycle: register a feedback repo, file an issue, run it. That is too heavy to use casually, and it isn't used much.

What is worth keeping:

- **Lessons To Promote** (from `docs/dogfood/README.md`): every observation maps to *update a skill / update docs / add a check / defer*. That is the core of the new tuning loop.
- **Repo context vs. per-run notes.** Durable learnings go in one short file. Transient notes stay out of it.
- **Cross-tool lesson.** Maintaining separate plugin manifests for Claude, Cursor, and Codex, plus hooks, adapters, and install tests, cost a lot. The shared `SKILL.md` standard now makes most of that unnecessary.

What goes away: the CLI, `state/`, `worktrees/`, phase enums, hooks, and per-tool plugin manifests. The investigate/propose/implement/review phase docs can come back later as an ordinary generic skill if they earn it.

## 2. Goals and non-goals

Goals

1. **A skill container.** It can list, add, import, and update skills, with one entry point that shows every skill and its state.
2. **Layers.** Framework ("core") skills and **generic** skills are shared upstream. **Local** (company or personal) skills stay in each clone.
3. **Feedback loop.** Using a skill produces feedback. Feedback is captured per skill, then folded back into the skill on purpose.
4. **Safe upstream updates.** A clone can pull framework and generic updates without merge conflicts, while keeping its own tuning.
5. **Tool-agnostic, Cursor first.** It works the same in Cursor, Codex, and Claude Code. No tool-specific feature is required.
6. **Simple and native.** Plain folders, Markdown, git, and two small shell scripts. No package, no daemon, no database.

Non-goals

- Automatic merging of upstream changes into local tuning. That stays the owner's job; the framework only flags when tuning may be stale.
- Usage telemetry. Without hooks, which aren't portable, "usage" means feedback entries only.
- Managing MCP servers. Jira and GitHub connections are configured per tool. Skills only say which tools they expect.

## 3. The portable baseline (verified 2026-09-27)

| | Cursor | Codex | Claude Code |
|---|---|---|---|
| User skill dirs | `~/.agents/skills`, `~/.cursor/skills` (+ reads `~/.claude/skills`, `~/.codex/skills` for compat) | `~/.agents/skills` | `~/.claude/skills` |
| Nested folders | recursive | per-directory `.agents/skills` walk | **one level only** |
| Symlinked skill dirs | not documented (verify in spike) | followed | followed |
| Invoke explicitly | `/name` | `$name` or `/skills` | `/name` |
| Frontmatter all three honor | `name`, `description` | `name`, `description` | `name`, `description` |

Design rules that follow from this:

- **Frontmatter is `name` + `description` only.** Everything else (source, layer, tuning) lives in folders and sidecar files, not metadata.
- **Installed skills are flat**, one folder per skill. The repo can be organized by layer, and `install.sh` flattens it with symlinks.
- **No `!cmd` injection, no `${CLAUDE_SKILL_DIR}`, no hooks.** These are Claude-only. Anything they would do is instead a plain instruction in `SKILL.md` that every agent can follow.
- **Skill names are globally unique** across layers, because they share one flat namespace once installed.

## 4. Two repos: framework and instance

```
whetstone/                         ← FRAMEWORK repo (shareable, upstream)
  README.md
  AGENTS.md                        ← rules for agents editing this repo (CLAUDE.md → symlink)
  install.sh                       ← link skills into the tools' skill dirs
  check.sh                         ← lint (see §9)
  skills/
    core/                          ← the framework's own meta-skills
      whetstone/                   ← entry point: list, status, new, import, update
        SKILL.md
        scripts/status.sh
        references/{new,import,update-upstream}.md
      skill-feedback/SKILL.md      ← capture feedback (auto-triggers)
      skill-tune/SKILL.md          ← fold feedback into the skill (deliberate)
    generic/                       ← reusable skills anyone can use
      pr-review/SKILL.md
      grill-me/{SKILL.md,SOURCE.md}  ← imported from a public skill

whetstone-acme/                    ← INSTANCE (a clone; remote "upstream" = whetstone)
  …everything above, never edited…
  skills/local/                    ← skills this instance owns
    jira-ticket/{SKILL.md,FEEDBACK.md}
    dev-container/{SKILL.md,scripts/…}
  skills/generic/grill-me/TUNING.md    ← instance-only overlay on an upstream skill
  skills/generic/grill-me/FEEDBACK.md  ← instance-only feedback log
```

You would run at least two instances: `whetstone-personal` and `whetstone-<company>`. Your own daily use happens in an instance too. The framework repo contains only what you'd hand to someone else.

### The one invariant

> **The framework repo never contains instance files** (`skills/local/`, `TUNING.md`, `FEEDBACK.md`), **and an instance never edits files that came from upstream.**

This invariant is what makes `git pull upstream main` conflict-free. Every file has exactly one owner:

| Path | Owner | How it changes |
|---|---|---|
| `skills/core/**`, `skills/generic/**/SKILL.md` (+ scripts, references) | framework | upstream commits only |
| `skills/generic/*/SOURCE.md` + vendored `SKILL.md` | third party, via framework | `whetstone update` re-import |
| `skills/**/TUNING.md` | instance | `skill-tune` |
| `skills/**/FEEDBACK.md` | instance | `skill-feedback` |
| `skills/local/**` | instance | anything, including direct `SKILL.md` edits |

"Am I in an instance?" means: does `skills/local/` exist? No config file is needed.

## 5. Anatomy of a skill

Every skill starts with the same two-line header, directly after the frontmatter:

```markdown
---
name: grill-me
description: Interrogate a plan or design with sharp questions before building. Use when the user says "grill me", asks to stress-test a plan, …
---

> **Tuning:** if `TUNING.md` exists in this skill's folder, read it first. It overrides anything below.
> **Feedback:** if the user corrects how this skill behaved, offer to log it with the `skill-feedback` skill.

# Grill me
…
```

This header does the job hooks or `!cmd` would do in Claude Code, and it works in all three tools. `whetstone new` and `whetstone import` add it, and `check.sh` enforces it.

Sidecar files (all optional):

| File | Purpose | Loaded by the agent at use-time? |
|---|---|---|
| `TUNING.md` | Instance overrides for a skill it doesn't own. Short: ≤ ~40 lines of do/don't. | Yes, via the header |
| `FEEDBACK.md` | Append-only log of raw feedback | No, only by `skill-tune` and status |
| `SOURCE.md` | Where an imported skill came from: URL, ref/commit, import date, local modifications (the header) | No |
| `scripts/`, `references/` | Standard skill resources | On demand, per the skill |

## 6. The feedback loop

```
 use skill ──► user corrects / says "feedback: …"
                     │
                     ▼
   skill-feedback: append entry to <skill>/FEEDBACK.md      (capture, cheap, no edits to the skill)
                     │
         … entries accumulate …
                     ▼
   skill-tune <skill>: read SKILL.md + TUNING.md + open entries
        → cluster → propose the smallest diff → user approves
        → apply:  owned skill  → edit SKILL.md
                  upstream/vendored skill in an instance → edit TUNING.md
        → mark entries applied (with commit) or declined (with reason) → git commit
                     │
                     ▼ (optional)
   promote: tuning that would help everyone → patch/PR to the framework's SKILL.md
            → once upstream has it, delete those lines from TUNING.md
```

### Capture (`skill-feedback`)

- It triggers when the user explicitly says "feedback on X", or when the header prompts an offer after a correction. The description is written to fire on phrases like "that skill asked too many questions" or "next time, don't …".
- It writes to `<skill-dir>/FEEDBACK.md`. The installed folder is a symlink, so the write lands in the instance repo.
- It never edits `SKILL.md` or `TUNING.md`. Capture is cheap and safe; changing behavior is a separate, deliberate step.

Entry format:

```markdown
## 2026-09-27 · open
- tool: cursor · context: reviewing PR in payments-api
- observed: asked 14 questions before giving any assessment
- wanted: at most ~5 questions per round, grouped by theme
```

Status is one of `open`, `applied <sha>`, or `declined: <reason>`.

### Tune (`skill-tune`)

- Only runs when you ask: `/skill-tune grill-me`, or "tune the skills with open feedback".
- Prefers patterns over anecdotes. A single entry becomes a proposal only if the user says so.
- Keeps `TUNING.md` short and imperative. If it grows past ~40 lines, the overlay has become a fork. Suggest *forking*: copy the skill to `skills/local/`, rename it, and own it.
- For skills it can't edit (upstream in an instance), it writes the overlay. If the overlay would contradict the base skill rather than refine it, it says so explicitly.
- Flags promotion candidates: tuning with nothing company-specific in it.

## 7. Entry point: `whetstone`

In Cursor and Claude Code it's `/whetstone`; in Codex, `$whetstone`. A single hub skill covers:

| Ask | Does |
|---|---|
| "whetstone" / "list my skills" / "status" | runs `scripts/status.sh`, then summarizes |
| "new skill …" | asks for layer (local vs generic) and name; writes the skeleton with header; hands authoring to the tool's own creator if it has one (Cursor `/create-skill`, Claude `skill-creator`) |
| "import <url or path>" | copies the skill folder, writes `SOURCE.md`, inserts the header, checks the name is unique |
| "update from upstream" | `git fetch upstream && git merge upstream/main`, re-run `install.sh`, list stale tunings |
| "update vendored skills" | re-fetches each `SOURCE.md`, shows a diff, and on approval re-imports and re-inserts the header. `TUNING.md` is untouched |

`status.sh` output (plain text, so any agent or a human can read it):

```
whetstone-acme  (instance · upstream whetstone@a1b2c3d, 2 commits behind)

LAYER    SKILL            SOURCE              TUNED      FEEDBACK
core     whetstone        framework           –          –
core     skill-feedback   framework           –          –
core     skill-tune       framework           –          –
generic  pr-review        framework           yes (12)   1 open
generic  grill-me         mattpocock/skills   yes (8) ⚠  3 open
local    jira-ticket      own                 –          2 open
local    dev-container    own                 –          –

⚠ grill-me: SKILL.md changed upstream after TUNING.md was last edited. Re-check the tuning.
Installed: ~/.agents/skills (7/7 linked) · ~/.claude/skills (7/7 linked)
```

The staleness check compares `git log -1 --format=%ct` of `SKILL.md` and `TUNING.md`. That's the only "evolve" support. Deciding what to do about it stays with the owner.

## 8. Install and sync (`install.sh`)

Idempotent, ~40 lines of bash:

1. For each `skills/*/*/SKILL.md`, symlink its folder to `<target>/<name>`.
2. Remove dangling symlinks in `<target>` that point into this repo (deleted or renamed skills).
3. Refuse to overwrite a non-symlink folder of the same name, and say so.

Targets:

- **Default: `~/.agents/skills`.** Covers Cursor and Codex.
- **`--claude`: also `~/.claude/skills`.** Needed for Claude Code. Cursor also reads this directory, so check in the spike whether Cursor shows duplicates. If it does, Claude users link only to `~/.claude/skills`; Cursor still reads it through compat.
- **`--project <dir>`:** links into `<dir>/.agents/skills` instead, for trying a skill in one repo.

Because skills are symlinked, edits made through tuning take effect immediately in every tool. Re-run `install.sh` only after adding, removing, or renaming a skill.

**Write access.** Feedback writes land outside the project you're working in. Cursor asks for approval, which is fine. Codex's default sandbox likely blocks it, so add the instance path to its writable roots in `~/.codex/config.toml` (verify in the spike). If a write is refused, `skill-feedback` prints the entry and the target path instead of losing it.

## 9. Guardrails (`check.sh`)

Runs in framework CI and on demand in an instance:

- Every `SKILL.md` has `name` and `description`, and `name` equals its folder name.
- Names are unique across all layers.
- The two-line header is present.
- *Framework repo only:* no `skills/local/`, `TUNING.md`, or `FEEDBACK.md`. This enforces the invariant.
- *Instance only:* no working-tree diffs to upstream-owned paths (`git diff upstream/main -- skills/core skills/generic ':!**/TUNING.md' ':!**/FEEDBACK.md'`).

## 10. Company-specific concerns

- **Connectors (Jira, GitHub).** A skill says "use the Jira MCP tools. If none are available, stop and tell the user to connect Jira in their tool's MCP settings." It never embeds tool-specific MCP config.
- **Company conventions** (container layout, ticket templates, project keys) live inside the relevant `skills/local/<skill>/references/`. Skills are self-contained, because relative paths outside a skill folder break once it's symlinked.
- **Hosting.** The company instance should be a company-hosted repo. The framework can be a personal public repo pulled as `upstream`, if company policy allows pulling from it. Otherwise mirror it internally.

## 11. Migration from GoShipit

1. Create `whetstone`: the core skills, `install.sh`, `check.sh`, `AGENTS.md`, and 1–2 generic skills (`pr-review`, `grill-me` imported).
2. Create `whetstone-personal` from it and use it in Cursor for a week or two. Tune from real feedback.
3. Create `whetstone-<company>` and add `local/` skills: container setup, Jira ticket.
4. Archive `go-ship-it`: point its README at the new repo. Keep it read-only as a reference for the phase docs.

## 12. Spike checklist (first hour of implementation)

- [ ] Cursor follows symlinked skill folders in `~/.agents/skills`.
- [ ] Cursor: same skill linked in both `~/.agents/skills` and `~/.claude/skills` → duplicate entries?
- [ ] All three tools actually read `TUNING.md` when the header tells them to. Test with an overlay that changes visible output.
- [ ] `skill-feedback` can write through the symlink in Cursor (approval flow) and Codex (sandbox).
- [ ] `skill-feedback` triggers on a natural correction without being named.

## 13. Open questions

1. **Name.** `whetstone` (entry `/whetstone`)? Alternatives: `skillsmith`, `tack`, `kit`. Short matters, because you'll type it a lot.
2. **Is Claude Code a real target** or just "nice to have"? That decides whether `--claude` is on by default.
3. **Framework visibility.** Is it public on your GitHub, or private and mirrored into the company?
