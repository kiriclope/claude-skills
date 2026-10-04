---
name: maintaining-skills
description: Create, update, review and lint the shared skills repo (~/claude-skills) and the projects that use it. Use when the user asks to add/write/update/fix/review a skill, when a correction from the user ("don't do X again", "log the way we do Y") should become a durable rule, when a skill gave wrong or stale instructions, when setting up skills in a new project, or for a periodic skills health check.
---

# Maintaining skills

Skills are code: one source, reviewed, linted, versioned, tested against the failures they
exist to prevent. The repo is `~/claude-skills` (a plugin marketplace, see its `README.md`).

**Edit skills from a session opened in `~/claude-skills`** — its `.claude/settings.json` disables
provenance/watermark-scrubbing hooks there. If such a hook flags a SKILL.md elsewhere, do not run
its "clean" fix: it deletes the `description:` frontmatter, which stops the skill from triggering.

## Where a rule belongs (decide first)

| The rule is… | Put it in |
|---|---|
| a procedure or convention useful in any research project | `plugins/research-core/skills/<skill>` |
| specific to a model family / method shared by several projects | a domain plugin (e.g. `plugins/lowrank-rnn`) |
| about one person (preferences, machine, tools) | `profiles/<person>.md` (symlinked as `~/.claude/CLAUDE.md`) or `plugins/personal` |
| a fact about one project (paths, doc map, env, vocabulary, colors) | that project's `.claude/project.yaml` |
| a one-off project fact or current status | the project's docs or auto-memory, not a skill |
| something that must NEVER be skipped (blocking) | a hook in settings, not a skill — skills are advice |

Shareable plugins (`research-core`, domain plugins) must contain **no personal names, home
paths or machine facts** — read them from `project.yaml` / the profile instead.

## Update an existing skill

1. Read the whole SKILL.md and its `references/`/`scripts/`.
2. Make the smallest change that encodes the rule; put the **why** next to it (the failure it
   prevents). If it contradicts an older line, replace that line — never leave both.
3. Rules that matter most go near the top (after compaction only the first part of a skill
   is guaranteed to stay in context).
4. Prefer a script check over prose whenever the rule is mechanical.
5. Bump `version` in that plugin's `.claude-plugin/plugin.json` and add a line to `CHANGELOG.md`.
6. Lint (below). Then check the projects still using it.

## Create a new skill

1. **Collect 3 real failure cases first** (memory `feedback_*.md` files, past corrections). These
   are the evals: the skill exists to make those cases go right.
2. `name`: lowercase-hyphen gerund (`making-figures`), = directory name, no "claude"/"anthropic".
   `description` (≤1024 chars, third person): what it does + **when to use it**, with the
   words the user actually says. The description is the only part loaded until it triggers.
3. Body ≤500 lines: rules, a numbered workflow, a copyable checklist. Detail in
   `references/*.md` (one level deep; contents list if >100 lines). Deterministic steps in
   `scripts/` with `--help` and a `--demo`/self-test. Assume Claude is smart; cut explanations.
4. One default, not a menu of options. Exact commands for fragile steps.
5. Lint, then test: run a fresh subagent on each failure case with the skill available and
   check it now behaves (optionally `claude plugin eval` with cases under `evals/`).

## Review / health check

```bash
python ~/claude-skills/plugins/research-core/skills/maintaining-skills/scripts/lint_skills.py \
    --projects <project roots that use the skills>
claude plugin validate ~/claude-skills
```
The linter flags: frontmatter rules, missing "when to use", length, missing referenced files,
nested references, personal facts in shareable plugins, hard-coded model names, old dated
facts to re-verify, scripts that do not compile, **project copies that should be symlinks**
(and copies that have drifted).

Then read each flagged skill and judge what a linter cannot:
- Does every instruction still match the code it drives (flags, script names, defaults)?
  Run each script's `--help` and compare.
- Do skills, `CLAUDE.md`, the profile and memories contradict each other? Fix the wrong one.
- Is a rule duplicated in two skills? Keep it in one and point to it.
- Is any skill never used, or triggered when it should not be? Tighten the description.

Report as a table: skill · issue · fix · done/pending. Ask before deleting a skill.

## Wire a project

```bash
mkdir -p .claude/skills
ln -s ~/claude-skills/plugins/<plugin>/skills/<skill> .claude/skills/<skill>   # domain skills
cp ~/claude-skills/templates/project.yaml .claude/project.yaml                 # then fill it in
```
`research-core` skills are linked once in `~/.claude/skills/` and apply everywhere. Never copy a
skill into a project: copies drift. Colleagues install with
`claude plugin marketplace add kiriclope/claude-skills` + `claude plugin install research-core@leon-skills`
(and `pip install "git+https://github.com/kiriclope/claude-skills#subdirectory=python"` for `cbstyle`).
After changing a skill, bump the plugin `version` so their `claude plugin marketplace update` picks it up.
