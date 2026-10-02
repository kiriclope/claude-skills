---
name: figure-gallery
description: Publish figures to Leon's local dual figure-gallery so they show up at http://localhost:8000 (viewed over an SSH tunnel). Use when he says "upload/publish/push the figures to the gallery / to localhost / to the server", or wants to view figures from any project (rnn, dual, …) in the browser gallery. Converts PDFs→PNG (the gallery is PNG-only), stages them into a gitignored folder under ~/dual/, and makes sure the server is running. Shared skill — works from every project.
---

# Figure gallery — publish to localhost

Leon browses figures through a live gallery: **`~/dual/serve_figures.py`** walks everything under
`~/dual/` and serves every **PNG** it finds at **`http://127.0.0.1:8000`**, grouped by folder,
newest-first. It binds localhost only; he views it from his laptop over an SSH tunnel
(`ssh -L 8000:localhost:8000 <box>`). The server **re-scans the filesystem on every request** — so
once a PNG lands under `~/dual/`, it appears on a browser refresh. **No restart, no HTTP upload.**

"Upload figures to localhost" therefore means: **get PNGs into a folder under `~/dual/`.** This skill
does that cleanly (PDF→PNG conversion, a gitignored staging area, and a server-liveness check) so it
works identically whether the figures come from `~/rnn`, `~/dual`, or anywhere else.

## Facts (verified 2026-07-20)

- Gallery script: `~/dual/serve_figures.py`, default port **8000**, binds `127.0.0.1` only.
- Runs under the dual env: **`/home/leon/mambaforge/envs/dual/bin/python`**.
- **PNG only** — SVGs/PDFs are ignored by the gallery. Convert first.
- `~/dual/.gitignore` ignores `*.pdf *.svg *.pyc *.pkl *.pth` but **NOT `*.png`** → raw PNGs dropped
  into the dual repo would show up in its git status. Stage under a **top-level folder named after the
  origin project** (`~/dual/rnn/`, `~/dual/<project>/`, …) and keep that path gitignored (step 1) so
  publishing never pollutes the dual repo.
- Converters present: `pdftoppm` (best for multi-page PDFs), `magick`/`convert`.

## Step 0 — pick project and source

- **project** = the origin project = top-level folder under the gallery: `rnn`, `dual`, … Target base =
  `~/dual/<project>/`.
- **source** = the figures to publish: a directory tree (e.g. `~/rnn/results/figures/`).

**Layout Leon wants (per-sweep, per-plot-type):** `~/dual/<project>/<sweep>/<type>/` where `<type>` ∈
{`accuracy`, `flow`, `traj`, `scatter`, …} classified from the filename, and the **seed is encoded into
the filename** (`<seed>_<name>.png`, seed = the `individual/<seed>/` component or `summary`). This gives
tidy gallery cards like `sweep_r2_newtgt / flow`, `sweep_r2_newtgt / traj`, filterable by seed. (He tried
flat-one-folder and preferred this nesting — keep the sweep/type subfolders.)

## Step 1 — one-time: gitignore the project's folder

```bash
grep -qxF '<project>/' ~/dual/.gitignore || echo '<project>/' >> ~/dual/.gitignore
mkdir -p ~/dual/<project>
```

## Step 2 — convert to PNG + stage

The plot scripts already emit PNGs (plot_sweep.py / rank3_flow.py save PNG+SVG via `save_fig`). Copy the
tree into per-sweep/per-type subfolders, encoding the seed into the filename:
```bash
cd <source-root>            # e.g. ~/rnn/results/figures
classify() { case "$1" in
    *accuracy*)                                      echo accuracy;;
    *fp_scatter*|*_scatter_*)                        echo scatter;;
    *flow*|*fp_dpa*|*fp_naive*|*fp_expert*|*rank3_*) echo flow;;
    *traj*)                                          echo traj;;
    *)                                               echo misc;; esac; }
for sweep in <sweep-dirs>; do
  find "$sweep" -name '*.png' | while read -r f; do
    rel="${f#$sweep/}"; name=$(basename "$f")
    [[ "$rel" == individual/* ]] && seed=$(echo "$rel" | cut -d/ -f2) || seed=summary
    dest=~/dual/<project>/$sweep/$(classify "$name"); mkdir -p "$dest"
    cp "$f" "$dest/${seed}_${name}"
  done
done
```
Idempotent — same names overwrite, so re-running picks up newly-rendered figures.

Only-have-PDFs case — `pdftoppm -png -r 150 in.pdf out_prefix` first (150 dpi screen default; `-r 200`
for dense multi-panel), then classify/copy as above.

## Step 3 — ensure the gallery is running

```bash
pgrep -f serve_figures.py >/dev/null && echo "gallery already up" || \
  ( nohup /home/leon/mambaforge/envs/dual/bin/python ~/dual/serve_figures.py --port 8000 \
        >~/dual/.gallery.log 2>&1 & echo "started gallery on :8000" )
```
If it was already up, do nothing — it re-scans per request, so the new folder is live on refresh.

## Step 4 — report

Tell Leon: how many PNGs published, and the URL — **`http://localhost:8000`** (open the single
`<project>` folder; use the filter box to narrow, e.g. by seed/stage/plot-type). If you had to start
the server, remind him of the tunnel:
`ssh -L 8000:localhost:8000 <box>`.

## Notes

- Re-publishing the same `<label>` overwrites in place; the gallery cache-busts by mtime, so a
  refresh shows the new version.
- Keep sets reasonable — the gallery handles ~2000 figures repo-wide but stays snappiest with
  focused folders.
- For a **shareable, self-contained** page instead of the live localhost gallery, use
  `~/dual/publish_figures.py --match <regex> --out <file>.html` (bakes PNGs into one HTML) — that's
  the cloud-publish path, distinct from this localhost one.
