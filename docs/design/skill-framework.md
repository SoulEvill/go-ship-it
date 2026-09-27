# Design: meta-skill-loop, and how it fits with shared skills and a personal hub

Status: proposal v3 · 2026-09-28 (supersedes v1 and v2)
Name: **meta-skill-loop** (see §8)

## 1. The three things you want

1. **A loop.** Give feedback on any skill while using it, store it in one consistent way, and later refine the skill from it.
2. **A container.** One entry point that lists the skills you care about, with their status, and routes to them. Today that's your "Wendell" skill at work.
3. **Sharing.** Hand individual skills to teammates, keep them updated, and let their improvements flow back.

These are three different jobs with different audiences and visibility, so they become **three separate layers**. Each works on its own and they compose.

## 2. Use cases → where each lives

| # | Use case | Who | Layer |
|---|---|---|---|
| U1 | Mid-use: "I have feedback on this skill," with evidence captured | anyone | **loop** |
| U2 | "Refine pr-review": turn accumulated feedback into an approved edit | anyone | **loop** |
| U3 | "Which skills have open feedback / changed / have updates?" | anyone | **loop** (plain status) |
| U4 | Pull a new version of a shared skill I've refined locally, without losing my changes | anyone | **loop** (merge) + **pack** (source) |
| U5 | Send my improvement back so teammates get it | anyone | **loop** (contribute) → **pack** (PR) |
| U6 | Share `setup-workspace` with my team; they install just that skill | team | **pack** |
| U7 | New teammate gets the team's skills in all their tools | team | **pack** (+ loop optional) |
| U8 | "/wendell": my curated menu of the skills I use, grouped my way | me | **hub** |
| U9 | "What am I working on?" (workspace progress) | me | a **domain skill** listed by the hub; not management at all |
| U10 | Use a public skill (grill-me) and tailor it to me | me | **loop** (manages it in place) |
| U11 | Improve meta-skill-loop itself from my usage | me → public | **loop** (feedback on its own skills → contribute) |

What falls out:

- **The loop is generic plumbing.** It cares that a skill exists, where it lives, where it came from, and what feedback it has. It never cares what a skill *does*. That's why it can be public.
- **Packs are the sharing unit.** They're plain git repos of skills. The loop doesn't host them, and the installer already exists.
- **The hub is personal taste.** "What I care about and how I group it" differs per person, so it's a skill *you* own, in *your* pack. It can show the loop's status, but the loop doesn't depend on it.
- **Generic skills like pr-review don't belong in the loop repo.** They go in a pack.

## 3. The layers

```
┌───────────────────────────────────────────────────────────────────┐
│  HUB (personal)         /wendell   → your menu, your grouping      │
│    lives in: your personal pack (private)                          │
│    reads: meta-skill-loop status (optional)                         │
├───────────────────────────────────────────────────────────────────┤
│  PACKS (sharing)        git repos of skills, installed per skill   │
│    team pack (private) · personal pack (private) · public packs    │
│    installed with: npx skills add <repo> --skill <name> --copy -g  │
├───────────────────────────────────────────────────────────────────┤
│  LOOP (public)          meta-skill-loop                            │
│    feedback · refine · status · update-merge · contribute          │
│    data: ~/.meta-skill-loop/ (local only)                          │
└───────────────────────────────────────────────────────────────────┘
      skills themselves: wherever tools load them (~/.cursor/skills, ~/.agents/skills, …)
```

### 3.1 Loop: `meta-skill-loop` (public GitHub repo)

It contains only the loop. It ships no generic skills.

```
meta-skill-loop/
  README.md · AGENTS.md · install.sh
  skills/
    meta-skill-loop/        hub for the loop itself: status, add, update, contribute
      SKILL.md
      scripts/msl.sh        mechanical work: scan, add, snapshot, status, merge (bash)
    meta-skill-feedback/    capture with evidence
    meta-skill-refine/      feedback → approved edit
```

**Its data** lives in `~/.meta-skill-loop/` on your machine. This directory is **not** where skills live, and it isn't something you share:

