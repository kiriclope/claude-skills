---
name: concluding-research
description: Conclude one research question across all its verdicts — collect every verdict card on the question, check they can be pooled (same scoring, criterion, code), account for every run, rebuild the status of each hypothesis across cards (established / supported / not supported / refuted / open, with independent units), list what was discarded and how decisively, surface contradictions and corrections, answer the question in plain words with a ledger figure, and propose the next 2–3 experiments ranked by how much they would change the answer, each as a draft pre-run card. Writes or rewrites the question's section of docs/conclusions.md. Use when a series of verdicts on one question is in, when the user asks "what do we know about X", "what did we learn", "conclude", "summarize the results so far", "where does this question stand", "what next on X", or before deciding to drop or change a direction. Not for a single fresh result → auditing-results; for the plan of the next experiment → planning-research.
---

# Concluding research

A verdict answers one run; a question is answered by many. Read one card at a time, a project
forgets what it refuted, repeats discarded levers, pools cards that were scored by different rules,
and keeps believing a card's title after its evidence was corrected. A conclusion is the state of
one question: what is known, how strongly, what was dropped and why, and what to run next.

## Step 0 — the question and its cards

1. State the question in the user's words, with the date it was asked (e.g. "what makes the
   curriculum solve Dual?"). One conclusion = one question; a second question gets its own section.
2. Collect its cards from the verdict log (`project.yaml` → `verdict_log`, default `docs/verdicts.md`):
   ```bash
   python <this skill>/scripts/collect_cards.py --log docs/verdicts.md --match "<regex>"          # headings only
   python <this skill>/scripts/collect_cards.py --log docs/verdicts.md --match "<regex>" --body   # + card bodies
   ```
   It prints each card's date, title, Verdict / Criterion / Plan (or Question / Claim tested) lines and
   flags (after-data, open card, corrected). Start with headings; add `--body` to find cards whose
   heading does not name the question, then drop the off-topic ones by reading them. Read every kept
   card in full — **the evidence, not the title**. **Why:** a card titled "κ₁ held near 0 through the
   curriculum" was contradicted by its own numbers (0.022–0.131 after Dual), and a later plan was built
   on the title (2026-10-29).
3. **Runs without a card:** list the finished run directories of the question's sweeps that no card
   cites. Report them as uncarded; conclude nothing from them until they are audited (auditing-results).
4. Show the card list to the user in one table (date · lever · verdict) and say which cards you left
   out and why. Open pre-run cards (RUNNING) are listed as pending, never concluded.

## Step 1 — can the cards be pooled?

For each card note: the scoring rule and its condition (e.g. noise on/off), the criterion, the
primary metric, the code version, the seeds. Cards judged differently are **not pooled** as they
stand. Handle each difference one of three ways and say which:
- **rescored**: the runs scored again under the current rule (the numbers change);
- **re-tallied**: the card's own per-run table read again under the current criterion (e.g. the
  criterion dropped retention) — allowed only when the table gives every run's numbers;
- **kept apart**: shown in its own row or footnote, not pooled.

**Units — count replicates, not runs.** Replicates are what was drawn independently: seeds (or
subjects). Runs that differ by a lever are arms, not replicates; nets that share a parent stage or
one init are one replicate for anything that parent or init fixes. Count a lever at the stage where
it acts (a GNG-stage lever: its GNG runs), but report the replicate count: "23/24 runs, 1 seed, 12
DPA nets from one init". A run cited by several cards counts once.

## Step 2 — the run account and the hypothesis ledger

