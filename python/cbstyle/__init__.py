"""Colorblind-safe palette and fixed-point markers — one standard for every project.

Rules this encodes (the reader may be colorblind; so is the author of these projects):
  * Never let hue alone carry a distinction. Pair it with shape, fill, line style or a label.
  * Binary contrasts use BLUE vs VERMILLION (separable for deutan, protan and tritan viewers);
    a second binary contrast in the same panel uses solid/dashed or filled/open, never a 2nd hue pair.
  * Up to 8 categories: Okabe-Ito order. Sequential: magma / cividis / viridis. Diverging: PuOr / RdBu.
    Never jet/rainbow, never red-vs-green.
  * Fixed points are coded by SHAPE only (white face, black edge) so they read on any colormap.

Usage:
    from cbstyle import OKABE_ITO, PAIR, FP, plot_fixed_points
    plot_fixed_points(ax, points)        # points: list of (x, y, kind)
    python -m cbstyle --demo out.png     # renders the standard + a deuteranopia/protanopia preview
"""
import argparse

import numpy as np

OKABE_ITO = {                      # Okabe & Ito 2008, the standard CVD-safe qualitative set
    "black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
    "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7",
}
CYCLE = [OKABE_ITO[k] for k in ("blue", "vermillion", "green", "orange", "sky", "purple", "yellow", "black")]
PAIR = (OKABE_ITO["blue"], OKABE_ITO["vermillion"])      # any two-class contrast (A/B, Go/NoGo, …)

# Fixed-point markers: shape carries the type; white face + black edge reads on every colormap.
_BASE = dict(markerfacecolor="white", markeredgecolor="black", markeredgewidth=0.8, linestyle="none")
FP = {
    "attractor": dict(marker="o", markersize=6.5, **_BASE),
    "saddle":    dict(marker="X", markersize=6.5, **_BASE),
    "repeller":  dict(marker="^", markersize=6.0, **_BASE),
    "marginal":  dict(marker="D", markersize=5.0, **_BASE),     # slow / non-hyperbolic / marginal
    "ghost":     dict(marker="o", markersize=6.5, markerfacecolor="none", markeredgecolor="white",
                      markeredgewidth=1.2, linestyle="none"),   # bottleneck of a vanished fixed point
}
MANIFOLD = dict(color="white", linewidth=1.6, linestyle="--")  # continuous attractor (ring, line)
FP_ALIASES = {"stable": "attractor", "slow attractor": "marginal", "slow": "marginal",
              "nonhyperbolic": "marginal", "unstable": "repeller"}


def plot_fixed_points(ax, points, legend=True, zorder=6):
    """points: iterable of (x, y, kind). Draws each kind once with the standard marker."""
    import matplotlib.patheffects as pe
    by_kind = {}
    for x, y, kind in points:
        kind = FP_ALIASES.get(kind, kind)
        by_kind.setdefault(kind, []).append((x, y))
    for kind, xy in by_kind.items():
        xy = np.asarray(xy)
        (ln,) = ax.plot(xy[:, 0], xy[:, 1], label=kind, zorder=zorder, **FP.get(kind, FP["marginal"]))
        if kind == "ghost":                            # white ring + black outline: visible on any background
            ln.set_path_effects([pe.Stroke(linewidth=2.6, foreground="black"), pe.Normal()])
    if legend and by_kind:
        leg = ax.legend(loc="lower right", frameon=True, framealpha=0.85, facecolor="0.25",
                        edgecolor="none", labelcolor="white", handletextpad=0.3, borderpad=0.4)
        leg.set_zorder(zorder + 1)
    return by_kind


def plot_manifold(ax, x, y, zorder=5):
    import matplotlib.patheffects as pe
    (ln,) = ax.plot(x, y, zorder=zorder, **MANIFOLD)
    ln.set_path_effects([pe.Stroke(linewidth=float(MANIFOLD["linewidth"]) + 1.2, foreground="black"), pe.Normal()])
    return ln


