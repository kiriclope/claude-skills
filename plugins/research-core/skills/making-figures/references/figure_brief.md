# Figure brief (a figure that must explain a result: a verdict, a conclusion, a paper panel)

Fill it and hand it to a fresh agent (Agent tool, general-purpose, the session's model). Or follow it
yourself. The brief gives the designer the problem and its sources, not a layout: the design is the
agent's call. Leave out what the reader already knows; keep in everything that makes the finding
true or doubtful.

```
You are designing the figure for a research result. A scientist who missed the work should
understand the result, and believe it, at a glance. Design it from your understanding of the
problem: you are not filling a template. Draw the figure a very good <field> researcher would draw
to explain this result to a colleague, first at a whiteboard, then with the real data.

## The reader
<who: their field, what views they read at a glance (e.g. flow fields, training curves, rasters),
what they find cryptic, colorblind or not>

## The problem
<the question in the user's words; the hypothesis and what it predicts; what was found, with the
numbers that decide it; the caveats, corrections and rivals still open. Point to the verdict entry
or plan; say which parts are settled and which are doubtful>

## Sources to draw on (say in designs.md which ones shaped your design)
1. Your knowledge of the problem: the mechanism, and the picture that would make it obvious.
2. The literature: how published work on this problem or method shows this kind of result. Spend a
   few searches (Semantic Scholar, OpenAlex, arXiv, PubMed) on 1–3 papers whose figures show it well,
   and name what you borrow. Verify each reference you name (verifying-citations).
3. The user's propositions: <the views and ideas the user asked for or liked, in their words, with
   dates: e.g. "show me the flows of all 24 nets"; the project memory's figure notes>.
4. The project's own work: <its views and the code that draws them (project.yaml → figure_views,
   figure_code); paper figures; past figures the user approved, with paths>. Reuse the code; do not
   hand-roll what exists.

## Data and tools
<run directories, result files, cached numbers, the per-unit table (copy it, do not redo it), how
to run code (env, device limits), what not to edit>

## How to work
1. Sketch at least THREE genuinely different designs in words: different views, not variants of
   one layout. For each, say what the reader sees in the first 3 seconds. Pick one (or a
   combination) that makes the finding most obvious AND most convincing, and say why.
2. Build it. Render, run check_figure until 0 issues, OPEN the PNG and look at it as the reader
   would, and improve it: at least two rounds of looking.
3. Hard constraints, only these:
   - real data (a schematic only if labeled as one);
   - colorblind-safe: never red vs green, never hue alone;
   - honest: every unit accounted for, on the figure or in the table; no limit that clips the
     effect without saying so; a small effect is shown against what no effect looks like (seed
     spread, a sham), or the figure says none was measured;
   - readable at print (5–8 pt), no stray bold;
   - what the eye takes in at once: at most two encodings (e.g. color = arm, line style = condition),
     panel titles ≤ 2 lines, few annotations; a second message gets its own figure rather than
     crowding this one;
   - the title is the finding in plain words.

   Not the figure: one derived number per unit against a threshold line with pass/fail markers.
   That is the table. Everything else (panels, layout, 2-D or 3-D, transforms, insets, schematics)
   is your design call.

## Deliverables in <dir> (edit nothing else)
fig.py (builder, docstring with a Usage line), <name>.png + .pdf, designs.md (the sketches, the
choice, the sources used). End with a short report: the design and why, what the reader sees first,
check_figure's last SUMMARY line, and what you could not show.
```

Before the designer starts: if the result already has a figure, do not show it (it anchors the new
design), unless the user asked for that figure to be improved rather than replaced.