```
~/.meta-skill-loop/
  skills/<name>/
    skill.yaml     where it lives, where it came from (pack repo + path + commit), ownership
    feedback.md    evidence log
    changes.md     every local change, each tied to the feedback ids that motivated it
    base/          the upstream version you last took (pristine)
    current/       the version you intend to have (upstream + your refinements)
```

It is a **local** git repo, used only for history and undo ("what did refine change last week?"). It holds company evidence, so it is never pushed publicly. Pushing it to a private remote for backup is optional.

### 3.2 Packs: the sharing format

- **One repo per audience, not one repo per skill.** A pack is `skills/<name>/SKILL.md` folders plus a README. Per-skill repos multiply overhead (access, CI, releases) without adding anything; git history per path already versions each skill.
  - `team-skills` (private, company): setup-workspace, pr-review, jira-ticket, …
  - `wendell-skills` (private, yours): the `wendell` hub, workspace-status, personal helpers
  - public packs (yours or others'): anything genuinely generic, if you ever want to publish it
- **Install individual skills** with the open-source `skills` CLI. It supports private git repos, selecting single skills, Cursor, Codex, and Claude Code, and a copy mode: `npx skills add git@github.com:acme/team-skills.git --skill setup-workspace --copy -g`. Use `--copy` because Cursor's symlink discovery is unreliable. We don't build an installer.
- **Flat names.** Claude Code only discovers skills one level deep and all tools share a flat namespace. Wendell's "sub-skills" are therefore separate flat skills (`wendell-workspace`, `setup-workspace`), and the `wendell` skill routes to them.
- **Improvements flow back as PRs** to the pack repo. The loop's `contribute` step prepares them (§5).

### 3.3 Hub: your `/wendell` (personal pack)

It's just a skill. Its `SKILL.md` holds your curated, grouped list of the skills you use and when, and routes requests to them. For a health column it runs `meta-skill-loop status` if the loop is installed. It lists skills by name, so it doesn't care which pack they came from. Teammates can copy the pattern, but each person owns their own hub.

The loop provides a **plain** status view on its own (`/meta-skill-loop`), so it's useful without a hub. Your hub is the opinionated view on top.

## 4. Updating in place, and resolving conflicts on the next pull

Refinements edit the skill **in place**, in the folder the tool actually loads. Every managed skill has three versions:

- **base** is the pristine upstream version you last took (`~/.meta-skill-loop/skills/<n>/base/`).
- **current** is what you intend: base plus your refinements (`current/`, refreshed on every refine).
- **live** is what's on disk now.

`msl.sh status` compares them:

| live vs. current | live vs. base | Meaning | Action |
|---|---|---|---|
| same | – | clean | none |
| differs | same as base | an update re-installed the old upstream and wiped your changes | restore `current` |
| differs | differs, source has a newer commit | **upstream update landed** | merge (below) |
| differs | differs, no newer upstream | you (or a creator tool) edited it by hand | accept as new `current` (ask) |

**Merge** runs through `/meta-skill-loop update pr-review`. It also works after the fact if you ran `npx skills update` yourself, because `current/` is already saved:

1. Three-way merge: `git merge-file current base new-upstream`. Non-overlapping edits merge automatically.
2. For conflicts, the agent resolves them **by intent, not by text**. `changes.md` says *why* each local change exists (feedback ids), so the agent re-applies the intent to the new wording. It also flags local changes the new upstream already covers and proposes dropping them, marking those feedback entries `resolved-upstream`.
3. You approve the result. Then `base ← new upstream` and `current ← merged`, and the loop writes it in place.

**Preventing repeat conflicts.** After a refine on a skill that comes from a pack, the loop offers `contribute`: a branch and PR to the pack repo. Once it merges, your local diff from base is empty, and future pulls are conflict-free. Local divergence is meant to be temporary for shared skills.

For skills you own (no upstream), there's no merge; `current` just tracks your edits.

## 5. Feedback, refine, contribute

**Capture** (`meta-skill-feedback`, always installed, triggers on "feedback on this skill…", "next time don't…").

1. It identifies the skill. If the skill isn't managed yet, it runs `add`, which records location and source and snapshots base/current.
2. It appends an entry with evidence:

```markdown
## fb-0007 · 2026-09-28 14:02 · open · annoying
- skill: pr-review @ sha256:3f9a1c…      (hash of the live SKILL.md at the time)
- where: cursor · project payments-api
- asked: "review PR 482"
- observed: 30 style nits, missed the unhandled retry error
- expected: correctness first; style only if asked
- user said: "stop with the nits, what's actually broken?"
- evidence: first 10 lines of the review output
```

**Nudge.** At `add`, the loop inserts one line after a skill's frontmatter: *"If the user gives feedback on how this skill behaved, log it with `meta-skill-feedback`."* That line is a local change like any other (recorded in `changes.md`, preserved by merge). Capture still works without it.

**Refine** (`meta-skill-refine`, only when asked).

1. It reads the live skill and its open feedback, then groups the feedback into themes with entry ids. A single entry changes nothing unless you say so.
2. It proposes the smallest diff and applies it in place after you approve.
3. It updates `current/` and `changes.md` and marks entries `applied`.

**Contribute** (part of `meta-skill-loop`). Your local change becomes a PR (or an issue) to the skill's **own source repo**, never anywhere else. The evidence is redacted and summarized; raw feedback never leaves your machine. Feedback about the loop's own skills goes to the public loop repo the same way, redacted.

## 6. Install

```sh
git clone https://github.com/<you>/meta-skill-loop && meta-skill-loop/install.sh
# or: npx skills add <you>/meta-skill-loop --copy -g
```

The loop's own skills are installed by copy into `~/.agents/skills` (Cursor and Codex). If you use Claude Code, they're also copied into `~/.claude/skills`. After installing, say "meta-skill-loop add" to bring in the skills you already have; the scan finds unmanaged skills in all tool directories.

Codex's default sandbox likely blocks writes to `~/.meta-skill-loop`; `install.sh` prints the writable-root line to add. Cursor asks for approval.

## 7. Your setup, concretely

| Today | Becomes |
|---|---|
| `wendell` skill (menu + sub-skills) | `wendell-skills` private pack: `wendell` (hub) + `wendell-workspace` + personal helpers |
| Skills worth sharing (pr-review, setup-workspace) | move to a `team-skills` private pack; teammates `npx skills add … --skill …` |
| Your own copies of those | installed from `team-skills` like everyone else's; refined in place by the loop; improvements go back as PRs |
| Feedback, tuning history | `~/.meta-skill-loop/` on your machine |
| GoShipit | archived with a README pointer; its "lessons to promote" rule became refine + contribute |

## 8. Name: "meta-skill-loop" over "skill-meta-loop"

- **It parses as a known term plus the thing.** "Meta-skill" is an established idea (a skill about skills), and "loop" is what it runs: *the meta-skill loop*. "Skill meta loop" stacks two modifiers, and "meta loop" isn't a term people recognize.
- **It groups well when typed.** All three core skills share the `meta-skill-` prefix (`meta-skill-loop`, `meta-skill-feedback`, `meta-skill-refine`), so typing `/meta-skill` lists exactly them. A name starting with `skill` would collide with Codex's built-in `/skills`, `skill-creator`, and every other `skill-*` tool in autocomplete.
- **The repo name matches the entry point** (`meta-skill-loop` → `/meta-skill-loop`), so there's one thing to remember.

## 9. Build plan

1. **Spike (Cursor first).**
   - [ ] `meta-skill-feedback` triggers on a natural correction.
   - [ ] Writing to `~/.meta-skill-loop` from another project works.
   - [ ] `npx skills add … --copy -g` puts skills where Cursor loads them. Does `update` overwrite local edits? (Assume yes; §4 handles it.)
   - [ ] Duplicate listing if a skill is in both `~/.agents/skills` and `~/.claude/skills`.
2. **v0.1 loop.** `msl.sh` (`scan`, `add`, `snapshot`, `status`) plus the three skills. Dogfood on your current Cursor skills.
3. **v0.2 loop.** `update` (three-way merge) and `contribute` (branch/PR with redaction).
4. **Packs.** Split Wendell into `wendell-skills` and `team-skills`, and share one skill with a teammate end-to-end.