# ── color-vision-deficiency simulation (Machado, Oliveira & Fernandes 2009, severity 1.0) ──────────
_CVD = {
    "deuteranopia": np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413],
                              [-0.011820, 0.042940, 0.968881]]),
    "protanopia":   np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216],
                              [-0.003882, -0.048116, 1.051998]]),
    "tritanopia":   np.array([[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602],
                              [0.004733, 0.691367, 0.303900]]),
}


def _lin(c):
    c = np.asarray(c, float); return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _gam(c):
    c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def simulate(rgb, kind="deuteranopia"):
    """rgb in [0,1], shape (..., 3) → how a dichromat sees it."""
    return _gam(_lin(rgb) @ _CVD[kind].T)


def _lab(rgb):
    x = _lin(rgb) @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    x = x / np.array([0.95047, 1.0, 1.08883])
    f = np.where(x > 0.008856, np.cbrt(x), 7.787 * x + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def delta_e(c1, c2):
    return float(np.linalg.norm(_lab(np.asarray(c1)) - _lab(np.asarray(c2))))


def confusable_pairs(colors, min_de=12.0):
    """Pairs of colors distinct for normal vision but closer than min_de (CIELAB ΔE) for a dichromat."""
    from matplotlib.colors import to_rgb
    rgbs = [np.array(to_rgb(c)) for c in colors]
    out = []
    for i in range(len(rgbs)):
        for j in range(i + 1, len(rgbs)):
            if delta_e(rgbs[i], rgbs[j]) < min_de:
                continue                               # already similar for everyone: not a CVD issue
            for kind in ("deuteranopia", "protanopia"):
                d = delta_e(simulate(rgbs[i], kind), simulate(rgbs[j], kind))
                if d < min_de:
                    out.append((colors[i], colors[j], kind, d))
    return out


def _demo(path=None):
    if path is None:
        import os, tempfile
        path = os.path.join(tempfile.gettempdir(), "cbstyle_demo.png")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    assert not confusable_pairs(list(PAIR)), "PAIR must survive CVD"
    bad = confusable_pairs(["#d62728", "#2ca02c"])                       # classic red/green
    assert bad, "red/green should be flagged"
    yy, xx = np.mgrid[-1.5:1.5:200j, -1.5:1.5:200j]
    speed = np.hypot(xx ** 3 - xx, -yy)
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6))
    for ax, kind in zip(axs, ("normal", "deuteranopia", "protanopia")):
        img = plt.get_cmap("magma")(speed / speed.max())[..., :3]
        ax.imshow(img if kind == "normal" else simulate(img, kind), extent=(-1.5, 1.5, -1.5, 1.5), origin="lower")
        plot_fixed_points(ax, [(-1, 0, "attractor"), (1, 0, "attractor"), (0, 0, "saddle"),
                               (0, 1.1, "repeller"), (0.6, -1.0, "marginal"), (-0.6, -1.0, "ghost")],
                          legend=False)
        t = np.linspace(0, 1, 50)
        for c, ls in zip(PAIR, ("-", "--")):
            cc = c if kind == "normal" else simulate(np.array(to_rgb(c)), kind)
            ax.plot(-1.3 + 0.8 * t, 1.3 - 0.3 * t * (1 if ls == "-" else 2), color=cc, ls=ls, lw=1.5)
        ax.set_title(kind, fontsize=8, loc="left"); ax.set_xticks([]); ax.set_yticks([])
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h[:6], l[:6], loc="lower center", ncol=6, fontsize=7, frameon=False, bbox_to_anchor=(0.5, -0.06))
    fig.savefig(path, dpi=200, bbox_inches="tight")
    print(f"red/green flagged: {[(a, b, k, round(d, 1)) for a, b, k, d in bad]}")
    print(f"wrote {path}\nSUMMARY: demo OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", metavar="OUT_PNG", help="render the standard with CVD previews")
    a = ap.parse_args()
    _demo(a.demo) if a.demo else ap.print_help()
