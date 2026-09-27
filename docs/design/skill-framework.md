# Design: metaloop, a management layer that tunes your agent skills over time

Status: proposal v2 · 2026-09-28 (supersedes v1 of 2026-09-27)
Working name: **metaloop** (see §12).

## 1. What it is

A small, tool-agnostic **management layer for agent skills**. You install it once. Then:

1. **Add**: "add this skill to metaloop." It works for skills you already have, wherever they live, or new ones from any skill creator. metaloop creates a folder for the skill in your workspace and records where the skill lives.
2. **Capture**: mid-use, you say "I have feedback on this." The agent writes a feedback entry with evidence into that skill's folder.
3. **Refine**: when you're ready, "refine grill-me." The agent reads the accumulated feedback, proposes the smallest change that addresses it, and applies it once you approve.
4. **See**: "metaloop status" lists every managed skill, its open feedback, and anything that needs attention.

metaloop ships with its own skills, which are managed and refined the same way. When a lesson applies to everyone, it goes back to the public repo.

It is **not** a skill authoring tool. Cursor `/create-skill`, Anthropic's `skill-creator`, or a text editor still create skills, and metaloop manages whatever they produce. It is also not a package manager or a runtime.

## 2. Principles

- **Tool-agnostic, Cursor first.** It relies only on the open `SKILL.md` standard (`name` + `description`), plain files, and bash. No hooks, plugin manifests, or tool-specific frontmatter.
- **Skills stay where they live.** metaloop never moves a skill and never requires symlinks (see §3).
- **Management data lives in a user workspace, not a repo you clone:** `~/.metaloop/`.
- **Scripts do the mechanical work; the agent does the judgment.** Scripts handle paths, hashes, snapshots, and status. The agent writes feedback, clusters it, and proposes edits.
- **Capture is cheap; changing a skill is deliberate.** Nothing edits a skill without the user approving a diff.

## 3. Verified constraints (2026-09-27/28)

| | Cursor | Codex | Claude Code |
|---|---|---|---|
| User skill dirs | `~/.agents/skills`, `~/.cursor/skills` (+ `~/.claude/skills`, `~/.codex/skills` for compat) | `~/.agents/skills` | `~/.claude/skills` |
| Project skill dirs | `.agents/skills`, `.cursor/skills` (recursive) | `.agents/skills` (cwd → repo root) | `.claude/skills` (one level) |
| Symlinked skill folders | **unreliable**: staff-confirmed bug Feb 2026; an Aug 2026 post suggests discovery works now; unconfirmed | followed (Windows issues reported) | followed |
| Invoke | `/name` | `$name`, `/skills` | `/name` |

Consequences:

- Symlinks cannot be required, so managed skills stay in place and metaloop's own skills are installed by **copy**.
- The frontmatter all three tools agree on is `name` and `description`. metaloop keeps its metadata out of `SKILL.md`.
- Skill names share one flat namespace per tool, so metaloop's own skills are prefixed `metaloop-`.

## 4. Layout

### Framework repo (public GitHub)

```
metaloop/
  README.md
  AGENTS.md                      ← rules for agents editing this repo (CLAUDE.md → symlink)
  install.sh                     ← creates the workspace, copies core skills into tool dirs
  skills/                        ← core skills (installed for every user)
    metaloop/                    ← hub: status, add, remove, sync, contribute
      SKILL.md
      scripts/ml.sh              ← all mechanical operations (bash)
      references/{add,sync,contribute}.md
    metaloop-feedback/SKILL.md   ← capture with evidence
    metaloop-refine/SKILL.md     ← review feedback → propose → apply
  catalog/                       ← optional generic skills (pr-review, grill-me, …), added on request
```

### User workspace (per machine; a private git repo you can push anywhere)

```
~/.metaloop/
  config.yaml                    ← framework path, install targets, tools in use
  framework/                     ← clone of the public repo (git-ignored by the workspace)
  skills/
    <name>/                      ← one folder per managed skill, created by "add"
      skill.yaml                 ← where it lives, ownership, scope, source (see §5)
      feedback.md                ← evidence log (see §6)
      tuning.md                  ← overlay, only for skills you don't own (see §5)
      snapshot/                  ← copy of the skill as of add / last refine
      proposals/                 ← refinements that couldn't be applied in place
```

`snapshot/` plus workspace git gives every skill a history, even when the skill lives in a folder that isn't version-controlled, like `~/.cursor/skills`. It also lets metaloop detect when a skill changed *outside* metaloop, for example through a creator tool or an upstream update.

## 5. Adding a skill, and who owns it

