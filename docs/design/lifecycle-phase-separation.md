# Lifecycle Phase Separation — Research & Design Record

**Issue:** `go-ship-it/issue-005` — "Redesign lifecycle phase separation (research-first, per-phase overridable, explicit close-out gates)"
**Phase:** propose (research done; architecture proposed; design SIGNED OFF 2026-07-06 — next: TDD implementation plan)
**Date:** 2026-07-06
**Status:** Design fully signed off by the user, including all four §8 sub-decisions (see §8 resolutions). NOT yet implemented. This document is the durable handoff so a fresh session can pick up cleanly.

---

## 0. TL;DR for the next session

We are redesigning GoShipit's issue lifecycle so each phase is a **cleanly separated, independently overridable unit**, and the **inner build loop (TDD/debug) is a pluggable axis inside `implement`**. We surveyed 19 coding-workflow frameworks (all four required: Superpowers, GSD, GSD-2, No Mistakes) and distilled 9 convergent patterns (P1–P9, §4). We then settled the big design forks with the user (§6) and produced a v1 architecture proposal (§7).

**What's decided:** enum + per-phase reference docs (not a skill-per-phase explosion, not a heavy supervisor); TDD as the entry contract to `implement`; the fast path expressed as *skippable phases within the one enum* (not a parallel pipeline); **close-out split out of `work-issue` into its own skill** (3 → 4 skills).

**What's next (§9):** (1) turn this into a proper design doc / spec and get explicit sign-off; (2) write a bite-sized TDD implementation plan; (3) implement in this worktree; (4) validate end-to-end with a dogfood run. **Hard gate: no implementation code until the design + plan are approved.**

**Where the live evidence is:** GoShipit run notes at `state/repos/go-ship-it/issues/execution/issue-005/notes.md` (all research + the v1 proposal, recorded via `append-note`). That path is git-ignored/local; THIS doc (committed on the issue branch) is the durable record.

---

## 1. Problem & goal (from the issue)

GoShipit's lifecycle is effectively a **monolith**: the `work-issue` skill bundles investigate → propose → implement → review → write-PR → push → archive into one flow, and phases are only loosely modeled (a free-form `set-phase` string). You **cannot change one phase's behavior without touching the whole thing**. The concrete motivating pain: *"I want to change only how the PR is written — its template/structure — and there's no easy, isolated place to do that."*

The trigger was a ParaWave dogfood run (`parawave/issue-001`) where close-out bundled "commit + local PR + archive" into one step, so an **irreversible archive happened before the user reviewed the local PR** (archive is terminal — there is no `reopen`/`unarchive`).

**Two separations wanted:**
1. **The problem-resolution meta-flow** (the spine): `investigate → propose → implement → review → write-PR → push → archive`. Each an addressable unit with a clear contract (inputs, outputs, evidence, gate). Changing one must not require editing the others.
2. **The inner solution-building loop** inside `implement` (TDD red→green→refactor, systematic debugging, spike): a different axis, pluggable/optional per issue, not hard-wired.

**Design principles the issue asks for:** separation of concerns, per-phase overridability, explicit human gates at irreversible steps (publish, archive), research-grounded choices.

## 2. Current GoShipit state (what exists today)

- **Phase is a free-form string.** `set-phase` (`src/go_ship_it/cli.py`) takes an unvalidated `phase` arg; `state.py` stores it as `str`. There is no enum, no per-phase contract.
- **The only "state machine"** is a hard-coded next-command ladder in `cli.py` (~line 751): `setup/investigate → propose → implement → test → cleanup`.
- **The `work-issue` skill is the monolith** — it holds investigate…review…PR…archive guidance in one file (`skills/work-issue/SKILL.md`).
- **Close-out is smeared across two skills:** `work-issue` documents `prepare-pr`/`publish-pr`; `manage-issues` documents `cleanup-issue` (the archive move). No single owner.
- **CLI seams already fairly isolated:** `pull_request.py` (~398 LOC) owns `prepare-pr`/`publish-pr` (publish gated by `auto_publish`/`--approved`); `cleanup-issue` owns execution→todo|archive (archive terminal; no reopen).
- **Skill surface is intentionally 3** (`using-go-ship-it`, `manage-issues`, `work-issue`) — see §5; `docs/dogfood/issue-014-skill-surface-consolidation.md` deliberately consolidated from 7 phase-skills down to 3.
- **Phase is already on disk** (`run.yaml`) — GoShipit already has GSD-2's "state-derived phase" property, just without the enum/contract.

