---
name: making-figures
description: Colorblind-safe house conventions and a render-check-look loop for scientific figures (matplotlib) — paper panels, supplements, analysis plots, flow fields, sweep summaries. Use BEFORE writing or editing any plotting code, when asked to make/fix/restyle a figure or panel, to prepare figures for submission, or when a figure "looks off". Covers style, content rules (real data, one representative example), file formats, and an automatic checker for small fonts, stray bold, overlapping/clipped text and colors a colorblind reader cannot separate. Takes precedence over generic charting skills (e.g. dataviz) for any scientific or matplotlib figure. Not for publishing pages → publishing-drafts.
---

# Making figures

A figure is finished when it has been **rendered, checked by script, and looked at** — not when
the code runs. Most figure rework in the past came from four things: ignoring the project's
existing plotting code, a style that drifted from the main figures, panels that summarized
instead of showing data, and reporting a figure nobody had looked at.

## Step 0 — load the project's conventions (do not skip)

```bash
cat .claude/project.yaml 2>/dev/null | sed -n '/figure/,/^$/p'
```
- `figure_style:` → the project's style file; else use `references/paper.mplstyle` (this skill).
- `figure_docs:` → read them now (plotting how-tos, color semantics, marker legends).
- `figure_code:` → the project's existing plotting helpers. **Reuse them.** Do not hand-roll a
  plotter for something the project already draws (flow fields, fixed points, trajectories);
  re-implementations have silently dropped panels and invented fake structure.

If none exist, grep for `def save_fig`, `def plot_`, `rcParams` before writing anything.

## Step 1 — decide the content

- **Show the data, not a summary of it.** Results panels are matrices, scatters with every
  unit, traces, spectra. A derived "summary graphic" that re-encodes the conclusion is not
  evidence; distillation goes in the text and caption. Schematics are for methods/task panels,
  full-size, never as micro-insets.
- **One representative example per single-network/single-subject panel.** Name it in the title
  if it is not the default (e.g. seed 0). No overlays of other examples' markers. Population
  statistics go in their own panel, unit by unit (per seed / per mouse), not as a mean alone.
- **Main figures read in the field's terms** (task, neurons, behavior, population dynamics).
  Diagnostics (residuals, convergence, spectra of a fit) go to the supplement.
- **Too busy?** Trim within the real-data format (fewer conditions, move the rest to the
  supplement) — do not switch format.
- **Every panel must support exactly the claim its caption makes.** If you cannot state that
  claim in one sentence, the panel is not ready.

### Evidence figures (the figure behind a verdict — auditing-results §0)

An evidence figure walks the user through one verdict entry: the same hypotheses, the same tests,
in the same order. It is not a paper panel: build it fast, but a reader who did not follow the
session must understand it with the entry beside it.
- **Laid out by the argument, not by the data:** one row per hypothesis, headed by it, one panel per
  test, lettered A, B, … in the order the entry cites them (Test A ↔ Fig. A). Use
  `cbstyle.evidence_figure(rows, verdict)`; it returns `{"A": ax, …}`. **Why:** a 3 × 3 grid by
  arm put the first claim in the last row and gave the text nothing to point at (2026-10-29).
- **Each panel title is its test and its result**, in plain words, on two lines ("Does the drug lower
  the threshold? / 7/8 mice lower"), set with `ax.set_title(…, loc="left")`; this overrides Step 2's
  short orienting titles. Axis labels in words, with units.
- **Every unit** (seed / mouse / session) as its own point or trace. A mean can go on top,
  but never alone.
- **The criterion drawn in the panel that tests it**: a threshold line, the chance level or null
  band, the target region. Label it ("criterion 0.95", "shuffle 95%"). A paired criterion (with vs
  without, before vs after) has no line to draw: join each unit's pair with a gray line (pass = it
  moves the right way) or plot the difference against a labeled 0 line.
- **The noise floor drawn next to the effect:** a band for what a change caused by nothing looks
  like (seed spread, rescoring noise, a sham run), labeled. If none was measured, the panel says so.
- **One encoding for the whole figure:** a color, line style or shape means the same thing in every
  panel. Pass vs fail = `cbstyle.PASS` (filled circle) / `cbstyle.FAIL` (open square) with the arm's
  `color=` (markersize may shrink in dense clusters), never color alone; arms or conditions go to
  color (+ line style or x position), never to a second set of shapes. One legend.