1. **Run account first (no quiet exclusions).** For each hypothesis, list every run in every arm the
   hypothesis covers, across all cards: included, or excluded with the reason. Keep the account in the
   notes beside the section; the section gives its totals ("23 of 24 runs; 1 excluded: other Dual
   loss"). **Why:** a test conclusion counted 22/22 for "no hold is enough" after silently skipping the
   one no-hold run that failed; only the fresh review found it (2026-10-29).
2. **The ledger,** one row per hypothesis (merge the same hypothesis worded differently):

| H | the hypothesis, one plain sentence | cards for · against | runs (replicates) | stage | status |
|---|---|---|---|---|---|

Status words, from auditing-results §0 and planning-research Step 1:
- **established**: supported, and repeated on fresh seeds by a confirming card;
- **supported**: the effect exceeds its measured noise floor, or the design could decide it
  (`stats_floor.py` reaches α at this N) and it did — exploring runs only, "not yet confirmed";
- **not supported**: a design that could decide found no effect;
- **refuted**: the prediction failed in a design that could decide;
- **open**: untested, a rival not excluded, the cards contradict, or the design could not decide.
  When the direction held in every replicate but N could not decide, write it so: **"open:
  consistent in 4/4 twin pairs, N cannot decide (McNemar floor .125)"**. That is the honest word for
  one-seed series; never upgrade it to "supported".

A screen (WHY "none") supports what a lever changed, never a mechanism. `stats_floor.py` is in the
choosing-statistics skill: `choosing-statistics/scripts/stats_floor.py --counts N | --n N`.

## Step 3 — the conclusion

- **The answer** in plain words a reader who missed every session understands, each claim with its
  status word; up to 8 lines. Then one line each: **Data finding** / **Imposed by the setup** (a loss
  term, a constraint, a scoring choice) / **Model limitation**.
- **What would overturn it**: for each claim the answer rests on, the card's own prediction or
  falsifier when it had one; when it had none, say "none fixed before" and name the result that would
  overturn it — that result is a candidate next step, not a test already passed.
- **Discarded, and how decisively**: every lever dropped, with the card, the reason and whether the
  test could have shown the opposite. **Why:** a wrong discard is invisible unless it is listed; the
  delay pin was first logged as refuted on a 4/6 vs 5/6 count that no outcome could have reversed.
- **Contradictions**: two cards that disagree are both shown, with which one is right and why, or
  the question is left open — never averaged.
- **Corrections found**: card statements the evidence does not support (cards and memory notes).
  List them for the user; do not edit the cards yourself (other sessions may be editing the log).

## Step 4 — the ledger figure (making-figures Steps 2–3)

Not the per-test evidence figure of auditing-results (that one has one panel per test and PASS /
FAIL markers); a conclusion has one panel, the ledger:
- one row per hypothesis (≤ 8; the rest stay in the table), labeled with it in plain words;
- x = the cards in log order, labeled by short name and date (cards share dates, so not by date);
- one mark where a card bears on a hypothesis, its shape = **what that card says about it**:
  ● supports · ✖ against, beyond noise · ○ no effect · ◇ cannot decide; a card that is only a
  baseline gets no mark, its count goes in the label of the card it is compared with;
- each mark labeled with its count (k/N, or "a vs b");
- the hypothesis's status at the row's right end, the same four shapes + the status word;
- the title is the answer in one line. Shapes carry the meaning; color may repeat it, never alone.

## Step 5 — next steps (ranked)

2–3 experiments ranked by **how much they would change the answer** — the open hypothesis whose
resolution matters most first, a confirming run for a supported one second. Each is a draft
pre-run card (planning-research Step 1: WHY with checked premises, PREDICTS, CRITERION with its cost
side, FLOOR, RIVALS, STAGE, N with `stats_floor.py`'s answer). Nothing is launched: the user picks,
then planning-research and launching-experiments take over.

## Step 6 — fresh review, then write

1. Run the fresh review of **thinking-critically** (steps 3–4). For a conclusion the reviewer gets:
   the question; as the plan, the cards' own criteria and predictions (no plan of the conclusion
   exists); the card list, the run account, the ledger and the answer's claims — not your reasoning.
   It re-checks each status against the cards' evidence and the run account. Triage its objections.
2. **Re-collect before writing**: run `collect_cards.py` again; other sessions append cards while you
   work. A new card is read and added, or listed as "after this conclusion".
3. Write the question's section in the conclusions doc (`project.yaml` → `conclusions_doc`, default
   `docs/conclusions.md`). **Rewrite it in place**, dated "as of"; the old version stays in git. It is
   a state, not a diary. The run account and the figure builder go beside it (e.g. `docs/conclusions/`).
4. Show it: the figure first, then the section right below it. Run as a subagent, return the figure
   path and the section; the main session shows them.

```markdown
## <the question, in the user's words> — as of <date>
![<the answer in one line>](<figure path>)

**Answer:** <up to 8 plain lines, each claim with its status word>.
**Data finding:** <…> · **Imposed by the setup:** <…> · **Model limitation:** <…>
**What would overturn it:** <per claim: the card's falsifier, or "none fixed before: <result>">

**Cards:** <N cards, <first date> → <last date>, by heading> · **Pooled:** <rescored / re-tallied / kept apart, which>
· **Runs:** <k runs, R replicates; excluded: …> · **Uncarded runs:** <…, or none>

| H | hypothesis | cards for · against | runs (replicates) | stage | status |
|---|---|---|---|---|---|

**Discarded:** <lever — card — reason — decisive or not>
**Contradictions / corrections:** <…, or none>
**Limits:** <seeds, one model family, verdicts within noise of the criterion> · **Reviewed:** <fresh review, date> / not reviewed
**Next (ranked):**
1. <draft pre-run card>
2. <…>
```

## Checklist (in the reply, one line: "✓ checklist" or the items that failed)
- [ ] question in the user's words; every card on it collected and read in full (not by title); uncarded runs listed
- [ ] pooling checked; each difference rescored / re-tallied / kept apart; replicates counted, not runs
- [ ] run account per hypothesis, every exclusion with its reason
- [ ] ledger with calibrated status words; "N cannot decide" written as open
- [ ] what would overturn each claim; discards with decisiveness; contradictions and corrections listed, cards not edited
- [ ] ledger figure made, checked and shown first
- [ ] 2–3 ranked next steps as draft pre-run cards, with stats_floor's N
- [ ] fresh review run; cards re-collected; section rewritten in place
