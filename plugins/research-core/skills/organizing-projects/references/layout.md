# Research repository layout

## Target layout

```
project/
├── README.md            what it is, how to run it, where results and docs live
├── CLAUDE.md            rules + doc map only (history goes to docs/)
├── .claude/project.yaml facts the shared skills read
├── src/                 package code (importable; tested)
├── scripts/             entry points by role: fig_*.py (figures), exp_*.py (analyses),
│                        *_verdict.py (scorers), run/sweep launchers
├── docs/                README.md or index.md listing every doc; logs, methods, how-tos
├── paper/               manuscript sources, figure builders, numbers script
├── assets/              hand-made sources: SVG schemes, drawings (tracked)
├── results/             outputs — ignored (or tracked selectively, by decision)
├── figures/             rendered figures — ignored, rebuilt by the scripts
└── scratchpad/          experiments; promote within ~2 weeks or delete; never imported
```

Projects that already have a different layout keep it; the rules below matter more than the
folder names.

## What git tracks and ignores

| Track | Ignore |
|---|---|
| code, configs, docs, manuscript sources | rendered figures, logs, checkpoints, caches |
| hand-made vector art (SVG schemes) and figure/page builders | files a script regenerates |
| the numbers script and small result tables a figure is built from (by decision) | large binary data (keep it in a data folder or archive, with its source noted) |

Ignore **by output folder**, not by extension: `figures/` and `results/` instead of `*.svg` or
`*.png`, which also hide hand-made sources. When an extension rule is unavoidable, add `!path`
exceptions for the sources.

## Naming

- One current version of every file — no `_v2`, `_old`, `_new`, `_final`, `_copy`, dated copies.
  Git keeps the history; a variant that must coexist gets a name that says what it is
  (`fig_flows_noise_averaged.py`), not a number.
- Scripts by role (`fig_`, `exp_`, `*_verdict`), readable names, no initialisms.
- Builders and helper scripts live in the repo, never in a temporary or job folder.

## Scratchpad

- Anything still in use after ~2 weeks is promoted: `git mv` into `scripts/` or `src/`, with a
  docstring saying what it decides and how to run it.
- Everything else is deleted (git keeps what was ever committed).
- Nothing imports from scratchpad; results quoted in docs or the paper never come from it.

## Docs and CLAUDE.md

- Every doc is listed in one index (`docs/README.md` or the CLAUDE.md doc table), with one line.
- CLAUDE.md: what the project is, the rules, the commands, the doc map. Dated history and
  results go to the docs; CLAUDE.md is read at every session start and should stay short.
