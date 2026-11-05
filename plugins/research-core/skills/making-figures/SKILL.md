---
name: making-figures
description: Colorblind-safe house conventions and a render-check-look loop for scientific figures (matplotlib) — paper panels, supplements, analysis plots, flow fields, sweep summaries. Use BEFORE writing or editing any plotting code, when asked to make/fix/restyle a figure or panel, to prepare figures for submission, or when a figure "looks off". Covers style, content rules (real data, one representative example), file formats, and an automatic checker for small fonts, stray bold, overlapping/clipped text and colors a colorblind reader cannot separate. Takes precedence over generic charting skills (e.g. dataviz) for any scientific or matplotlib figure. Not for publishing pages → publishing-drafts.
---

# Making figures

A figure is finished when it has been **rendered, checked by script, and looked at** — not when
the code runs. Most figure rework in the past came from four things: ignoring the project's
existing plotting code, a style that drifted from the main figures, panels that summarized
instead of showing data, and reporting a figure nobody had looked at.

## Who does which step (decide before delegating)

| Step | Who | Why |
|---|---|---|
| run the plotting script on existing code (flags, run IDs) | a cheap dispatcher agent (`model: haiku`), or the session inline for one short run | mechanical; the GPU, not the model, is the cost |
| catch layout faults (overlaps, clipping, fonts, colorblind) | `check_figure`, called inside the project's `save_fig` | a script check costs no tokens and does not depend on which model ran it |
| report the check | the dispatcher relays `check_figure`'s warnings **verbatim** + the file paths; it never says a figure "looks fine" | a weak "fine" makes the session skip the look, and whoever made the output tends to confirm it |
| write or change plotting code | the session, or a coding agent (`sonnet`); the session model if the change spans several files | coding, not dispatch |
| look (Step 3.3) | the session that will report or conclude, on the 1–2 figures that back a claim | judging what a figure shows is where the strong model pays; `check_figure` covers the bulk of per-run figures |

Delegate the run when it is long, noisy or repeated (picking run IDs, several sweeps, retries): the
saving is keeping that output out of the session's context, more than the per-token price. A single
short plot command is about as cheap inline as the hand-off itself. If the project's `save_fig` does
not call `check_figure` yet, add it (Step 3.2) before routing runs to a cheap model.

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
  evidence; distillation goes in the text and caption. A schematic (labeled as one) may explain
  beside the data, never replace it; full-size, never as micro-insets.
- **One representative example per single-network/single-subject panel.** Name it in the title
  if it is not the default (e.g. seed 0). No overlays of other examples' markers. Population
  statistics go in their own panel, unit by unit (per seed / per mouse), not as a mean alone.
- **Main figures read in the field's terms** (task, neurons, behavior, population dynamics).
  Diagnostics (residuals, convergence, spectra of a fit) go to the supplement.
- **Too busy?** Trim within the real-data format (fewer conditions, move the rest to the
  supplement) — do not switch format.
- **Every panel must support exactly the claim its caption makes.** If you cannot state that
  claim in one sentence, the panel is not ready.

### Figures that explain a result (a verdict, a conclusion, a paper panel): designed, not templated

**The figure shows the effect itself; the test tally is a table.** What the system does (its dynamics,
its curves, its outputs, an example of each outcome) is the figure; which unit passed which test is
the per-unit table under it (auditing-results §0). **Why:** verdict figures built as one derived number
per seed against a threshold line, with filled/open markers and count-sentence titles, were cryptic to
the user in every project (2026-11-03: "not well polished… very cryptic", "as bad in other sessions").
Rebuilt to show the effect, the same results showed what the dots had hidden: wells pushed down while
the trials went up, and a width trend that the stated explanation did not fit.

**Design it from the problem.** Hand a fresh agent the brief in `references/figure_brief.md` (or follow
it yourself): the reader, the problem, the data, and four sources the design draws on:
1. knowledge of the problem: the mechanism, and the picture that would make it obvious;
2. the literature: how published work on this problem shows such a result (a few searches, the
   figures borrowed from named, references verified);
3. the user's propositions: the views and ideas the user asked for or liked, in their words;
4. the project's own work: its views and the code that draws them (`project.yaml` → `figure_views`,
   `figure_code`), paper figures, past figures the user approved.

The designer sketches at least three genuinely different designs, says what the reader sees in the
first 3 seconds of each, picks one and says why (`designs.md`). Then Steps 2–3. The constraints are
few: real data, colorblind-safe, every unit accounted for (figure or table), a small effect against
what no effect looks like, readable at a glance (at most two encodings, titles ≤ 2 lines; a second
message gets its own figure), the title the finding in plain words. The rest is a design call.
Don't show the designer an earlier figure of the same result (it anchors the design) unless the user
asked to improve that figure.

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
- **One color, one meaning across the whole figure**: a color + marker
  + line style means the same condition in every panel. **Why:** a submitted draft's Fig. 3 used green
  for NoGo in one panel and for Lick in the next (2026-08-30 snapshot review).
- **Numbers on the figure are formatted from the variable** (`f"{acc:.2f}"`), never typed: a typed
  "0.93" stayed on a panel after the value became 0.92.
- Axis limits must contain every feature the claim is about (attractors, wells, the full
  distribution) — check them, don't inherit them.

## Step 3 — render, check, look (loop until clean)

1. Save through the project's `save_fig` or as **PNG (review/gallery) + vector (SVG/PDF for
   submission)**, with editable text (`svg.fonttype none`, `pdf.fonttype 42`).
2. Run the checker before saving (in a project, put this call inside its `save_fig` so every
   figure is checked, whoever runs the script):
   ```python
   sys.path.insert(0, "<this skill dir>/scripts"); from check_figure import check_figure
   check_figure(fig, print_width_mm=183)     # fonts < 5 or > 8 pt, stray bold, overlaps, clipping,
                                             # colorblind, text/legend on data points, one color two meanings
   ```
   It also prints NUMBERS: every number written on the figure, panel by panel.
3. **Open the PNG with the Read tool and look at it.** Check: every panel present and in
   order, legends not covering data, markers distinguishable, limits not clipping features,
   and **tick every line of NUMBERS against the script's printed output** (a reviewer agent once drew a
   ±0.021 band where the data gave ±0.011, 2026-10-29).
4. Fix and repeat. Report only after a clean pass, and show (or publish) the figure — never
   report figure numbers without the figure.

## Captions and text

See `references/captions.md` (caption skeleton, panel inventory, shared vocabulary).

## Checklist (check before reporting; in the reply, one line: "✓ checklist" or the items that failed)
- [ ] project conventions/helpers loaded and reused
- [ ] content: real data, one named representative example, claim per panel
- [ ] style file applied; same style as the main figures
- [ ] `check_figure` clean (called from the project's `save_fig`); its NUMBERS ticked against the script output
- [ ] a delegated run reported warnings verbatim, no "looks fine"; the session looked at the key figures itself
- [ ] PNG opened and inspected; numbers match the script output
- [ ] PNG + vector saved; figure shown/published
