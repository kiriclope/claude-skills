---
name: verifying-citations
description: Verify every reference before it is cited — existence, title, first author, year, venue and DOI checked against Crossref and OpenAlex with verify_refs.py — and pin each cited claim to the passage that supports it. Use whenever adding, drafting or reviewing references, a bibliography, a related-work paragraph, a literature summary, or any sentence of the form "X et al. showed …"; when the user asks "is this reference right", "check the citations", "audit the bib"; and before any manuscript, grant or report goes out.
---

# Verifying citations

Language models produce plausible references that do not exist, and real references with the
wrong year, venue or first author, and real papers cited for claims they do not make. All three
look identical on the page. **A reference that has not been verified in this session is not
cited** — it is written as `[CITATION NEEDED: what it should support]` until it is.

## Step 1 — verify existence and metadata (script, never from memory)

```bash
python <this skill dir>/scripts/verify_refs.py refs.bib                 # BibTeX
python <this skill dir>/scripts/verify_refs.py refs.txt                 # one reference per line
python <this skill dir>/scripts/verify_refs.py --ref "Author et al. 2020 Journal" --ref 10.xxxx/yyy
```
Set `VERIFY_REFS_MAILTO` to a contact address (polite API pool). No keys needed.

| Verdict | Action |
|---|---|
| `VERIFIED` | cite it, using the printed DOI |
| `VERIFIED (no title)` | read the printed title; cite only if it is the paper you mean |
| `MISMATCH(field)` | correct that field from the printed record, re-run |
| `NOT FOUND` | do not cite; search by hand (WebSearch) or ask the user; never invent a substitute |

Run it on the whole bibliography before every submission, not only on new entries.

## Step 2 — verify the claim (the part no script can do)

For each citation that supports a specific claim:
1. Open the source (abstract at minimum, full text when the claim is specific: a number, a
   method, a brain area, a species).
2. Quote the supporting passage in your working notes:
   `claim → ref → "quoted passage" (section/figure)`.
3. Check the direction and scope: species, area, task, correlational vs causal, model vs data.
   "X et al. showed" requires that X showed it, not suggested or assumed it.
4. If you only read the abstract, say so in the notes. If the passage does not support the
   claim, weaken the claim or drop the citation.

## Step 3 — report

A table: reference · verdict · DOI · claim it supports · supporting passage (or "abstract only")
· action. List every `NOT FOUND` and `MISMATCH` first.

## Rules

- Never fill a reference from memory, even a famous one: run the script. Famous papers are
  where the year and first author are most often wrong.
- Never "fix" a `NOT FOUND` by picking the nearest search result; that is a different paper.
- Preprint vs published: cite the published version when it exists (the script shows the
  journal record); keep the preprint only if the claim is in it alone.
- Keep the checked list in the project's notes (e.g. `docs/lit/references_checked.md`) with the
  date it was verified, so the next session does not re-check or re-guess.

## Checklist (copy and tick)

- [ ] `verify_refs.py` run on every reference; zero `NOT FOUND` / `MISMATCH` left
- [ ] every `VERIFIED (no title)` title read and confirmed
- [ ] each specific claim pinned to a quoted passage (or marked abstract-only)
- [ ] no `[CITATION NEEDED]` left in text that goes out
