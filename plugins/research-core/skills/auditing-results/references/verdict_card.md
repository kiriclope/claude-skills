# The verdict card (auditing-results §0)

The full format of a verdict entry: what it holds, in what order, and the rules for each part.
The body of auditing-results §0 has the summary; this file is read when writing or checking a card.

## Contents
- The entry: an argument, one hypothesis at a time (template)
- Rules: chat order, figure vs table, tests that can fail, before/after the data, rivals, noise floor,
  conclusion words, next, the reader, length, independent units, clarity check, the log, corrections,
  counting cards, a missing figure

## The entry

**The entry is an argument, one hypothesis at a time; each test cites its numbers from the table.** It is
the report half of the scientific method; the plan half (hypothesis, predictions, criterion) was
written before the run by planning-research, and the entry quotes it. When the log holds the run's
open pre-run card (planning-research Step 1), write the entry under it: replace RUNNING in its heading
with the verdict and leave the card's lines unchanged — they are the record of what was fixed before.
Quote the frozen copy in the run directory (`precard.md`); if the log's card differs from it, say how
and why in the entry. An exploring card's pass is "open" until a confirming card repeats it, and a
screen (WHY "none") supports no mechanism (planning-research Step 1).

```markdown
## <date> · <what was tested, a few words>
![<the verdict in one line>](path/to/figure.png)

**Verdict:** kept / discarded / superseded / open (not decided: say who decides): <one line>, because
<H1 …, H2 …>.

**Per unit:** <the table inline when it is short, else its path>: units × tests, each cell its
number and pass/fail, the count per arm.

**Question:** <who asked, when, in their words; why it was worth testing> · **Data:** <runs or units,
by content, not arm codes> · **Plan:** <the pre-run card above this entry, or a plan § and date> or "none: the hypotheses were written after the data"

### H1 · <the hypothesis, one plain sentence that could be false> (plan <date> / after the data)
**Predicts:** if true, <what we will see>; if false, <what we will see instead>.
- **Test A: <what is compared, in plain words>.** <units, condition>. Criterion (fixed before <date> /
  exploratory / none: shown only): <…>. **Shown:** <where the figure shows it, colors by name +
  line style, or "table only">; noise floor <…>. **Result:** <k/N [95% interval], the numbers
  that decide it> → for / against H1. **Rivals:** <what else gives this result> → excluded by <control> / not excluded.
- **Test B: …**
- **Conclusion on H1:** supported / not supported / refuted / open: <how A and B decide it together>. Not shown: <…>.

### H2 · …

**Limits:** <units, seeds, reviewed or not>. **Next:** <the one experiment that would most change this>.
```
- **In the chat: the figure first, the verdict written right below it.** The reply that reports a
  verdict starts by showing the PNG (send the file with the session's file tool, or the project's
  gallery link; a bare path is not shown), then gives the whole entry in the chat itself, in this
  order. A summary in place of the entry, or the entry without the figure, is not a verdict. The log
  entry keeps the same order.
- **The figure shows the effect; the table holds the tests.** Design the figure for the problem from
  the brief in making-figures (`../../making-figures/references/figure_brief.md`, "Figures that explain a result"):
  what the system does, an example of each outcome, in the views the reader knows. It is not laid
  out by test. The per-unit table (units × tests, numbers, pass/fail, counts per arm) is saved next to
  the figure (`<figure>_table.md`), and every count in the entry comes from it. A second reason for a
  discard is a second test, a second column of the table, and is shown in the figure when it can be.
- **A test must be able to fail.** Its outcome if H is true and if H is false must differ (the
  Predicts line). A test whose outcome both predict is not a test: drop it or mark it "shown only".
- **Before or after the data, said plainly.** Quote the hypothesis and its prediction from the plan
  with the plan's date. Without a plan, write "after the data": the hypothesis is exploratory, and
  the entry never presents it as a prediction.