**Files most relevant to the change:** `src/go_ship_it/state.py` (phase field), `src/go_ship_it/cli.py` (`set-phase`, the ~L751 ladder, `verify-run`, `status`), `src/go_ship_it/pull_request.py` (prepare/publish), `src/go_ship_it/verify.py`, `skills/work-issue/`, `skills/manage-issues/`, `skills/using-go-ship-it/`, `docs/maintainers.md` (the design-philosophy gate).

---

## 3. Research: the frameworks we studied (19 sources)

We covered the four required sources (Superpowers, GSD, GSD-2, No Mistakes) plus 15 more, well beyond the issue's "at least five." Two required ones needed real detective work:
- **"No Mistakes" → `no-mistakes` by Kun Chen.** The requester's "MatterLA engineer" was **"Meta L8 engineer"** misheard. Kun Chen is ex-Meta L8 / ex-Atlassian (Rovo Dev).
- **GSD / GSD-2 lineage.** GSD = "Get Shit Done" (Lex Christopherson / TÂCHES → Open GSD). GSD-2 = the TypeScript rewrite on the "Pi" SDK (→ GSD Pi). Unrelated to Superpowers.

### 3a. Local reference plugins (read firsthand from the installed environment)

**Superpowers 6.1.1** — the richest 1:1 phase reference. Model = **one skill per phase, composed by explicit handoff**. Skills and their phase mapping:

| Superpowers skill | Maps to |
|---|---|
| `brainstorming` | design/propose (HARD-GATE: no impl before approved spec; terminal = invoke writing-plans) |
| `writing-plans` | propose artifact (plan doc w/ per-task `Consumes`/`Produces` interface contracts) |
| `executing-plans` / `subagent-driven-development` | implement (SDD = fresh subagent per task + two-stage review) |
| `test-driven-development` | inner loop (red-green-refactor; "iron law: no production code without a failing test first") |
| `systematic-debugging` | alternate inner loop |
| `requesting-code-review` / `receiving-code-review` | review |
| `verification-before-completion` | review gate ("NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE") |
| `finishing-a-development-branch` | close-out (verify tests → present EXACTLY 4 options merge/PR/keep/discard → typed "discard" confirm) |
| `using-git-worktrees` | isolation |
| `writing-skills` | META: how to author the skill interface itself |

**What to learn:** single-responsibility phase units; composition by explicit named handoff + artifact-as-contract; inner loop as a separate pluggable axis (referenced, not hard-wired); structured-options + typed confirmation at irreversible steps; the evidence-before-claims gate.

**`writing-skills` (meta-rules that govern how we write the per-phase docs/skills):**
- **description = WHEN-TO-USE only**, never a workflow summary (a summarizing description makes agents shortcut and skip the skill body — empirically observed).
- **"Match the Form to the Failure":** discipline-violation → prohibition + rationalization table + red flags; wrong-shaped output → positive recipe/contract; omitted element → structural REQUIRED slot; conditional behavior → conditional keyed to an observable predicate.

**`feature-dev` plugin — phase-specialized AGENTS.** One `/feature-dev` command, 7 inline phases (Discovery → Exploration → Clarify → Architecture → Implementation → Quality Review → Summary). Each phase fans out to specialized parallel subagents (code-explorer ×2-3; code-architect ×2-3 with minimal|clean|pragmatic focuses; code-reviewer ×3 with simplicity|bugs|conventions focuses). Hard gate: "DO NOT START [impl] WITHOUT USER APPROVAL." **What to learn:** the seam can be at the *agent* level; a phase can spawn lens-diverse reviewers.

**`code-review` plugin — a phase FULLY EXTRACTED as its own invokable unit.** `/code-review <PR>`: eligibility (Haiku) → collect CLAUDE.md paths → summarize → 5 lens-diverse reviewers (CLAUDE.md adherence | shallow bugs | git-blame history | prior-PR comments | code-comment compliance) → per-issue confidence score 0-100 (Haiku) → filter <80 → re-check eligibility → post. **What to learn:** the exact shape of an independently-overridable single phase — swap the whole internal pipeline + numeric gate without touching any other phase. This is the overridability target.

### 3b. The required externals

