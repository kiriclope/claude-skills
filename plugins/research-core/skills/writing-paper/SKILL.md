---
name: writing-paper
description: Draft and revise manuscript prose for a research paper — abstract, introduction, results, discussion, methods — in journal house style, claim-first, with every figure panel cited, one vocabulary, and every number traced to the numbers log. Use when the user asks to write, rewrite, polish, humanize or restructure paper text, a results paragraph, an abstract, a discussion, or to "make it read like a real paper"; also when turning results or notes into manuscript text. Captions are covered by making-figures (references/captions.md).
---

# Writing the paper

Manuscript text is final text: a reviewer reads a skipped panel, a wrong number or a term used
two ways as sloppiness. Write for the argument first; length is a separate, final pass.

## Step 0 — load the project's writing facts

From `.claude/project.yaml`: `style_guide` (journal house style, e.g. a corpus-derived guide),
`vocabulary` (the one term per concept), `numbers_log` (where every reported number comes from),
`paper_dir` (draft files). Read the style guide before writing a line. If there is none, build
one from 5–8 recent papers of the target journal (abstract architecture, paragraph skeleton,
how statistics are placed) and save it.

## Step 1 — decide the claims before the prose

- List the paper's claims in order (one line each); each Results section proves one.
- **Theory papers lead with the propositions** (what is proved/derived), then the simulations
  that test them, then data. **Data papers lead with the finding**, not the method.
- Lead with what is new and needs this paper to be known; well-established results are
  premises, not headlines.
- While the claims are still moving (new simulations pending), work on main results and main
  figures only; do not polish supplements, Methods or legends.

## Step 2 — paragraph skeleton (Results)

1. Motivation or prediction ("To test whether …, we …").
2. What was done, with the control or null named in the same breath.
3. The finding, past tense, figure pointer at the end of the clause it supports:
   "(Fig. 3b, blue)". Statistics in the parenthesis, not as the subject of the sentence:
   "(Fig. 4e; effect ± error, P, n with unit, test)".
4. At most one interpretive sentence, hedged ("indicating that", "consistent with").

State observations flatly; hedge only inferences. Rationed emphasis words ("Importantly" at
most a few per paper; never "Critically", "Surprisingly", "clearly show", "prove").

## Step 3 — panels, numbers, vocabulary (mechanical, do not skip)

- **Panel inventory:** open each rendered figure (Read the PNG), list every panel letter and
  sub-panel, and check that each is cited in the text and described correctly. Never guess
  panel letters.
- **Numbers:** every number in the text comes from the numbers log / script output of the
  current figures. If a number is not in the log, add it there first. Run the
  **auditing-paper-numbers** skill before a draft goes out.
- **Vocabulary:** one term per concept from `vocabulary`; define coined terms once, at first
  use, then never vary them. Do not let working jargon (variable names, lab shorthand) into
  the manuscript.
- **Citations:** only verified references (**verifying-citations**).

## Step 4 — style pass (reads as written by a scientist, not generated)

Remove: aphoristic colon openers, epigram closers, em-dash asides (use parentheses or commas),
"X, not Y" antitheses, the same thesis sentence repeated across Abstract/Introduction/
Discussion, rhetorical questions in Results, dates and version numbers in prose, and
ornamental sentences that restate a figure in metaphor. Prefer active first-person ("we
found"), plain transitions ("However", "We next", "Together"). Measure before claiming the
style is fixed (count em-dashes, semicolons and "we" per 1,000 words against the guide).

Caveats and limitations belong in the Discussion scope paragraph and Methods, not sprinkled
through Results. Be direct about absence when the test had power ("we did not observe …").

## Step 5 — length (only when asked)

Word limits are a final trimming pass once the argument is settled. Do not report length as
progress; judge a revision by whether the argument moves in one line.

## Checklist (copy and tick)

- [ ] style guide, vocabulary, numbers log loaded
- [ ] claims listed; section order follows them
- [ ] every panel inventoried from the rendered figure and cited correctly
- [ ] every number traced to the numbers log (auditing-paper-numbers run)
- [ ] every reference verified
- [ ] style pass done and measured
