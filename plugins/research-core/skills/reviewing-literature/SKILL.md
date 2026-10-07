---
name: reviewing-literature
description: Search, read and position a project against the literature — a search protocol across Semantic Scholar, OpenAlex, PubMed, arXiv and bioRxiv, source tiers, a "they show X, we add Y" comparison matrix with named foils, the method gaps a reviewer will press, and notes checkpointed to docs/lit/ so they survive long sessions. Use when the user asks for a literature review, related work, "what is known about X", "has anyone done Y", positioning or novelty, a Discussion skeleton, or which papers a reviewer will cite against us. Not for checking one reference → verifying-citations; for a mock review → reviewing-manuscript.
---

# Reviewing literature

The goal is not a list of papers. It is a **position**: what is established, what the closest
work shows, exactly what this project adds, and where a reviewer will push. Every paper in the
output is real (verified) and every claim about it is something the paper says.

## Step 0 — scope and checkpoint file

1. Write the question in one sentence and the project's 2–4 candidate claims (from the
   overview doc / results draft).
2. Open or create `docs/lit/<topic>.md`. **Write findings there as you go** (after every few
   papers), not at the end — long searches get compacted and unwritten findings are lost.
   Read the file first: do not redo a search that is already logged.

## Step 1 — search protocol

- Sources, in order: Semantic Scholar / OpenAlex (citation graph), PubMed (neuroscience),
  arXiv and bioRxiv (recent and modeling), then Google Scholar-style WebSearch for gaps.
  APIs: `https://api.semanticscholar.org/graph/v1/paper/search?query=…`,
  `https://api.openalex.org/works?search=…` (WebFetch).
- Query by **mechanism and by method**, not only by topic; use the field's synonyms (the same
  idea often has 3 names across subfields).
- From the 3–5 most relevant hits, go **backward** (their references) and **forward** (who
  cites them, last 3 years). Stop when new searches return papers already logged.
- Log each search: date, source, query, number of hits screened, papers kept.

## Step 2 — tiers (read depth follows tier)

| Tier | What | Read |
|---|---|---|
| 1 Anchor | closest prior work; the paper a reviewer will name | full text, methods included |
| 2 Foil | a competing mechanism or result we must contrast | full text of the key figures |
| 3 Support | establishes a premise we use | abstract + the relevant result |
| 4 Context | background, reviews | abstract |

Prefer primary research over reviews for any specific claim; peer-reviewed over preprint when
both exist; say when a source is a preprint.

## Step 3 — the position (the output)

In `docs/lit/<topic>.md`:

```
## Comparisons (Discussion skeleton)
- Author et al. YEAR Journal — what they show (one line, their terms) — relation to us
  (lineage / framework / FOIL / same family) — what we add, in one line.
## Foils
- the 1–3 papers whose mechanism differs from ours, and the observable that tells them apart
## Method gaps a reviewer will press (priority order)
- gap — which paper sets the bar — our answer or the analysis that would pre-empt it
## Strengths to state plainly
## Vocabulary swaps
- our working term → the field's term (with the paper that uses it)
## Lead claims
- the 2–3 claims that are genuinely new given the above; what NOT to lead with (well-trodden)
```

## Step 4 — verify

Run the **verifying-citations** skill on every paper in the file (script for metadata; a
quoted passage for every "they show"). Mark each entry `✓ verified YYYY-MM-DD`. Unverified
entries stay out of drafts.

Then run the fresh review of **thinking-critically** (steps 3–4) on the position — the comparison
matrix, the foils and the lead / novelty claims. The reviewer searches for work that already
shows our "we add", and for papers that contradict a "they show".

## Rules

- Say "we did not find prior work on X (searched: …)" rather than "this is the first" —
  novelty claims are the ones reviewers check.
- Report contradicting evidence as prominently as supporting evidence.
- Do not summarize a paper you did not open; label abstract-only reads.

## Checklist (check before reporting; in the reply, one line: "✓ checklist" or the items that failed)
- [ ] question + candidate claims written; checkpoint file opened and read
- [ ] searches logged (source, query, screened, kept); backward + forward done for anchors
- [ ] comparison matrix, foils, reviewer gaps, lead claims written
- [ ] every entry verified (metadata + passage)
- [ ] position reviewed by a fresh agent (thinking-critically): novelty and "they show" claims