**No Mistakes — `no-mistakes` by Kun Chen** (https://github.com/kunchenguid/no-mistakes, docs https://kunchenguid.github.io/no-mistakes/). MIT, ~1.3k stars. A **post-development git-push GATE**, not a coding tool. You run `git push no-mistakes <branch>` → it lands in a **local bare "gate" repo** between your repo and the real remote → a daemon spins a **disposable worktree** and runs a fixed pipeline; the branch is forwarded upstream + a clean PR opened **only after every stage is green**. Also exposed as a Claude Code skill `/no-mistakes`.
- **Pipeline (fixed, sequential):** `intent → rebase → review → test → document → lint → push → pr → ci`. `intent` captures the agent's goal/tradeoffs; `review` runs in a **fresh context window** (self-review-bias avoidance); `test` forces **E2E evidence** (screenshots) not just unit tests; `push`/`pr` only after green; `ci` is babysat + auto-fixed.
- **Gating:** findings typed `auto-fix | no-op | ask-user`. Pipeline pauses only when blocking findings remain OR any finding is `ask-user` (the human gate). A **force-push data-loss guard** refuses pushes that would discard commits the run didn't incorporate.
- **What to learn:** (1) review in a clean room = a fresh agent with only diff+intent; (2) **intent as a first-class artifact** the review is measured against; (3) classify findings, only `ask-user` stops the human; (4) single deliberate gate, "nothing ships until green," + data-loss guard; (5) E2E evidence + bounded re-review loop as the definition of "done."

**GSD ("Get Shit Done", TÂCHES → Open GSD `gsd-core`)** (https://github.com/open-gsd/gsd-core, archived original https://github.com/glittercowboy/get-shit-done). Markdown/prompt-based Claude Code framework. Five-step loop, **one slash command per phase**: `discuss` (/gsd-discuss-phase → CONTEXT.md) → `plan` (/gsd-plan-phase → atomic XML task plans) → `execute` (/gsd-execute-phase, parallel waves, fresh 200k ctx per executor) → `verify` (/gsd-verify-work, manual UAT yes/no) → `ship` (/gsd-ship, create PR + archive phase).
- **Separation** = command-per-phase + per-phase orchestrator subagents in fresh contexts + durable state files (SPEC.md/CONTEXT.md/STATE.md/.plans/).
- **Inner loop NOT hard-wired TDD** (explicitly "TDD is Superpowers' focus"); correctness enforced by Verify UAT + `/gsd:debug`.
- **Gates:** roadmap approval; **`SPEC.md == FINALIZED`** (code mechanically blocked until the propose artifact is approved); Verify yes/no; quality gates detect schema drift + scope reduction.
- **Fast path:** `/gsd-fast` inlines trivial tasks + **skips planning entirely**; older `/gsd:quick` with composable flags (`--discuss --research --full`); `/gsd:set-profile budget|balanced|quality`.
- **What to learn:** one phase = one overridable command with a state-derived gate; steal `SPEC == FINALIZED`; a real fast path that skips planning.

**GSD-2 / GSD Pi** (https://github.com/gsd-build/gsd-2 → https://github.com/open-gsd/gsd-pi). TypeScript rewrite on the "Pi" SDK. Strictly sequential `Research → Plan → Implement → Verify` over milestones → slices → tasks.
- **Defining idea:** control lives **OUTSIDE the agent harness** — an external dispatcher ("auto mode") per unit reads durable state, picks the next unit, spawns a **fresh agent session**, injects focused context, applies **phase-specific tool policy**, re-reads disk. Phase is **derived from state** (`deriveState()` parses `.gsd/`), never held in memory. State = `.gsd/` Markdown + `gsd.db` SQLite (atomic txns, `content_hash` integrity) → crash recovery/resume, stuck-loop detection, cost tracking, complexity-based model routing.
- **Inner loop:** verify-driven auto-fix retries (lint/test/typecheck) with bounded backoff + stuck detection; **pluggable** via an extension surface + loads `.claude/skills`.
- **Human gate** biased to **review-at-merge** via worktree isolation.
- **Fast path:** complexity classifier **light/standard/heavy** (routes model+timeout) + `/gsd quick` vs `/gsd auto`.
- **v1→v2 lesson:** *"GSD v1 taught the harness how to behave; GSD-2 supervises the run."* Prompt-injected discipline is unreliable/unrecoverable over long autonomous runs; externalizing control + state-derived phase makes discipline **enforced + resumable**.
- **Cross-cut:** same phase vocabulary, opposite enforcement — GSD by **convention** (finalized-spec gate + command-per-phase), GSD-2 by **construction** (dispatcher won't advance + per-phase tool policy). **We chose convention** (§6) — GoShipit is local-first + human-in-loop and doesn't have GSD-2's autonomous-run problem; but we steal the cheap part of construction (state-derived phase enum).

### 3c. Spec-driven frameworks

- **GitHub Spec Kit** (https://github.com/github/spec-kit): commands `/speckit.specify → clarify → plan → tasks → analyze → implement`; each phase emits **one markdown artifact that is the sole input to the next**; `plan` emits machine-checkable `contracts/`. **Constitution-as-config** (`.specify/memory/constitution.md`) every phase reads. **Article III:** no implementation code before tests are written, user-approved, and confirmed FAILING (Red). Weakest at small-change routing (uses an "evolving specs" guide).
- **BMAD-METHOD** (https://github.com/bmad-code-org/BMAD-METHOD, ~50k stars): specialized agent personas + per-phase docs (`prd → architecture → story-file`). **Story-file sharding** compiles a self-contained minimal-context work unit for implement. Named readiness gate **`check-implementation-readiness` = PASS/CONCERNS/FAIL**. Test-Architect is an **optional installable module** (pluggable inner loop). **Scale-adaptive tracks: Quick Flow / full / Enterprise** ("route by planning need, not story math").
- **Amazon Kiro** (https://kiro.dev/docs/specs/): three files `requirements.md (EARS notation) → design.md → tasks.md`, explicit **approval gates between phases**. **Three tiers: vibe → quick-plan → full-spec** with a "Generate spec" promotion path. EARS = `WHEN <event> THE SYSTEM SHALL <behavior>` — testable acceptance criteria at the gate.
- **Tessl** (https://tessl.io): plan/spec/tests as long-term codebase memory; **spec-as-source** (code regenerable); plan-approval gate before execution; a versioned "Spec Registry" of library usage specs.

**What to learn:** one artifact per phase IS the contract (swap a producer without touching consumers = overridability); a versioned constitution/principles file; machine-checkable contracts at design→implement; named gates with an explicit verdict; tests-approved-before-code; pluggable inner-loop module; small-change routing with a promotion path; context sharding.

### 3d. Interactive coding loops

- **Aider** (https://aider.chat): `architect` vs `code`/`ask` modes; architect = reasoning model proposes → editor model applies (ephemeral in-turn handoff). Auto-lint on by default, auto-test opt-in; **auto-commit every edit** but **"git push is still your call."** Fast path = plain `code` mode (edit+commit in one step); planning is the opt-in upgrade.
- **Cline** (https://docs.cline.bot): **Plan mode (read-only) vs Act mode**; separate model per mode; "for typos/simple fixes, start directly in Act — planning adds overhead." Auto-approve panel per action category.
- **Roo Code** (https://docs.roocode.com): modes Architect/Code/Ask/Debug/Orchestrator, each with a **tool-group permission set**; Architect can edit **markdown only** → plans become artifacts by construction; custom modes with file-glob scope.
- **Claude Code** (https://code.claude.com): **permission modes** `default/acceptEdits/plan/auto`; plan mode is read-only; **plan-approval menu selects the execution autonomy** (approve+auto / approve+accept-edits / approve+review-each); classifier blocks force-push/push-to-main even in auto; `.git`/config are protected paths.

**What to learn:** PLAN = a read-only capability tier (not a persona); the single human gate sits between plan→execute and the approval also picks execution autonomy; the fast path is the DEFAULT and planning is the opt-in upgrade; per-invocation escape hatches; sticky per-phase model/effort; **commit/push gated separately from edit, push defaults OFF.**

### 3e. Baseline SDLC conventions (the "boring but proven" floor)

- **GitHub Flow / trunk-based** (https://githubflow.github.io/, https://trunkbaseddevelopment.com/): branch → PR → **review (the human gate)** → merge → deploy. "Anything in `main` is deployable." **"No difference between a hotfix and a very small feature"** — no unreviewed fast lane; trunk-based routes hotfixes as fix-on-trunk-then-cherry-pick.
- **Conventional Commits** (https://www.conventionalcommits.org): `<type>[scope]: <desc>` (feat/fix/BREAKING → SemVer bump); a machine-readable **declaration of intent** that drives changelog/version/publish — the clean, overridable "how the commit/PR is written" seam.
- **semantic-release / release-please / Changesets:** all converge on a **prepare vs publish split** (semantic-release `prepare`→`publish`; release-please cut-tag/Release-PR → registry publish, "does NOT handle publication to package managers"; Changesets `version`→`publish`). Put the extra confirmation on the second, irreversible action.
- **Irreversibility rationale:** SemVer 2.0 Rule 3 (a released version MUST NOT be modified); npm unpublish policy (a used version string is burned forever; unpublish can't be undone). → push the irreversible act as late as possible, behind its own affirmative human trigger, never as a side effect.

**What to learn:** one human gate at the propose→integrate seam; prepare-vs-publish split with the irreversible step guarded; commit/PR convention as the overridable seam; **fast = keep the normal path short, NOT add an unreviewed shortcut** (the caveat that shaped our fast-path decision).

---

## 4. Distilled patterns (P1–P9)

Convergent across the strong majority of the 19 sources:

| # | Pattern | Seen in |
|---|---------|---------|
| **P1** | **One artifact per phase IS the contract** — override a phase = swap its producer, consumers untouched | Spec Kit, BMAD, Kiro, Tessl, GSD, Superpowers |
| **P2** | **A phase is a capability/tool tier**, not a persona (read-only → edit-scoped → commit/push) | Claude Code plan mode, Roo (Architect=md-only), GSD-2 |
| **P3** | **Phase derived from durable on-disk state** → resumable/inspectable | GSD-2, GSD (GoShipit already half-does this) |
| **P4** | **Named gate with an explicit verdict** before irreversible steps ("a gate, not a formality") | BMAD PASS/CONCERNS/FAIL, Kiro Approve, GSD FINALIZED, Claude Code plan-approval |
| **P5** | **Tests before code — test-approval elevated to a gate** | Superpowers TDD, Spec Kit Article III |
| **P6** | **Inner loop = a separate, pluggable axis** (TDD ∣ debug ∣ spike), referenced not hardwired | Superpowers, BMAD Test-Architect, GSD/GSD-2, Kiro |
| **P7** | **Prepare vs publish split, irreversible step guarded** | semantic-release, release-please, Changesets, No Mistakes, Superpowers finishing-a-branch |
| **P8** | **Review in a clean room, measured against intent**; classify findings auto-fix/no-op/ask-user | No Mistakes, code-review (5 lenses + confidence gate), feature-dev |
| **P9** | **Fast path routed by *planning-need*, not diff-size, with a promotion path** | GSD `/gsd-fast`, GSD-2 light/std/heavy, Kiro vibe→quick→spec, BMAD tracks, Cline, Aider |

---

## 5. The GoShipit-specific tension & how we resolved it

Superpowers models **one skill per phase** (~11 skills). But `docs/maintainers.md` mandates **"stay small at the surface and explicit underneath"** — keep the agent-facing skill surface lean (currently exactly 3), and: *"Add a CLI command when the behavior is plumbing. Add a skill only when the user needs a distinct mental model."* The **Skill Change Gate**: before changing a skill, cite a pressure scenario/dogfood note/failing test; before adding a skill, prove a **distinct mental model**. `docs/dogfood/issue-014-skill-surface-consolidation.md` *deliberately consolidated* from 7 phase-skills down to 3.

So the naive "port Superpowers one-skill-per-phase" would **reverse a considered decision**. Resolution: achieve phase separation the **GSD way (convention-enforced)** — a real **phase enum + one reference doc per phase (its contract)** under the owning skill, reusing existing CLI plumbing — and add a new skill *only* where it clears the distinct-mental-model bar.

### The five design principles we agreed on (these decide the rest)

1. **Lean surface.** Default to ref-docs + CLI. A new skill must earn a "distinct mental model."
2. **Overridability = artifact contracts.** Each phase = fixed `inputs → outputs → evidence → gate`. Override = swap the producer, consumers untouched. (P1 — the most universal pattern.)
3. **Convention over construction — for now.** Enforce with prose + `status` hints + `verify-run`, not a heavy supervisor. Steal the cheap part of construction: a state-derived phase enum (P3).
4. **Gates protect irreversibility, not ceremony.** Every path — fast or full — crosses the close-out human gate. What varies is planning ceremony, never the gate. (Reconciles P9 with the GitHub-Flow caveat.)
5. **Always keep one overseer.** Something must see the whole flow (`work-issue` + `status`). Don't let phase-decoupling dissolve the to-do spine. (This is why we did NOT go one-skill-per-phase — independent skills = a relay race with no referee.)

---

## 6. Decisions locked (with the user)

- **Q1 — Phase model: enum + per-phase reference docs**, `work-issue` stays the overseer. (Rejected: wholesale one-skill-per-phase — surface bloat + loses the referee; GSD-2 supervisor — overkill for local-first.)
- **Q2 — TDD: the failing test is the entry contract to `implement`** for code; the inner loop stays pluggable (`tdd | debug | spike | none`) for docs/config/spike work.
- **Q3 — Fast path: skippable phases within the ONE enum model** (a `quick` issue marks propose + the test-gate as not-required), NOT a parallel pipeline. Still crosses close-out; promotable to full if it grows. (User's own refinement — cleaner than a second lane.)
- **Lean surface / close-out: split close-out OUT of `work-issue` into its own skill.** Shipping/archiving is a distinct "gate" mental mode and is currently smeared across `work-issue` (PR) + `manage-issues` (archive). The user delegated the specifics of this to the implementer.

---

## 7. Proposed architecture (v1)

### 7.1 Skill surface: 3 → 4

| Skill | Owns | Change |
|---|---|---|
| `using-go-ship-it` | orientation, routing | + point to close-out |
| `manage-issues` | todo / start / return-to-todo (lifecycle state moves) | unchanged |
| `work-issue` | **build** phases: investigate, propose, implement, review + evidence | **shrinks** (loses PR + archive guidance) |
| **`close-out`** *(new; alt name `ship-issue`)* | **ship** phases: prepare-pr → publish → archive as three distinct gates | new — distinct "gate" mental model |

### 7.2 Phase enum (replaces the free-form string)

`setup → investigate → propose → implement → review → prepare-pr → publish → archived`

| Phase | Owner | Overridable unit (ref-doc) | Gate |
|---|---|---|---|
| investigate / propose / implement / review | work-issue | `skills/work-issue/references/phases/*.md` | propose→implement is a human gate (approve plan + failing test) |
| prepare-pr | close-out | `write-pr.md` ← *edit only this to change PR shape* | none (local `pr.md`, reversible) |
| publish | close-out | `publish.md` | **human:** approve push (`publish-pr --approved`) |
| archived | close-out | `archive.md` | **human:** warned terminal + explicit confirm |

Each phase doc is a **contract**: `Inputs → Outputs → Evidence → Gate`. This is the mechanism that makes "change write-PR without touching anything else" true.

### 7.3 The four mechanisms

- **Close-out = three separate gates** (the original trigger fix, reinforced by No Mistakes P8 + release-please/Changesets P7): `prepare-pr` (local `pr.md`, reversible) → *user reviews `pr.md` + `evidence.md`* → `publish --approved` (push + `gh pr create`, guarded) → `archive` (**terminal**: warns "no reopen/unarchive" and requires confirmation, never bundled with publish). Borrow from No Mistakes: review findings tagged `auto-fix / no-op / ask-user` (only `ask-user` stops the human); a data-loss/force-push guard on publish.
- **TDD = entry contract to implement** (P5): for code, the failing test is authored in `propose`; `implement` records the RED evidence (test + failing output) as implement-entry evidence, then drives it green. GoShipit still does **not** own the methodology — `implement.md` *references* the platform TDD/debug skill (e.g. Superpowers). Non-code sets `inner_loop: none/spike/debug`.
- **Fast path = skippable phases** (P9, user's Q3 insight): a per-issue `track: quick | standard` property (in `run.yaml`/frontmatter). `quick` requires only `implement → review → close-out` (skips investigate/propose + the test-gate; `inner_loop` may be `none`/light). `verify-run` demands evidence only for the track's REQUIRED phases; `status` next-command hints follow the track. Promotion: `set-track standard` (or `promote`) reinstates skipped phases. Every track still crosses close-out gates.
- **Review = pluggable pipeline behind a fixed contract** (P8; sub-decision (d), user-refined): the review phase's contract lives ONLY in `review.md` (inputs: diff + intent/plan; outputs: findings classified `auto-fix | no-op | ask-user`; evidence; gate), and a `review_pipeline: self | clean-room | plugin:<name>` field in `run.yaml` — recorded at review-entry, symmetric with `inner_loop` — selects the implementation (e.g. the platform `code-review` plugin's 5-lens pipeline). Swap the whole pipeline without touching any other phase; extraction into its own skill stays a cheap follow-up if a distinct mental model emerges.

### 7.4 CLI changes (FORWARD-ONLY — user decision 2026-07-06: no backward compatibility; design for the cleanest end state)

- `set-phase` validates **strictly** against the enum — invalid phase = hard error. NO legacy shim, no `test → review` mapping, no deprecation warnings.
- `start-issue --quick` / `--track`; a `set-track` (or `update-run`) command for promotion.
- Archive gains a terminal warning + confirmation.
- `verify-run` required-evidence set becomes **track-aware** (quick issues don't fail for missing propose evidence) and **publish-aware** (§8 (h)); failures hard-block `publish-pr` (§8 (e)).
- `status` next-command ladder becomes enum + track aware (replaces the hardcoded ladder at `cli.py` ~L751).
- **Command renames are permitted wherever they make the surface cleaner** — e.g. a dedicated `archive` command instead of overloading `cleanup-issue --destination archive`. Pick the cleanest name per phase; do not preserve old spellings.

### 7.5 Migration: NONE (forward-only; delete stale state)

- **No compat layer, no legacy detection.** User decision: old run state that predates the new lifecycle is simply **deleted/reset** when the change lands — "delete current state if that's better so we don't need to maintain or worry about what has ran before." No `doctor` legacy-string detection, no manual-migration guidance; the tool only ever knows the new enum. (The active issue-005 run needs no action — its `phase: propose` is already a valid enum value.)
- `work-issue`'s close-out sections MOVE to the close-out skill (removed from work-issue, not duplicated); `using-go-ship-it` routing updated.
- Tests: update `test_skills.py` / `test_cli_smoke.py`; ADD per-phase ref-doc example-drift tests (the maintainers rule: "add or update a test so example drift is caught"). Delete any tests that exist only to pin legacy behavior.
- Validate end-to-end with a dogfood run (an acceptance criterion).

---

## 8. Sub-decisions — RESOLVED at sign-off (2026-07-06) + follow-ups

**(a)–(c) confirmed by the user at the recommended option; (d) refined by the user:**
- **(a)** New skill name: **`close-out`**. (Rejected: `ship-issue`.)
- **(b)** Test-gate strictness: **`propose` fully pre-approves the failing test** (Spec Kit Article III style — tests-approved-before-code). (Rejected: only recording RED at implement-entry.)
- **(c)** Fast-path field: **`track: quick | standard`**. (Rejected: `tier: light | standard | heavy` — "heavy" had no defined behavior.)
- **(d)** **Review = a standalone pluggable unit, but NOT its own skill (surface stays at 4).** User requirement: review "should at least be a standalone unit so we can change its behavior and consider plugging" — the skill-vs-unit call was delegated to the implementer. Resolution: treat review **symmetrically with the inner loop** (Q2). Its ref-doc `skills/work-issue/references/phases/review.md` is the SOLE contract (inputs: diff + intent/plan; outputs: findings classified `auto-fix | no-op | ask-user`; evidence; gate), and a **`review_pipeline` field** in `run.yaml` (recorded at review-entry, mirroring `inner_loop`) selects the implementation: `self | clean-room | plugin:<name>` (e.g. the platform `code-review` plugin's 5-lens pipeline, or Superpowers requesting-code-review). Swapping the entire review pipeline = edit review.md + set the field; nothing else moves. If dogfooding later proves a distinct mental model, extraction into its own skill is a cheap follow-up (the contract already stands alone).

**Sign-off round 2 (2026-07-06, same day): four friction points surfaced during the design walkthrough, all resolved with the user:**
- **(e) Gate strength — block at close-out only.** `publish-pr` REFUSES to run when `verify-run` fails for the track's required phases — **absolute block, NO override/force flag** (user: "no fall back please"; the only way through the gate is to fix the evidence). Build-phase transitions stay warn-only. Mechanical enforcement sits exactly at irreversibility; convention everywhere else. (Rejected: advisory-everywhere — repeats the condition behind the original archive-before-review incident; block-all-transitions — GSD-2-style friction that fights local-first.)
- **(f) Test-gate scope — acceptance test(s) only.** `propose` authors and pre-approves the **acceptance-level** failing test(s) — the executable definition of done — NOT every task's unit test. Per-task RED→GREEN stays inside `implement`'s inner loop. Keeps propose a planning phase instead of absorbing half of implement. (Refines decision (b).)
- **(g) Quick track + tests — default TDD, opt-out logged.** `track: quick` skips the planning/pre-approval ceremony, but `inner_loop` still DEFAULTS to `tdd` for code changes; setting `inner_loop: none` on a code change requires a recorded reason (in run notes/`run.yaml`). Docs/config-only changes may be `none` freely. (Refines the fast-path mechanism in §7.3.)
- **(h) Publish gate — conditional on repo config.** `publish` is a required phase only when `repo.yaml` defines a remote/PR target. Local-only repos (or a stop-at-local-PR policy) may archive after local `pr.md` sign-off, with the skip recorded in the run. `verify-run`'s required-phase logic must account for this alongside track-awareness. (Rejected: strictly linear enum — breaks local-only repos and contradicts the stop-at-local-PR close-out rule.)

- **(i) FORWARD-ONLY — no backward compatibility, no fallbacks, anywhere.** User directive (emphatic, repeated): "we don't need backward compatibility … I want to have it as clean as possible"; "no fall back please"; "no backward compatibility!"; "delete current state if that's better." Consequences threaded through §7.4/§7.5: strict enum validation (no legacy shim), command renames permitted for cleanliness, no override flag on the publish gate, stale pre-lifecycle run state deleted rather than migrated, legacy-pinning tests deleted.

**Also noted at walkthrough (not a decision):** with close-out split out, the whole-flow "overseer" (design principle 5) is carried by the CLI `status` ladder + `using-go-ship-it` routing rather than any single skill; watch this during the dogfood run.

**Follow-up issues (out of scope here; may be their own issues — do NOT let them block the core work):**
- A `reopen`/`unarchive` command (archive is currently terminal with no undo).
- An issue-level draft-vs-ready / push-vs-local PR policy (there is no draft-PR support today; PR config is repo-level in `repo.yaml`).
- `go-ship-it/issue-004` (verify-run acceptance matcher requires verbatim criterion text) — do AFTER this issue. Note the P3/EARS "machine-checkable acceptance criteria" idea connects to it.

---

## 9. What's next (the plan for the next session)

**Hard gate reminder:** the issue treats "propose an architecture and get sign-off" as a gate before ANY implementation. The direction in §6 is agreed with the user, but the detailed design + plan should be confirmed before code.

1. **Turn this into a proper design doc / spec and get explicit sign-off.** This document is the seed. Confirm the four open sub-decisions (§8). Consider using the `brainstorming` → `writing-plans` discipline if Superpowers is available.
2. **Write a bite-sized TDD implementation plan** (Superpowers `writing-plans` style: exact files, per-task `Consumes`/`Produces`, RED→GREEN→commit steps). Suggested task decomposition:
   - Task A: phase enum in `state.py` + strict `set-phase` validation (hard error on anything else; no legacy mapping) (tests first).
   - Task B: per-phase reference docs scaffold + the contract template + example-drift tests.
   - Task C: split the `close-out` skill out of `work-issue`; move PR/archive guidance; update `using-go-ship-it` routing; update `manage-issues` boundary.
   - Task D: close-out gates — terminal-archive warning/confirm in `cleanup-issue`; findings classification in the review ref-doc; publish data-loss guard.
   - Task E: `track: quick|standard` field + `start-issue --quick` + `set-track`/promote + track-aware `verify-run` and `status` (replace the `cli.py:751` ladder).
   - Task F: pluggable-axis fields — `inner_loop` recorded at implement-entry (+ `implement.md` referencing the platform TDD skill) and `review_pipeline` recorded at review-entry (+ `review.md` referencing pluggable pipelines, findings classification).
   - Task G: docs (`README.md` lifecycle section, `docs/maintainers.md`) + full test pass + a dogfood validation run.
3. **Implement** in this worktree (`worktrees/go-ship-it/issue-005`, branch `go-ship-it/issue-005`), TDD, per the plan.
4. **Validate end-to-end with a dogfood run** and record it as GoShipit evidence; then close-out via the new three-gate flow (stop at the local PR for user sign-off — do NOT bundle archive).

---

## 10. Pointers & references

**Live GoShipit evidence (local, git-ignored):**
- Run notes (all research + v1 proposal): `state/repos/go-ship-it/issues/execution/issue-005/notes.md`
- Run metadata: `state/repos/go-ship-it/issues/execution/issue-005/run.yaml`
- Issue brief: `state/repos/go-ship-it/issues/execution/issue-005/issue.md`
- Worktree: `worktrees/go-ship-it/issue-005/` (branch `go-ship-it/issue-005`)

**Key source files to change:** `src/go_ship_it/state.py` (phase field/enum), `src/go_ship_it/cli.py` (`set-phase`, `status`, `verify-run`, the ~L751 ladder), `src/go_ship_it/pull_request.py` (prepare/publish gates), `src/go_ship_it/verify.py` (track-aware evidence), `skills/work-issue/`, `skills/manage-issues/`, `skills/using-go-ship-it/`, plus the new `skills/close-out/`.

**Design-philosophy gate to respect:** `docs/maintainers.md` (lean surface; add-a-skill bar; "add or update a test so example drift is caught"); `docs/dogfood/issue-014-skill-surface-consolidation.md` (why the surface is 3).

**Source URLs (research):**
- Superpowers / feature-dev / code-review: installed Claude Code plugins (`~/.claude/plugins/cache/claude-plugins-official/`).
- No Mistakes: https://github.com/kunchenguid/no-mistakes · https://kunchenguid.github.io/no-mistakes/
- GSD: https://github.com/open-gsd/gsd-core · https://github.com/glittercowboy/get-shit-done
- GSD-2 / GSD Pi: https://github.com/gsd-build/gsd-2 · https://github.com/open-gsd/gsd-pi
- Spec Kit: https://github.com/github/spec-kit · https://github.com/github/spec-kit/blob/main/spec-driven.md
- BMAD: https://github.com/bmad-code-org/BMAD-METHOD · https://docs.bmad-method.org/
- Kiro: https://kiro.dev/docs/specs/
- Tessl: https://tessl.io/blog/how-tessls-products-pioneer-spec-driven-development/
- Aider: https://aider.chat/docs/usage/modes.html · https://aider.chat/2024/09/26/architect.html
- Cline: https://docs.cline.bot/core-workflows/plan-and-act
- Roo Code: https://docs.roocode.com/basic-usage/using-modes
- Claude Code: https://code.claude.com/docs/en/permission-modes · https://code.claude.com/docs/en/sub-agents
- GitHub Flow / trunk-based: https://githubflow.github.io/ · https://trunkbaseddevelopment.com/
- Conventional Commits: https://www.conventionalcommits.org/en/v1.0.0/
- Release automation: https://semantic-release.gitbook.io/ · https://github.com/googleapis/release-please · https://github.com/changesets/changesets
- Irreversibility: https://semver.org/ · https://docs.npmjs.com/policies/unpublish/
