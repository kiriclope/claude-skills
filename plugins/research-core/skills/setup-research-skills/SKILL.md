---
name: setup-research-skills
description: Configure a research project once for the spec → tickets flow and the shared skills — the issue tracker (GitHub issues or local .scratch/), the triage and spec labels, the research meanings of Pocock's to-spec and to-tickets, a GLOSSARY.md drafted from the project's vocabulary rules, the "Agent skills" block in CLAUDE.md, .claude/project.yaml and the skill links. The research version of Matt Pocock's setup-matt-pocock-skills.
disable-model-invocation: true
---

# Setup research skills

Run once per project (again only to switch trackers). The templates are in `templates/agents/` of the skills repo
(`~/claude-skills`); every file this writes is the project's own afterwards, edited by hand.

## 1. Look first

```bash
git remote -v; gh auth status 2>&1 | head -3
gh repo view --json nameWithOwner,visibility 2>/dev/null
ls docs/agents GLOSSARY.md .claude/project.yaml 2>/dev/null; grep -n "^## Agent skills" CLAUDE.md
```

## 2. Choose the tracker (state it, ask only if unclear)

- A **private** GitHub remote and `gh` logged in → GitHub (`issue-tracker-github.md`).
- No remote, a public remote, or no `gh` → local markdown in `.scratch/` (`issue-tracker-local.md`); add `.scratch/` to
  `.gitignore` when the repo is public. Research tickets never go on a public tracker.
- Several projects share one repo (e.g. two worktrees) → still GitHub; the `spec:<name>` label keeps them apart.

## 3. Write `docs/agents/`

Copy `issue-tracker-<kind>.md` as `issue-tracker.md` (fill `{owner}/{repo}`), `triage-labels.md`, `research.md` and
`domain.md`. Never overwrite an existing file: show the diff and ask.

## 4. Draft `GLOSSARY.md` (the user approves it before it is written)

Format: `templates/agents/GLOSSARY-FORMAT.md` (Pocock's). Collect the project's vocabulary rules from the memory
(`feedback_*` notes on naming, vocabulary, notation), `CLAUDE.md`, `.claude/project.yaml` and the docs: each term once,
defined in one or two sentences, with its `_Avoid_:` words. Terms of this project only (task names, axes, group
elements, measures, run naming), never general ML terms. Where the memory and the docs disagree, ask. When the
glossary is written, the memory notes it replaces get one line pointing to it (maintaining-memory), not a deletion.

## 5. CLAUDE.md, project.yaml, links

- Add the `## Agent skills` block (`templates/agents/agent-skills-block.md`) to `CLAUDE.md`, or update it in place.
- `.claude/project.yaml` from `templates/project.yaml` if missing (`review_checkpoint:` included).
- Domain skills: `ln -s ~/claude-skills/plugins/<plugin>/skills/<skill> .claude/skills/<skill>` (maintaining-skills,
  "Wire a project").

## 6. Labels on GitHub (ask first: it writes to the repo)

```bash
for l in needs-triage needs-info ready-for-agent ready-for-human wontfix paused; do gh label create "$l" 2>/dev/null; done
```
A `spec:<name>` label is created when its spec is published (`docs/agents/research.md`).

## 7. Report

The tracker chosen and why, the files written (paths), what was left as it was, and the next step: `/grill-research`
on a destination, then `/to-spec` and `/to-tickets` in the same session.
