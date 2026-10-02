"""Lint a matplotlib figure for print problems before anyone looks at it.

Checks every visible Text artist of a live Figure:
  * font size at FINAL print size (scaled by print_width_mm / figure width) below `min_pt`
  * bold text that is not a panel letter (only panel letters may be bold)
  * overlapping text boxes (legend on stats line, tick labels on titles, ...)
  * text that falls outside the figure canvas (clipped on save)
  * data colors in one axes that a deuteranope/protanope cannot tell apart (via cb_style)

Usage inside a figure script, right before saving:

    import sys; sys.path.insert(0, "<skill_dir>/scripts")
    from check_figure import check_figure
    check_figure(fig, print_width_mm=183)        # prints a report; returns the list of issues

Or as a smoke test:  python check_figure.py --demo
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # cb_style lives next to this file

import matplotlib
from matplotlib.text import Text

PANEL_LETTER = re.compile(r"^\(?[a-zA-Z]\d?\)?$")   # a, B, (c), b1


def _undrawn_tick_labels(fig):
    """Tick labels matplotlib keeps outside the view interval (never drawn) — exclude them."""
    hidden = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            lo, hi = sorted(axis.get_view_interval())
            eps = 1e-9 * max(1.0, abs(hi - lo))
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not (lo - eps <= tick.get_loc() <= hi + eps):
                    hidden.update((id(tick.label1), id(tick.label2)))
    return hidden


def _visible_texts(fig):
    hidden = _undrawn_tick_labels(fig)
    out = []
    for t in fig.findobj(Text):
        s = t.get_text().strip()
        if s and t.get_visible() and id(t) not in hidden and (t.axes is None or t.axes.get_visible()):
            out.append(t)
    return out


def _label(t):
    s = t.get_text().replace("\n", " ")
    where = f"ax[{t.axes.get_title() or t.axes.get_label() or '?'}]" if t.axes is not None else "fig"
    return f"'{s[:40]}' in {where}"


def _data_colors(ax):
    """Distinct, saturated colors of lines and scatter points in one axes (grays ignored)."""
    from matplotlib.colors import to_hex, to_rgb
    cols = []
    for ln in ax.get_lines():
        cols.append(ln.get_color())
    for coll in ax.collections:
        fc = coll.get_facecolor()
        if len(fc) and len(fc) <= 20:
            cols += [tuple(c[:3]) for c in fc]
    out = []
    for c in cols:
        try:
            r, g, b = to_rgb(c)
        except ValueError:
            continue
        if max(r, g, b) - min(r, g, b) < 0.15:          # gray/black/white: not a hue distinction
            continue
        h = to_hex((r, g, b))
        if h not in out:
            out.append(h)
    return out


def _cvd_issues(fig):
    try:
        from cb_style import confusable_pairs
    except ImportError:
        return []
    issues = []
    for ax in fig.axes:
        for a, b, kind, d in confusable_pairs(_data_colors(ax)):
            issues.append(("colorblind", f"ax[{ax.get_title() or '?'}]: {a} vs {b} nearly identical for "
                                         f"{kind} (ΔE {d:.0f}) — use cb_style.PAIR / OKABE_ITO or add shape/line style"))
    return issues


def check_figure(fig, print_width_mm=183.0, min_pt=5.0, max_overlap_frac=0.15, verbose=True):
    """Return a list of (kind, message). print_width_mm = width the figure will be printed at."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    scale = (print_width_mm / 25.4) / fig.get_figwidth()     # >1 means it will be enlarged
    fig_bb = fig.bbox
    texts = _visible_texts(fig)
    issues = []

    boxes = []
    for t in texts:
        size_print = t.get_fontsize() * scale
        if size_print < min_pt:
            issues.append(("small-font", f"{_label(t)}: {size_print:.1f} pt at print (< {min_pt})"))
        weight = t.get_fontweight()
        is_bold = weight in ("bold", "heavy", "extra bold", "black") or (isinstance(weight, (int, float)) and weight >= 600)
        if is_bold and not PANEL_LETTER.match(t.get_text().strip()):
            issues.append(("bold", f"{_label(t)}: bold text that is not a panel letter"))
        bb = t.get_window_extent(renderer)
        if bb.width > 0 and bb.height > 0:
            if bb.x0 < fig_bb.x0 - 1 or bb.y0 < fig_bb.y0 - 1 or bb.x1 > fig_bb.x1 + 1 or bb.y1 > fig_bb.y1 + 1:
                issues.append(("clipped", f"{_label(t)}: extends outside the canvas"))
            boxes.append((t, bb))

    for i in range(len(boxes)):
        ti, bi = boxes[i]
        for j in range(i + 1, len(boxes)):
            tj, bj = boxes[j]
            if not bi.overlaps(bj):
                continue
            w = min(bi.x1, bj.x1) - max(bi.x0, bj.x0); h = min(bi.y1, bj.y1) - max(bi.y0, bj.y0)
            frac = (w * h) / min(bi.width * bi.height, bj.width * bj.height)
            if frac > max_overlap_frac:
                issues.append(("overlap", f"{_label(ti)} overlaps {_label(tj)} ({frac:.0%})"))

    issues += _cvd_issues(fig)

    if verbose:
        print(f"check_figure: {len(texts)} texts, print scale ×{scale:.2f} "
              f"({fig.get_figwidth():.2f} in → {print_width_mm:.0f} mm)")
        for kind, msg in issues:
            print(f"  [{kind}] {msg}")
        print(f"SUMMARY: {len(issues)} issue(s)" + ("  ✓" if not issues else ""))
    return issues


def _demo():
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.5))
    axs[0].plot([0, 1], [0, 1], color="#d62728"); axs[0].plot([0, 1], [1, 0], color="#2ca02c")   # red/green
    axs[0].set_title("Fine title", fontsize=8)
    axs[0].text(0.5, 0.5, "stats p = .02", fontsize=4, transform=axs[0].transAxes)       # too small
    axs[0].text(0.5, 0.52, "overlapping label", fontsize=7, transform=axs[0].transAxes)   # overlap
    axs[1].set_title("Bold claim", fontweight="bold")                                    # bold, not a letter
    fig.text(0.01, 0.95, "a", fontweight="bold", fontsize=11)                            # allowed
    issues = check_figure(fig, print_width_mm=183)
    kinds = {k for k, _ in issues}
    assert {"small-font", "overlap", "bold", "colorblind"} <= kinds, kinds
    print("demo OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="run the built-in smoke test")
    args = ap.parse_args()
    if args.demo:
        _demo()
    else:
        ap.print_help()
