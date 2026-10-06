# Research skills

Shared Claude Code skills for computational-neuroscience projects. One source, linked into
every project, so a fix lands everywhere and nothing drifts.

## Layout

```
.claude-plugin/marketplace.json     marketplace "leon-skills"
plugins/
  research-core/   shareable, any project — no personal facts allowed
    clarifying-requests      vague request → look first, mirror, ≤4 sharp questions with options → task spec
    running-review-checkpoints  regular human review: digest + decisions to approve; Stop hook + commit gate enforce it
    thinking-critically      plan → act → FRESH independent review of every claim → revise (anti-hallucination loop)
    planning-research        hypothesis → predictions → controls → success criteria → staged runs
    launching-experiments    confirm params, pilot, one screen + log per seed, provenance (record_provenance.py)
    debugging-training       systematic diagnosis; freeze_check.py (frozen params, grad norms)
    auditing-results         unit-by-unit, all outcomes, nulls, matched n (audit_table.py)
    checking-derivations     sympy + numeric check against the model (check_jacobian.py)
    making-figures           colorblind-safe style (cb_style.py, paper.mplstyle), check_figure.py, captions
    writing-research-code    naming, docstrings, single source of truth, verify by running
    reviewing-code-readability  colleague test + readability_check.py against the house conventions
    writing-paper            claim-first prose, every panel cited, one vocabulary
    auditing-paper-numbers   every number in the draft traced to the numbers log (audit_numbers.py)
    verifying-citations      Crossref/OpenAlex check of every reference (verify_refs.py)
    reviewing-literature     search protocol, comparison matrix, notes in docs/lit/
    responding-to-reviewers  point-by-point, no fabrication, no overpromising
    log-and-ship             docs + memory + commit
    maintaining-skills       create / update / review skills (lint_skills.py)
  lowrank-rnn/     domain: flow-verdict, traj-verdict, bifurcation-probe
  personal/        Leon's machine only: figure-gallery
hooks/             guard_bash.py — enforced rules (push asks, trailer, sweeps in screen); see hooks/README.md
profiles/<person>.md   personal preferences, linked as ~/.claude/CLAUDE.md
templates/project.yaml per-project facts the skills read (.claude/project.yaml)
```

## Three layers of facts

1. **Skills**: procedures and default conventions (generic).
2. **`.claude/project.yaml`** in each project: doc map, memory folder, env prefix, figure style,
   vocabulary, never-stage paths.
3. **Profile** (`~/.claude/CLAUDE.md`): who you are and how you like to work.

## Install

Leon (live edits, via symlinks):
```bash
ln -s ~/claude-skills/plugins/research-core/skills/* ~/.claude/skills/
ln -s ~/claude-skills/plugins/lowrank-rnn/skills/<skill> <project>/.claude/skills/<skill>
```
Colleagues (versioned plugin install from GitHub):
```bash
claude plugin marketplace add kiriclope/claude-skills
claude plugin install research-core@leon-skills       # + lowrank-rnn@leon-skills for low-rank RNN projects
pip install "git+https://github.com/kiriclope/claude-skills#subdirectory=python"   # cbstyle, used by making-figures
git clone https://github.com/kiriclope/claude-skills ~/claude-skills               # templates, profiles, hooks
cp ~/claude-skills/templates/project.yaml <project>/.claude/project.yaml          # fill in
cp ~/claude-skills/profiles/leon.md ~/claude-skills/profiles/<you>.md             # edit, link as ~/.claude/CLAUDE.md
```
The plugin install copies only the plugin folders, so `cbstyle` needs the `pip` line; the hooks are
installed by hand (`hooks/README.md`).

## Health check

```bash
python plugins/research-core/skills/maintaining-skills/scripts/lint_skills.py --projects <project roots>
claude plugin validate .
```
