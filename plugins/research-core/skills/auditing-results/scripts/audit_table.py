"""Helpers that make the usual result-reporting mistakes visible.

  per_unit_table(rows, ...)   one row per unit (seed / subject / session) + "SUMMARY: k/N pass" — never a mean alone
  flat_columns(rows, ...)     columns whose spread is tiny relative to their scale: the tell of a normalization
                              that removed the quantity being measured (or a bug that ignores its input)
  matched_n(stat, clouds,...) recompute a statistic on point clouds subsampled to the SAME n (smallest cloud),
                              so a comparison cannot be driven by trial count (e.g. participation ratio grows with n)
  participation_ratio(X)      PR of a (n_points, n_dims) cloud — a common n-sensitive geometry statistic

Import:
    import sys; sys.path.insert(0, "<skill_dir>/scripts")
    from audit_table import per_unit_table, flat_columns, matched_n

Self-test:  python audit_table.py --demo
"""
import argparse
import math

import numpy as np


# ── per-unit table ──────────────────────────────────────────────────────────

def per_unit_table(rows, cols=None, unit="unit", passes=None, fmt="+.2f", title=None):
    """Print rows (list of dicts, each with key `unit`) as an aligned table, one line per unit.

    passes: optional callable row -> bool (the success criterion written BEFORE looking).
    Returns (k_pass, N). The mean is printed only as an aside under the table.
    """
    if not rows:
        print("per_unit_table: no rows"); return 0, 0
    cols = cols or [k for k in rows[0] if k != unit]
    w_u = max(len(unit), *(len(str(r[unit])) for r in rows))

    def cell(v):
        if isinstance(v, (float, np.floating)):
            return "nan" if math.isnan(v) else format(float(v), fmt)
        return str(v)

    widths = {c: max(len(c), *(len(cell(r.get(c, ""))) for r in rows)) for c in cols}
    if title:
        print(title)
    head = f"{unit:<{w_u}}  " + "  ".join(f"{c:>{widths[c]}}" for c in cols) + ("  pass" if passes else "")
    print(head); print("-" * len(head))
    k = 0
    for r in rows:
        ok = bool(passes(r)) if passes else None
        k += bool(ok)
        line = f"{str(r[unit]):<{w_u}}  " + "  ".join(f"{cell(r.get(c, '')):>{widths[c]}}" for c in cols)
        print(line + (f"  {'✓' if ok else '✗'}" if passes else ""))
    num = [c for c in cols if all(isinstance(r.get(c), (int, float, np.integer, np.floating)) for r in rows)]
    if num:
        print("  (aside, mean ± sd: " + ", ".join(
            f"{c} {np.nanmean([r[c] for r in rows]):{fmt}} ± {np.nanstd([r[c] for r in rows]):.2f}" for c in num) + ")")
    if passes:
        print(f"SUMMARY: {k}/{len(rows)} {unit}s pass")
    return k, len(rows)


# ── flat-column detector ────────────────────────────────────────────────────

def flat_columns(rows, cols=None, rel_tol=0.01, min_rows=3, verbose=True):
    """Return numeric columns whose (max - min) / max(|mean|, eps) < rel_tol across ≥ min_rows rows.

    A geometry / effect statistic that is (nearly) identical across sets, stages or subjects is
    more often an artifact (per-set z-scoring, a constant normalization, an unused input) than a
    finding. Each flagged column must be explained before the table is reported.
    """
    if len(rows) < min_rows:
        return []
    cols = cols or list(rows[0])
    flagged = []
    for c in cols:
        vals = [r.get(c) for r in rows]
        if not all(isinstance(v, (int, float, np.integer, np.floating)) for v in vals):
            continue
        v = np.asarray(vals, float); v = v[np.isfinite(v)]
        if len(v) < min_rows:
            continue
        spread = v.max() - v.min(); scale = max(abs(v.mean()), 1e-12)
        if spread / scale < rel_tol:
            flagged.append(c)
            if verbose:
                print(f"  [flat] '{c}' ≈ {v.mean():.4g} in all {len(v)} rows (spread {spread / scale:.2%}) — "
                      f"normalization artifact or ignored input? explain before reporting")
    return flagged


# ── matched-n control ───────────────────────────────────────────────────────

def participation_ratio(X):
    """PR = (Σλ)² / Σλ² of the covariance of a (n_points, n_dims) cloud."""
    X = np.asarray(X, float); X = X - X.mean(0)
    lam = np.linalg.svd(X, compute_uv=False) ** 2
    return float(lam.sum() ** 2 / (lam ** 2).sum())


def matched_n(stat, clouds, n=None, n_draws=20, seed=0):
    """stat evaluated on each cloud subsampled (without replacement) to the same n.

    clouds: dict name -> (n_points, n_dims) array. n defaults to the smallest cloud.
    Returns dict name -> (mean, sd) over draws, and prints raw vs matched side by side.
    """
    rng = np.random.default_rng(seed)
    n = n or min(len(X) for X in clouds.values())
    out = {}
    print(f"matched_n: n = {n} points per cloud, {n_draws} draws")
    for name, X in clouds.items():
        X = np.asarray(X)
        vals = [stat(X[rng.choice(len(X), n, replace=False)]) for _ in range(n_draws)]
        out[name] = (float(np.mean(vals)), float(np.std(vals)))
        print(f"  {name:<12} n_raw {len(X):>5}  raw {stat(X):8.3f}   matched {out[name][0]:8.3f} ± {out[name][1]:.3f}")
    return out


# ── demo / self-test ────────────────────────────────────────────────────────

def _demo():
    rng = np.random.default_rng(1)

    # 1. a mean hides the one seed that works
    rows = [dict(seed=f"s{i}", well_k1=v, depth_sigma=v / 0.37) for i, v in enumerate([+0.30, +0.25, -1.30, +0.28])]
    k, N = per_unit_table(rows, unit="seed", passes=lambda r: r["depth_sigma"] < -1, title="well depth per seed")
    assert (k, N) == (1, 4)

    # 2. per-cloud z-scoring makes the radius a constant → flat column
    tab = []
    for stage, scale in (("naive", 1.0), ("expert", 3.0), ("late", 0.5)):
        X = rng.normal(size=(100, 50)) * scale
        Z = (X - X.mean(0)) / X.std(0)
        tab.append(dict(stage=stage, radius_raw=np.linalg.norm(X - X.mean(0), axis=1).mean(),
                        radius_z=np.linalg.norm(Z, axis=1).mean()))
    flagged = flat_columns(tab, rel_tol=0.05)
    assert flagged == ["radius_z"], flagged

    # 3. PR grows with trial count: same distribution, different n
    d = 60; C = np.diag(1.0 / np.arange(1, d + 1))
    clouds = {"small_set": rng.normal(size=(40, d)) @ C, "large_set": rng.normal(size=(400, d)) @ C}
    raw = {k: participation_ratio(v) for k, v in clouds.items()}
    m = matched_n(participation_ratio, clouds, n_draws=30)
    assert raw["large_set"] > raw["small_set"] * 1.1, raw                     # the artifact
    assert abs(m["large_set"][0] - m["small_set"][0]) < 3 * max(m["large_set"][1], m["small_set"][1]) + 0.5, m
    print("demo OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="run the built-in self-test")
    if ap.parse_args().demo:
        _demo()
    else:
        ap.print_help()
