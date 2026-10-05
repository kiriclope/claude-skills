---
name: reviewing-code-readability
description: Review research code for readability and the house coding conventions — can a colleague tell what it decides, run it from its docstring, and trust its numbers — then fix what fails without changing behavior. Runs readability_check.py (opaque names, hard-coded derived constants, comments that swallowed code, silent excepts, missing docstring/Usage, hex colors, deep nesting) and a colleague-test rubric. Use when code was just written or edited and before committing it, when asked to review / clean up / tidy / make readable a script, "is this readable", "does this follow my conventions", or before sharing code with colleagues. For correctness bugs use /code-review; for reuse and simplification use /simplify.
---

# Reviewing code readability

Code passes when a colleague who has never seen it can, in five minutes, say what it decides,
run it, and find the reason for every non-obvious choice — and when it follows the house
conventions, so that every file in every project reads the same way.

The conventions are defined once, in the `writing-research-code` skill. This skill checks code
against them and fixes it. Project-specific rules come from `.claude/project.yaml` →
`code_rules` (read by you) and `code_check` (read by the script).

## Step 0 — load the rules

```bash
cat .claude/project.yaml 2>/dev/null | sed -n '/^code_rules:/,/^[a-z_]*:/p; /^code_check:/,/^[a-z_]*:/p'
```
Read `writing-research-code/SKILL.md` if it is not already in context. `references/examples.md`
(this skill) has the before/after pairs that define the conventions in practice.

## Step 1 — run the checker on what changed

```bash
python <this skill>/scripts/readability_check.py <files you wrote or edited>      # lines changed since HEAD
python <this skill>/scripts/readability_check.py --all <file>                     # whole-file audit
```
Default scope is the lines changed since the last commit (new files: all lines) — review what was
just written, do not bury it under the history of the file. `--all` only when asked for an audit.

| severity | rule | why it matters |
|---|---|---|
| error | `hard-coded-derived` | a constant the config derives (α, dt, σ) was typed in — it drifts silently when the config changes |
| error | `code-in-comment` | `a = 1  # note; b = 2` — a definition swallowed by a comment |
| error | `silent-except` | bare `except:` / `except Exception: pass` hides the failure |
| warn | `opaque-name` | `k1zcnl`, `sclnl` — the reader cannot decode it |
| warn | `module-docstring`, `usage-block`, `argparse-help` | a script must say what it decides and how to run it |
| warn | `deep-nesting`, `long-line`, `hex-color` | hard to follow; colors must come from `cbstyle` / the project map |
| info | `long-function`, `todo`, `commented-code`, `spelling` | judgment calls; spelling = American English in comments/docs only |

## Step 2 — the colleague test (what no script can judge)

Read the changed code as a stranger would. For each item, a concrete finding or nothing:

1. **What does it decide?** The module docstring states the question the script answers and its
   success criterion, before any procedure (model: `references/examples.md` § docstring).
2. **Can I run it?** A `Usage:` line with the exact command, including the env prefix
   (`project.yaml` → `env_prefix`), and argparse `help=` texts that explain semantics.
3. **Why this number?** Every threshold, sign convention, window and magic constant has its
   reason next to it — or comes from the config. Dated decisions say when and on what evidence.
4. **Same name, same thing.** Names follow the math and the paper (`project.yaml` → `vocabulary`):
   one symbol per quantity across files (`kappa`/`κ₀` everywhere, not `k0` here and `kap0` there).
5. **One source of truth.** No copied constant, no re-implemented training/analysis logic —
   grep for the definition and import it (project `code_rules` name the canonical helpers).
6. **One idea per function.** A function that loads, computes and plots is split where it
   changes subject — but match the file's existing density; do not explode dense research code
   into twenty one-liners.
7. **Comments are true.** A comment that contradicts the code is worse than none — fix or delete
   it. Comments say why, not what. No commented-out blocks without a reason.
8. **Fails loudly.** No silent defaults for missing data, no swallowed exceptions.
9. **Prints unit by unit.** Results come per seed/subject with a `SUMMARY: k/N` line.
10. **Project rules.** Each `code_rules` item from `project.yaml` holds.

## Step 3 — report

One table, most misleading first (wrong comments, hidden constants, swallowed code before
cosmetics):

| severity | file:line | issue | fix |
|---|---|---|---|

End with the checker's SUMMARY line and what you did not check (e.g. "did not run it").

## Step 4 — fix (when asked, or for code you just wrote yourself)

- **Behavior-preserving edits only.** Before and after a fix, run the script on a small real case
  and compare the printed numbers — identical, or explain the difference (a fix that changes a
  number is a bug fix, report it as one).
- **Never rename without asking:** public functions, CLI flags, config fields, file names, and
  stored keys (cache, results, checkpoint dicts) — other scripts, old checkpoints and results
  depend on them. Propose the rename instead.
- Do not reformat untouched code, do not run a formatter over a whole file, do not add
  docstrings to trivial helpers (match the file's comment density), do not translate existing
  identifiers to American English.
- Re-run the checker until it reports no `error`; `warn` items are fixed or justified in one line.

## Checklist (copy into your reply)

- [ ] rules loaded (writing-research-code, project `code_rules`)
- [ ] `readability_check.py` run on the changed files — SUMMARY: … 
- [ ] colleague test done (10 items)
- [ ] findings reported, most misleading first
- [ ] fixes behavior-preserving, verified by running; no unasked renames
