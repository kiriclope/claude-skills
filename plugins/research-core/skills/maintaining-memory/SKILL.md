---
name: maintaining-memory
description: Keep Claude Code's cross-session memory short, current and trustworthy — find oversized memory notes, trim each to its current state plus the rules that still hold, archive the full original (never delete), and keep notes from growing back into logs. Use when a memory note is over the size cap (resuming-work flags it), when the user says "trim / archive / clean up the memory", when memory contradicts the docs, or as a periodic check. Not for the session catch-up → resuming-work; not for the repository's files and docs → organizing-projects.
---

# Maintaining memory

A memory note that grows into a newest-first log is searched, not read, so a superseded claim in its
history comes back as current; it also drifts from the project docs. Trimming fixes that. Deleting
would not: when five 60–140 KB notes were trimmed, 25 of the 253 scripts they named were described
nowhere else. So **trim and archive, never delete**.

## Rules
- The full original goes to `memory/archive/<note>.md`: not in the index, found by search.
- **The user approves each note** before it changes. Never trim on your own initiative.
- A trimmed note has three parts: **Current state** (dated, newest first), **Rules that still hold**
  (traps, dead ends, corrections, decisions in force), **Where the history is** (the archive first,
  then the docs). About 150 lines / 15 KB.
- Facts and numbers verbatim. Additions (verified pointers, "Checked" lines, conflict lists) are marked.
- Other sessions write memory at the same time: snapshot before drafting; `apply` refuses a changed note.
- Doc contradictions found on the way are reported with file:line for fixing in the docs, not
  silently resolved in memory.

## Workflow
```bash
S=<this skill>/scripts/memory_trim.py; W=<scratch folder, e.g. the job's tmp dir>/trim
python $S scan --all                                   # notes over the cap (resume.memory_cap_kb, 40 KB)
python $S snapshot --work $W <note> [<note> ...]
```
1. **Draft**: one fresh agent per note, in parallel and in the background. Prompt: "Follow
   `references/trim_brief.md`. Note: <path>. Work folder: $W. Docs to check coverage against: <paths>.
   Topic notes in <memory folder> can replace content by their [[link]]." Each writes `$W/<stem>.md`
   and `$W/<stem>.report.md` and nothing else.
2. **Check**: `python $S check --work $W --roots <project folders>`. It reports a front-matter change,
   a missing archive pointer and a draft over the target as blocking, numbers absent from the original
   (each must be a marked addition; look each one up), and how-to coverage: scripts and flags that
   only the original described ("file only", "code only").
3. **Decide** with the user, one question per note (AskUserQuestion, at most four per round): *Apply,
   keep flagged* (recommended) · *Apply as drafted* · *Not now*. Preview: sizes, the flagged uncovered
   items, the conflicts. For "keep flagged", send the list to the drafting agent (it still holds the
   note); it adds them verbatim; re-run `check`.
4. **Apply**: `python $S apply --work $W <note>` for each approved note.
5. **Log**: when the user asks to commit, commit the vault (`memory: trim <notes>`, log-and-ship step 2)
   and list the doc conflicts with file:line.

## Keeping notes trim (whenever you write memory)
- A state note holds the current state, not a diary: when you add a dated entry, rewrite or delete the
  entries it supersedes in the same edit. History belongs in the project docs (log-and-ship writes it
  there anyway); the note points to it.
- A rule learned from a mistake goes under "Rules that still hold" or into a feedback note, never only
  inside a dated entry where it will be buried.
- A topic that grows its own history gets its own note, and a `[[link]]` from the state note.
- After writing memory, `python $S scan --repo .`: a note over the cap → propose this skill (do not
  trim unasked). `MEMORY.md` near 200 lines / 25 KB → shorten index lines (lines past the limit are
  never loaded).

## Vault
If the memory root is a git vault with a whitelist `.gitignore`, it must track the archive:
`!*/memory/archive/` and `!*/memory/archive/*.md`.

## Never
- Delete a note or its history, or apply a trim the user did not approve for that note.
- Apply over a note that changed since the snapshot; merge or redraft instead.
- Let a drafting agent edit anything but its draft; round, re-derive or "fix" a number in memory.

Checklist, reported as one line: scanned · snapshot · drafts checked (front matter, numbers, how-to) ·
user approved each note · applied with archive · doc conflicts reported.
