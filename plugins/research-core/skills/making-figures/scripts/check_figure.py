"""Lint a matplotlib figure for print problems before anyone looks at it.

Checks every visible Text artist of a live Figure:
  * font size at FINAL print size (scaled by print_width_mm / figure width) below `min_pt` or above
    `max_pt` (panel letters exempt from the maximum)
  * bold text that is not a panel letter (only panel letters may be bold)
  * overlapping text boxes (legend on stats line, tick labels on titles, ...)
  * text that falls outside the figure canvas (clipped on save)
  * data colors in one axes that a deuteranope/protanope cannot tell apart (via cb_style)
  * text or a legend drawn over data points (markers, scatter points)
  * one color with two meanings: across the figure's legends, a color under two labels, or a label in two colors
It also lists every number written on the figure (ticks excluded), panel by panel, to check against the
script's printed output: a typed annotation drifts from the data it describes.

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
    ax = t.axes
    title = (ax.get_title() or ax.get_title(loc='left') or ax.get_label() or '?').replace("\n", " ")[:30] if ax else ""
    where = f"ax[{title}]" if ax is not None else "fig"
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
    except ImportError:                       # say so: a silently skipped check reads as a pass
        return [("colorblind-unavailable", "colorblind check NOT run: cbstyle is not importable — "
                 "pip install \"git+https://github.com/kiriclope/claude-skills#subdirectory=python\"")]
    issues = []
    for ax in fig.axes:
        for a, b, kind, d in confusable_pairs(_data_colors(ax)):
            issues.append(("colorblind", f"ax[{ax.get_title() or '?'}]: {a} vs {b} nearly identical for "
                                         f"{kind} (ΔE {d:.0f}) — use cb_style.PAIR / OKABE_ITO or add shape/line style"))
    return issues


def _points_px(ax):
    """Display coordinates of the drawn data points of one axes: line markers and scatter offsets.
    shortcut: lines without markers are skipped (a label on a curve is often deliberate); add segments if needed."""
    import numpy as np
    pts = []
    for ln in ax.get_lines():
        if ln.get_visible() and ln.get_marker() not in (None, "", "None", " ") and len(ln.get_xydata()):
            pts.append(ax.transData.transform(ln.get_xydata()))
    for coll in ax.collections:
        off = coll.get_offsets()
        if coll.get_visible() and len(off) and len(off) == len(np.atleast_2d(off)):
            pts.append(coll.get_offset_transform().transform(off))
    pts = np.concatenate(pts) if pts else np.zeros((0, 2))
    return pts[np.isfinite(pts).all(1) & _inside(ax.bbox, pts)] if len(pts) else pts


def _inside(bb, pts):
    return (pts[:, 0] > bb.x0) & (pts[:, 0] < bb.x1) & (pts[:, 1] > bb.y0) & (pts[:, 1] < bb.y1)


def _text_on_data(fig, texts, renderer):
    """Texts inside an axes, and legends, whose box covers at least one data point of that axes."""
    issues = []
    for ax in fig.axes:
        pts = _points_px(ax)
        if not len(pts):
            continue
        own = [t for t in texts if t.axes is ax and t in ax.texts]
        leg = ax.get_legend()
        boxes = [(_label(t), t.get_window_extent(renderer)) for t in own]
        if leg is not None and leg.get_visible():
            boxes.append((f"legend in ax[{ax.get_title() or ax.get_title(loc='left') or '?'}]", leg.get_window_extent(renderer)))
        for name, bb in boxes:
            n = int(_inside(bb.padded(-1), pts).sum()) if bb.width > 2 and bb.height > 2 else 0
            if n:
                issues.append(("on-data", f"{name}: drawn over {n} data point(s)"))
    return issues


def _handle_color(h):
    from matplotlib.colors import to_hex
    for get in ("get_color", "get_markerfacecolor", "get_facecolor"):
        try:
            c = getattr(h, get)()
        except AttributeError:
            continue
        try:
            if hasattr(c, "ndim") and c.ndim == 2:
                c = c[0] if len(c) else None
            return None if c is None else to_hex(c)
        except (ValueError, TypeError):
            continue
    return None


def _handle_style(h):
    """Everything besides color that can carry a meaning: marker, fill, line style."""
    from matplotlib.colors import to_rgba
    get = lambda name, default=None: getattr(h, name)() if hasattr(h, name) else default
    face = get("get_markerfacecolor")
    try:
        hollow = face is not None and (str(face).lower() == "none" or to_rgba(face)[3] == 0 or to_rgba(face)[:3] == (1, 1, 1))
    except ValueError:
        hollow = False
    return (str(get("get_marker", "")), hollow, str(get("get_linestyle", "")), str(get("get_hatch", "")))


def _color_meanings(fig):
    """A handle style (color + marker + fill + line style) under two legend labels, or a label in two colors."""
    from matplotlib.colors import to_rgb
    legends = [ax.get_legend() for ax in fig.axes] + list(fig.legends)
    by_style, by_label = {}, {}
    for leg in legends:
        if leg is None:
            continue
        for h, t in zip(leg.legend_handles if hasattr(leg, "legend_handles") else leg.legendHandles, leg.get_texts()):
            c, lab = _handle_color(h), t.get_text().strip()
            if not c or not lab:
                continue
            r, g, b = to_rgb(c)
            if max(r, g, b) - min(r, g, b) < 0.15:            # grays carry no category
                continue
            by_style.setdefault((c,) + _handle_style(h), set()).add(lab)
            by_label.setdefault(lab, set()).add(c)
    issues = [("color-meaning", f"{k[0]} (same marker and style) means {sorted(labs)} — one color, one meaning")
              for k, labs in by_style.items() if len(labs) > 1]
    issues += [("color-meaning", f"'{lab}' is drawn in {sorted(cs)} — one meaning, one color")
               for lab, cs in by_label.items() if len(cs) > 1]
    return issues


NUMBER = re.compile(r"[-−+]?\d*[.,]?\d+(?:\s*/\s*\d+|%)?")


def _tick_label_ids(fig):
    ids = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                ids.update((id(tick.label1), id(tick.label2)))
    return ids


def _figure_numbers(fig, texts):
    """[(where, text)] for every non-tick text that contains a number."""
    ticks = _tick_label_ids(fig)
    return [(_label(t), t.get_text().replace("\n", " ")) for t in texts
            if id(t) not in ticks and NUMBER.search(t.get_text()) and not PANEL_LETTER.match(t.get_text().strip())]


def check_figure(fig, print_width_mm=183.0, min_pt=5.0, max_pt=8.0, max_overlap_frac=0.15, verbose=True):
    """Return a list of (kind, message). print_width_mm = width the figure will be printed at."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    scale = (print_width_mm / 25.4) / fig.get_figwidth()     # >1 means it will be enlarged
    fig_bb = fig.bbox
    texts = _visible_texts(fig)
    issues = []

    ticks = _tick_label_ids(fig)
    big_ticks = {}
    boxes = []
    for t in texts:
        size_print = t.get_fontsize() * scale
        if size_print < min_pt:
            issues.append(("small-font", f"{_label(t)}: {size_print:.1f} pt at print (< {min_pt})"))
        elif size_print > max_pt + 0.05 and id(t) in ticks:
            big_ticks[round(size_print, 1)] = big_ticks.get(round(size_print, 1), 0) + 1
        elif size_print > max_pt + 0.05 and not PANEL_LETTER.match(t.get_text().strip()):
            issues.append(("large-font", f"{_label(t)}: {size_print:.1f} pt at print (> {max_pt})"))
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

    issues += [("large-font", f"{n} tick labels: {pt} pt at print (> {max_pt})") for pt, n in big_ticks.items()]
    issues += _cvd_issues(fig)
    issues += _text_on_data(fig, texts, renderer)
    issues += _color_meanings(fig)
    numbers = _figure_numbers(fig, texts)

    if verbose:
        print(f"check_figure: {len(texts)} texts, print scale ×{scale:.2f} "
              f"({fig.get_figwidth():.2f} in → {print_width_mm:.0f} mm)")
        for kind, msg in issues:
            print(f"  [{kind}] {msg}")
        if numbers:
            print("NUMBERS on the figure (tick each against the script's printed output):")
            for where, txt in numbers:
                print(f"  {where.split(' in ')[-1]}: {txt[:80]}")
        print(f"SUMMARY: {len(issues)} issue(s)" + ("  ✓" if not issues else ""))
    return issues