Say "add grill-me to metaloop" or "add ~/.cursor/skills/jira-ticket". To find unmanaged skills, `ml.sh scan` lists every skill in known tool and project dirs that isn't managed yet. Adding then:

1. Resolves the skill's folder and reads its `name` and `description`.
2. Asks two questions, pre-filled from what it can detect:
   - **Ownership.** `own` means you edit this skill directly. `upstream` means it comes from somewhere that will overwrite it (a public skill, a plugin, a teammate's repo, metaloop itself).
   - **Scope.** `generic` means it's safe to share publicly. `company` means it must never leave your machine or company.
3. Writes `skill.yaml`, takes a `snapshot/`, and inserts the **header** (below).
4. Commits the workspace.

```yaml
# ~/.metaloop/skills/grill-me/skill.yaml
name: grill-me
path: ~/.cursor/skills/grill-me        # where the skill actually lives (left in place)
ownership: upstream                    # own | upstream
scope: generic                         # generic | company
source: https://github.com/<owner>/<repo>/tree/<ref>/grill-me   # upstream only
added: 2026-09-28
```

### The header (the portable "feedback hook")

Inserted directly after the frontmatter:

```markdown
> **metaloop:** before starting, read `~/.metaloop/skills/grill-me/tuning.md` if it exists; it overrides anything below.
> If the user gives feedback on how this skill behaved, log it with `metaloop-feedback`.
```

- **Own** skills get only the second line; refinement edits them directly, so they need no overlay.
- **Upstream** skills get both lines. Refinement writes to `tuning.md` in the workspace, which updates never touch. Only the two-line header can be overwritten, and `sync` detects and restores it.
- Feedback capture does **not** depend on the header. `metaloop-feedback` is always installed, and its description triggers on "feedback on this skill" for any skill, managed or not. The header just makes the agent *offer* to capture after a correction.

## 6. Capture: `metaloop-feedback`

Triggers on explicit feedback ("feedback on this skill: …", "log that", "next time don't …") or when a skill's header prompts an offer after a correction.

1. Identify the skill. The agent knows which skill it loaded; if it's ambiguous, it asks. If the skill isn't managed yet, it offers to add it first.
2. Gather the evidence and append an entry to `~/.metaloop/skills/<name>/feedback.md`:

```markdown
## fb-0007 · 2026-09-28 14:02 · open · annoying
- skill: grill-me @ sha256:3f9a1c… (hash of SKILL.md when this happened)
- where: cursor · project payments-api
- asked: "grill me on the retry design"
- observed: asked 14 questions in one message before any assessment
- expected: ≤ 5 questions per round, grouped by theme, with a short read of the design first
- user said: "way too many questions, I just want the big risks first"
- evidence: first message of the grill (trimmed): "1. What is the … 14. How will …"
```

3. Commit the workspace. It never edits the skill.

Severity is one of `nit`, `annoying`, or `wrong`. The skill hash lets refinement tell whether feedback predates a later change. If the tool blocks writing to `~/.metaloop` (Codex's default sandbox likely does), the agent prints the entry and the path instead. See §9.

## 7. Refine: `metaloop-refine`

Only runs when asked: "refine grill-me", or "refine everything with open feedback".

1. Read the skill (live), `tuning.md`, and all `open` feedback entries. Flag entries whose skill hash is stale.
2. Group entries by theme and show a short summary: each theme, the entry ids behind it, and how strong the pattern is. A single entry doesn't change a skill unless the user says so.
3. Propose the smallest diff per theme, where it depends on ownership:
   - **own**: edit `SKILL.md` (or its references) in place.
   - **upstream**: edit `tuning.md`. Keep it short and imperative, about 40 lines at most. If it grows past that or contradicts the base skill, suggest **forking**: copy the skill to a new name and mark it `own`.
   - Anything that can't be applied in place (a teammate's repo you shouldn't edit) goes to `proposals/<date>.md` as a patch you can take to that repo.
4. After approval: apply, mark entries `applied <workspace-commit>` or `declined: <reason>`, refresh `snapshot/`, and commit.
5. If a change isn't company-specific and the skill is `generic`, offer `contribute` (§8).

## 8. The hub: `metaloop` (`/metaloop` in Cursor/Claude, `$metaloop` in Codex)

| Ask | What happens |
|---|---|
| "metaloop" / "status" | `ml.sh status` → table below, then a one-paragraph summary and suggested next step |
| "add …" / "what skills aren't managed?" | §5 / `ml.sh scan` |
| "remove …" | removes the header and archives the workspace folder |
| "sync" | pulls framework updates, re-copies core skills, restores missing headers, reports skills changed outside metaloop |
| "contribute …" | turns a generic refinement or framework-skill feedback into a GitHub issue or PR on the source. **Company scope is always blocked, and evidence is redacted before anything leaves the machine.** |

```
metaloop · workspace ~/.metaloop · framework v0.3.1 (1 update available)

SKILL              OWNER     SCOPE    LIVES IN              FEEDBACK   NOTES
metaloop           upstream  generic  ~/.agents/skills      –
metaloop-feedback  upstream  generic  ~/.agents/skills      1 open
metaloop-refine    upstream  generic  ~/.agents/skills      –
grill-me           upstream  generic  ~/.cursor/skills      3 open     tuned (8 lines)
jira-ticket        own       company  ~/.cursor/skills      2 open
dev-container      own       company  work-repo/.cursor/…   –          ⚠ changed outside metaloop
pr-review          upstream  generic  ~/.agents/skills      –          ⚠ header missing (updated?)

Unmanaged skills found: 4 → "metaloop add" to review
```

## 9. Install and updates

```sh
git clone https://github.com/<you>/metaloop ~/.metaloop/framework
~/.metaloop/framework/install.sh            # detects Cursor/Codex/Claude; asks if unsure
```

`install.sh` does four things:

1. Creates the workspace: `git init`, `config.yaml`, a `.gitignore` for `framework/`.
2. **Copies** the core skills into `~/.agents/skills`, which Cursor and Codex both read. If Claude Code is in use, it also copies them into `~/.claude/skills`.
3. Registers the core skills as `upstream`/`generic`, so feedback on metaloop itself works from day one.
4. Prints the next step: "Say *metaloop add* in your agent to bring in your existing skills."

Updates: "metaloop sync" (or re-running `install.sh`) runs `git pull` in `framework/`, re-copies core skills, and runs the header and drift checks. Your `tuning.md` overlays survive every update. If an update conflicts with your tuning, sync flags it; resolving it is your call, with `metaloop-refine` to help.

Write access: agents write to `~/.metaloop`, outside your project. Cursor asks for approval. Codex needs `~/.metaloop` added as a writable root in `~/.codex/config.toml`; `install.sh` prints the exact line.

## 10. Where things end up

| You want… | It lives… |
|---|---|
| framework + core skills | public GitHub repo → cloned to `~/.metaloop/framework`, copied into tool dirs |
| generic skills from the framework | `catalog/` → copied into a tool dir on "add pr-review from the catalog" (`upstream`) |
| public third-party skills (grill-me) | wherever you installed them; managed as `upstream` with overlay |
| your company skills | wherever you keep them (`~/.cursor/skills`, a team repo); managed as `own` + `company` scope |
| all feedback, tuning, and history | `~/.metaloop/skills/*`, a private git repo you can push anywhere |

Sharing company skills with teammates is out of scope for v1. The skills live in a team repo like any other; each person's metaloop manages their own copy of them.

## 11. What happens to GoShipit

GoShipit (a ~4.9k-line lifecycle CLI) gets archived with a README pointer to metaloop. The one idea carried over is its dogfood rule that every lesson maps to *update a skill / update docs / add a check / defer*, which is what refinement does. Its issue-phase docs could later return as a catalog skill.

## 12. Name

The name should say "meta" and "loop" without "feedback", since the loop covers more than feedback.

| Name | Why | Invoke |
|---|---|---|
| **metaloop** (recommended) | says exactly what it is; easy to search; prefix `metaloop-` for core skills | `/metaloop` |
| strangeloop | Hofstadter's self-referential loop: it refines its own skills too | `/strangeloop` |
| ouroboros | loop that feeds itself; memorable, long to type | `/ouroboros` |
| recurse | short, meta, verb-like | `/recurse` |

Check GitHub for name collisions before creating the repo.

## 13. Build plan

1. **Spike (first session, in Cursor)**
   - [ ] The header reliably makes the agent read `tuning.md` before acting. Test with an overlay that changes visible output.
   - [ ] `metaloop-feedback` triggers on a natural correction without being named.
   - [ ] Writing to `~/.metaloop` from a Cursor session in another project works (approval flow). Codex: writable root.
   - [ ] The same skill in `~/.agents/skills` and `~/.claude/skills` → does Cursor show duplicates? This decides the Claude install target.
2. **v0.1:** `install.sh`, `ml.sh` (`status`, `scan`, `add`, `snapshot`, `check`), the three core skills.
3. **Dogfood:** manage your existing Cursor skills for 1–2 weeks and refine from real feedback, including metaloop's own skills.
4. **v0.2:** `sync`, `contribute` (with redaction), `catalog/` with 1–2 generic skills.