- **The main title is the verdict, in one line** ("design2 → discarded: w1 one side per seed; w4
  loses GNG"). Numbers and caveats belong in the entry, not the title.
- **Few panels:** ≤ 6. For a discard, show the failure itself (the run that diverged, the null band
  that swallows the effect, the seed that misses). A cost (accuracy lost, instability) is a test
  of its own with its own panel. **Why:** w4 was discarded for losing the Go/NoGo task, but the
  figure showed only depth, where w4 looked like a success.
- **No abbreviation without a key in the figure**, and fix every `check_figure` overlap
  before reporting.
- A conclusion across verdicts (concluding-research) uses its own one-panel ledger figure instead.
- Save it next to the run's outputs (or under `figures_root`/verdicts/), then render,
  check and look at it as in Step 3; the clarity check of auditing-results §0 reads it with the entry.

## Step 2 — style (one style for main AND supplementary figures)

```python
plt.style.use(STYLE)          # AFTER all project imports (some set seaborn context at import)
```
- Size the canvas at **final print width** (single column 89 mm, double 183 mm) so the font
  sizes in the style are the printed sizes. If you must draw larger, scale every font by
  `print_width / canvas_width`.
- Text: 5–8 pt at print. **Only panel letters are bold** (lowercase for Nature journals).
  Titles left-aligned, plain, short, orienting ("DPA · sample code") — claims go in the caption.
- Label axes with quantity, unit and the trial subset ("Δ accuracy, DPA trials"); state the
  unit of n ("9 mice", "8 seeds").
- Per-unit scatters: every point visible, thin white edge; no oversized mean markers hiding
  the points.
- **Colorblind-safe, always** (readers and authors may be colorblind). Use `scripts/cb_style.py`:
  hue never carries a distinction alone — pair it with shape, fill or line style.
  - the project's map (`project.yaml` → `colors:`) wins over these defaults;
  - default two-class contrast (A/B, left/right): `PAIR` = blue `#0072B2` vs vermillion `#D55E00`;
    a second contrast in the same panel takes the project's second pair (e.g. Go/NoGo sky / orange)
    AND a second cue (solid/dashed or filled/open) — never hue alone;
  - up to 8 categories: `OKABE_ITO` / `CYCLE`; sequential: magma / cividis / viridis;
    diverging: PuOr / RdBu centered on the true zero; never jet/rainbow, never red vs green;
  - fixed points by SHAPE (white face, black edge; `plot_fixed_points`): ● attractor, ✖ saddle,
    ▲ repeller, ◆ marginal/slow, ◎ ghost; continuous attractor = dashed white line (`plot_manifold`).
  - A project's condition → color map is defined once in `project.yaml` → `colors:` and must
    pass `check_figure`'s colorblind check. Import colors from `cbstyle` (`pip install -e
    ~/claude-skills/python`) — never re-type hex codes in figure scripts.
- Axis limits must contain every feature the claim is about (attractors, wells, the full
  distribution) — check them, don't inherit them.

## Step 3 — render, check, look (loop until clean)

1. Save through the project's `save_fig` or as **PNG (review/gallery) + vector (SVG/PDF for
   submission)**, with editable text (`svg.fonttype none`, `pdf.fonttype 42`).
2. Run the checker before saving:
   ```python
   sys.path.insert(0, "<this skill dir>/scripts"); from check_figure import check_figure
   check_figure(fig, print_width_mm=183)     # small fonts, stray bold, overlaps, clipping, colorblind
   ```
3. **Open the PNG with the Read tool and look at it.** Check: every panel present and in
   order, legends not covering data, markers distinguishable, limits not clipping features,
   numbers on the figure match the script's printed output.
4. Fix and repeat. Report only after a clean pass, and show (or publish) the figure — never
   report figure numbers without the figure.

## Captions and text

See `references/captions.md` (caption skeleton, panel inventory, shared vocabulary).

## Checklist (check before reporting; in the reply, one line: "✓ checklist" or the items that failed)
- [ ] project conventions/helpers loaded and reused
- [ ] content: real data, one named representative example, claim per panel
- [ ] style file applied; same style as the main figures
- [ ] `check_figure` clean
- [ ] PNG opened and inspected; numbers match the script output
- [ ] PNG + vector saved; figure shown/published