def _demo():
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 7, "axes.titlesize": 8})                         # print sizes, as the house style
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

    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.5))
    axs[0].plot([0.5], [0.5], "o", color="#0072B2", label="Naive")
    axs[0].text(0.5, 0.5, "label on a point", fontsize=7, ha="center", va="center")      # over the point
    axs[0].legend(fontsize=7, loc="lower right")
    axs[1].plot([0, 1], [0, 1], "o", color="#0072B2", label="Lick")                      # same blue dot, new meaning
    axs[1].plot([0, 1], [1, 0], "s-", color="#D55E00", label="Naive")                    # Naive in a second color
    axs[1].legend(fontsize=7, loc="center left")
    axs[1].set_title("p = 0.04, 7/9 mice", fontsize=11, loc="left")                      # too large; numbers
    issues = check_figure(fig, print_width_mm=183)
    kinds = [k for k, _ in issues]
    assert "on-data" in kinds and kinds.count("color-meaning") == 2 and "large-font" in kinds, kinds
    assert ("p = 0.04, 7/9 mice" in [t for _, t in _figure_numbers(fig, _visible_texts(fig))])

    fig, ax = plt.subplots(figsize=(3.5, 2.5))                                           # a clean one stays clean
    ax.plot([0, 1], [0, 1], "o", color="#0072B2", label="pass")
    ax.plot([0.5], [0.2], "o", color="#0072B2", mfc="none", label="fail")                 # fill carries it: allowed
    ax.legend(fontsize=7, loc="upper left")
    ax.set_xlabel("time (s)", fontsize=7); fig.tight_layout()
    assert not [k for k, _ in check_figure(fig, print_width_mm=89, verbose=False)], "false positive"
    print("demo OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="run the built-in smoke test")
    args = ap.parse_args()
    if args.demo:
        _demo()
    else:
        ap.print_help()
