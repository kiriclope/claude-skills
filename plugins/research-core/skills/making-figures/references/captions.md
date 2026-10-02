# Captions and figure text

## Caption skeleton

1. **Title = the figure's claim**, then one sentence of roadmap: how the panels build it
   ("b counts the dimensions, c shows …, f tests …").
2. **Each panel, in order:** what is plotted (axes, points, units) → how it was computed (one
   clause) → what it shows, in plain language → the statistics (test, n with its unit, p).
   Never open a panel description with numbers.
3. **One vocabulary across all figures.** Define a term at first use (in the figure where it
   first appears) and reuse the same word everywhere after; the project's glossary lives in
   `.claude/project.yaml` → `vocabulary`.
4. Cross-reference instead of re-defining ("same axes as Fig. 3a").
5. Keep caveats (excluded units, failed seeds) in the caption; do not silently drop them.

## Panel inventory (before writing results text or a caption)

Open the rendered PNG and list every panel letter and sub-panel. Each one must be:
- described in the caption, matching the actual layout (sub-panels, schematics included);
- cited at least once in the main text, in the form "(Fig. 6b, blue)" at the end of the clause.

## Numbers

Every number in a caption or on a panel comes from the script's printed output of the current
render — not from memory or an older draft. If the script does not print it, make it print it.

## Prose priorities

Argument, flow and clarity first; word limits are handled by a separate trimming pass when the
user asks for one.