- **Rivals (strong inference):** for each result, name what else would produce it (noise, a
  sensitive training run that any perturbation would flip, a confound, the scorer) and the control
  that excludes it, or write "not excluded". An unexcluded rival caps the conclusion at "open".
- **Noise floor:** show what a change caused by nothing looks like: the spread over seeds, the
  rescoring noise, or a sham run (the same run with another noise seed, or the lever at weight 0).
  If none was measured, say so; a small difference without a noise floor is "open" at best.
- **Conclusion words, calibrated:** *supported* = the predicted outcome, beyond the noise floor,
  rivals excluded; *not supported* = no effect beyond the noise floor, or a test too weak to tell;
  *refuted* = the outcome H forbids, beyond the noise floor; *open* = rivals not excluded or tests
  disagree. Counts carry their exact 95% interval (`scipy.stats.binomtest(k, n).proportion_ci()`);
  two counts are compared with Fisher's exact test. **Why:** 4/6 vs 5/6 solved, one seed (Fisher
  p = 1) was first written "refuted"; it is "not supported" (2026-10-29).
- **Next:** the one experiment that would most change the conclusion, often the control that would
  exclude a rival. It is the next plan's question (planning-research).
- **Write for a reader who did not follow the session:** plain sentences, every run named by what it
  is, every symbol said once in words, only the numbers the argument needs (link the full table:
  `per-unit table: path`). Each test ends with what it means for its hypothesis. Take definitions
  from the project's docs, never invent.
- **Short: the card ≤ 40 lines,** its pre-run card included; each test ≤ 6 lines, the Question/Data
  lines ≤ 4. Detail beyond that (per-test numbers, extra checks) goes into the table file, linked.
  `collect_cards.py` (concluding-research) flags a longer card `long`. Define a term once, where it is
  first needed, not in a glossary up front. **Why:** the logs reached 260–280 kB in 6–9 days; 19 of 77
  rnn cards and 33 of 66 dual cards ran over 40 lines, the longest 155 (2026-11-04).
- **Count independent units only:** runs that share a stage (one DPA stage feeding three GNG
  versions) are one unit at that stage. **Why:** "18/18 stage ends" counted each shared DPA stage three
  times; the real count was 14/14 (2026-10-29).
- **Clarity check before reporting:** give a fresh agent the PNG, the entry and the table and
  nothing else. First, from the PNG alone, it says in one or two sentences what the figure shows: if
  that is not the verdict, redesign the figure. Then it restates, per hypothesis, the hypothesis and
  its prediction, each test's result and rivals, and the conclusion, from the entry and the table.
  Any mismatch → fix the text; at most two rounds. A question the entry
  cannot answer from its own evidence goes into "Not shown" or the Limits.
- Put the figure and the entry in the reply and add the entry to the project's verdict log (`project.yaml` →
  `verdict_log`, default `docs/verdicts.md`) **at the top, newest first** — where planning-research opens
  the pre-run cards; with a pre-run card, the entry goes under it, in place. One history of what was tried
  and why it was dropped. Older logs in mixed order stay as they are; never reorder them.
- **A correction is a new card.** The old card gets one line, never the new evidence: `Superseded
  <date> by "<new card's title>": <what changed>`. **Why:** corrections appended in full to old cards
  (11 of 76 in rnn) left the current state spread over several cards.
- **Then count the question's cards** since its section in the conclusions doc (`project.yaml` →
  `conclusions_doc`, default `docs/conclusions.md`) was last written ("as of" date), or all of them
  when it has no section: `collect_cards.py --log <log> --match "<question regex>" --since <as-of>`.
  At 5 or more, run concluding-research on that question next, and say so with the verdict.
  **Why:** rnn had one conclusions section for 76 cards, so every session rebuilt the state from the log.
- If no figure can show the effect (a crash, a missing file), say so in the figure slot and give the
  log line instead. Never leave the slot out.
