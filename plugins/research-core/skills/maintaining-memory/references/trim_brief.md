# Brief for the drafting agent: trim one memory note

Give this file to a fresh agent with: the note's path, the work folder, the project docs to check
coverage against, and the memory folder (topic notes there can replace content by a `[[link]]`).

A memory note that grew into a long newest-first log is consulted by search, not read, so a superseded
claim in its history can come back as current. Goal: a short note that tells a fresh session **what is
true now** and **which rules still hold**, and points to where the history lives. The full original
will be archived as `memory/archive/<note>.md`, so nothing is lost by dropping history.

## Write ONLY these two files
- `<work>/<note stem>.md` — the draft
- `<work>/<note stem>.report.md` — the report

Do not edit the memory note, any doc, or anything else. Read-only everywhere else; no scratch files
outside `<work>`.

## The draft
- Keep the front matter block (from the first `---` to the second) byte-identical.
- Target ≤ 150 lines and ≤ 15 KB. Sections, in this order:
  1. **Current state**: what is true now (latest results, decisions in force, what is running or
     pending, the next step), newest first, each item dated (absolute dates).
  2. **Rules that still hold**: traps, dead ends ("do not re-report"), corrections that supersede older
     claims, user decisions still in force, conventions, gotchas. Keep these even when old.
  3. **Where the history is**: first `memory/archive/<note stem>.md` (the full pre-trim note), then the
     doc files/sections that hold the long-form history (verify each path exists).
- Copy facts and numbers **verbatim**; never invent, round or re-derive a number. Every kept claim must
  appear in the original. You may shorten the wording around the facts.
- Additions are allowed only when verified and marked: a "Read first" pointer to newer docs, a
  "Checked <date>:" status line, a "Conflicts to settle" list. Say in the report what you added.
- A newer entry supersedes an older one: keep only the newer. If the original contradicts itself
  (e.g. a factor that does not follow from its own formula), keep the consistent part and report it.
- Keep the `[[links]]` to other notes; content that a topic note already holds becomes its link.
- Running jobs and "pending" items: check them (screen -ls, the files they produce) before keeping them.
- Write in the user's language variant (see the profile).

## The report (≤ 60 lines)
1. Sizes: original lines/KB → draft lines/KB.
2. What "Rules that still hold" keeps, one line each.
3. **Dropped content found in no doc**: for each dropped block, search the project docs for a
   distinctive phrase or number from it. List the uncovered ones: date, one-line summary, and your
   judgment, still useful (a rule, a number used in the paper, the only description of a script) or
   obsolete. This is the list the user decides on; nothing on it is lost (the archive keeps it).
4. What you were unsure about (superseded or not, still pending or not).
5. Contradictions between the note and a doc (name both places, file:line).
