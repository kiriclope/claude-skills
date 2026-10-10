---
name: validating-claims
description: Keep a ledger of every claim a paper, talk or report makes, with the controls that could falsify it — the falsifying result written before the control runs, the command, its output, the result and a status — and check it with claims_ledger.py (controlled, failed, uncontrolled, pending, stale; claim sentences in the text with no entry). Use when a result becomes a claim in a manuscript or doc, before sharing or submitting a draft, after re-running analyses a claim rests on, or when the user asks "is this claim controlled", "what would falsify this", "did we run the shuffle / the null / more seeds / the nuisance control". Not for auditing one fresh result → auditing-results; for numbers against the numbers log → auditing-paper-numbers.
---

# Validating claims

A claim is as strong as the control that could have killed it. The ledger makes that visible:
every claim, the controls its kind requires, what result would have refuted it, and whether
that control was run on the current data.

## Rules

- **Write `falsifies_if` before running the control**: the result (number and direction) that
  would refute the claim. Never edit it after seeing the result. If it was the wrong test, add a
  new control and keep the old one with its status.
- **A control that comes out against the claim changes the claim** (weaken, qualify, remove),
  never the control. Record the new wording.
- **The claim's kind sets the controls it needs** (defaults; a project can extend them under
  `validation: required:` in `.claude/project.yaml`):

  | Kind | The claim says | Required | Typical control |
  |---|---|---|---|
  | effect | X is above chance, non-zero, increases | null | label shuffle, permutation, null model, OFF-vs-OFF noise band |
  | difference | A differs from B | null, confound | list what differs besides the variable; match each or control it |
  | null-result | X does not change | positive | the method detects a planted change of the size that would matter (validating-pipelines) |
  | generalization | holds across sessions, animals, seeds, noise | held-out | fit on some units, test on the others; unseen noise levels and delays |
  | mechanism | X because of Y | ablation | remove or clamp Y; X must go, and nothing else must explain the loss |
  | correlation | X tracks Y | null, confound | shuffle; partial out the third variable (licks, running, session) |

- **Read a claim at the stage it is about.** A metric measured after a later step that retrains
  or renormalizes the quantity can hide the effect (memory retention read after a stage that
  retrains the memory). Add a `metric` control: the claim under the metric that isolates the
  stage, or under the 2–3 reasonable metrics.
- **n in the unit of the claim** (seeds, mice, sessions — not trials). Below `validation.min_n`
  (default 5) the text says exploratory.
- **The ledger records controls; it does not run them.** They come from validating-pipelines
  (positive and ground-truth controls), validating-decoders (null, leakage, nuisance, held-out
  sessions), validating-networks in the low-rank RNN projects (held-out noise, ablations), and
  auditing-results helpers (matched n, unit tables). A control that needs a new sweep or a long
  job waits for the user's go.

## Workflow

1. **Find or start the ledger**: `validation.claims_file` in `.claude/project.yaml`, else
   `<paper_dir>/claims.yaml`. To start one from a manuscript:
   ```bash
   python <this skill>/scripts/claims_ledger.py --init --text <manuscript> \
       --start '^## Abstract' --stop '^## Methods' > <paper_dir>/claims.yaml
   ```
   It lists every claim-like sentence (a statistic or a claim verb). Merge sentences that make
   one claim and delete the ones that are not claims.
2. **Fill each entry**: kind, unit, n, source (the numbers-log key or the file the number comes
   from), and one control per required type, each with `falsifies_if`, `command` and `output`:
   ```yaml
   claims:
     - id: retention
       text: "Go/No-Go training leaves the DPA memory intact"     # verbatim fragment of the manuscript
       kind: effect
       unit: seed
       n: 8
       source: paper/numbers.json:retention.after_gng_dpa
       controls:
         - name: label shuffle
           type: null
           falsifies_if: "accuracy within the shuffle's 95% band"
           command: "python analyze.py --results results/dual/x/results.jsonl --shuffle 1000"
           output: results/dual/x/shuffle.json
           result: "null 0.50 ± 0.02; 8/8 seeds above 0.80"
           status: passed            # passed | failed | pending
           date: 2026-10-09
   ```
3. **Run the pending controls** (ask before long ones) and record result, status, date, output.
4. **Check**:
   ```bash
   python <this skill>/scripts/claims_ledger.py --ledger <claims.yaml> --text <manuscript> \
       --start '^## Abstract' --stop '^## Methods'
   ```
   Resolve every line that is not CONTROLLED: FAILED → change the claim; UNCONTROLLED → add the
   control; PENDING → run it; STALE → re-run it on the current data; GONE → update or delete the
   entry; UNLEDGERED → add an entry, or confirm the sentence is not a claim.
5. **Report** one row per claim (claim · verdict · what was run or changed), then the claims
   whose wording changed, quoted before and after.

## Checklist (in the reply: "✓ checklist" or the items that failed)
- [ ] every claim in the ledger, with kind, unit and n in the unit of the claim
- [ ] every required control present, `falsifies_if` written before it ran
- [ ] `claims_ledger.py` clean, or each remaining line justified
- [ ] failed controls changed the claim's wording, not the control
- [ ] claims read at the stage they are about; metric controls where a later step could hide the effect
