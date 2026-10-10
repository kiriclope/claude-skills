"""Ground-truth recovery: run an analysis pipeline on synthetic data with a planted effect of known size, and none.

You write a small adapter module (a .py file) next to the analysis:
    def simulate(effect, rng):  -> data with the effect planted (same n, trials, noise, nuisance as the real data)
    def estimate(data):         -> the pipeline's output: a number, or a dict {"value": x, "p": p, "ci": (lo, hi)}
optional:
    EFFECTS = [0, 0.1, 0.2, 0.4]       planted effect sizes (0 must be included: the null)
    def truth(effect): ...             what the measure SHOULD read for that effect (enables bias and slope checks)
    NULL_VALUE = 0.5                   what the measure should read with no effect, when truth() is not given
                                       (chance accuracy, a correlation of 0, a ratio of 1)
The script runs every effect `--reps` times and reports, per effect, the mean estimate, bias, s.d., the
detection rate (p < alpha) and CI coverage, then the verdicts:
  OFFSET          with no effect the measure is not where it should be (its zero is elsewhere: a baseline,
                  a positive bias of |x|, a chance level that is not 0.5)
  SHRINKAGE       the estimate grows more slowly than the truth (slope < 1 - tol): something removes the effect
                  (a per-condition normalization, regularization, averaging over the wrong axis)
  INFLATION       slope > 1 + tol
  SIGN FLIP       the estimate goes down when the effect goes up
  NOT MONOTONE    a larger planted effect gives a smaller mean estimate
  FALSE POSITIVES the null is detected more often than alpha allows (pseudoreplication, leakage, a wrong test)
  UNDERCOVERAGE   95% intervals contain the truth clearly less often than 95% (beyond 2.5 binomial s.e.)
and as information: the smallest planted effect detected with power ≥ 0.8 — the positive control a
null-result claim needs ("the pipeline would have seen an effect of this size").

Usage:
    python recovery_check.py --adapter analysis/recovery_adapter.py [--reps 50] [--effects 0 0.1 0.3] [--alpha 0.05]
    python recovery_check.py --demo
Exit 1 on any verdict above (information lines do not fail).
"""
import argparse
import importlib.util
import math
import os
import sys
import tempfile
import time

import numpy as np


def load_adapter(path):
    spec = importlib.util.spec_from_file_location("recovery_adapter", path)
    if spec is None or spec.loader is None:
        sys.exit(f"{path}: not a Python module")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(mod)
    for fn in ("simulate", "estimate"):
        if not callable(getattr(mod, fn, None)):
            sys.exit(f"{path}: the adapter must define {fn}()")
    return mod


def _as_dict(out):
    if isinstance(out, dict):
        return out
    return {"value": float(out)}


def run(mod, effects, reps, seed=0):
    """{effect: list of estimate dicts}; each repetition has its own RNG stream."""
    res = {}
    for i, e in enumerate(effects):
        res[e] = [_as_dict(mod.estimate(mod.simulate(e, np.random.default_rng([seed, i, r])))) for r in range(reps)]
    return res


def summarize(res, truth, null_value, alpha):
    rows = []
    for e, outs in res.items():
        v = np.array([o["value"] for o in outs], float)
        t = truth(e) if truth else (null_value if e == 0 else None)
        ps = [o["p"] for o in outs if o.get("p") is not None]
        cis = [o["ci"] for o in outs if o.get("ci") is not None]
        rows.append({"effect": e, "truth": t, "mean": v.mean(), "sd": v.std(ddof=1) if len(v) > 1 else 0.0,
                     "se": v.std(ddof=1) / math.sqrt(len(v)) if len(v) > 1 else 0.0, "n": len(v),
                     "detect": (np.mean([p < alpha for p in ps]) if ps else None),
                     "cover": (np.mean([lo <= t <= hi for lo, hi in cis]) if cis and t is not None else None)})
    return rows


def verdicts(rows, alpha, slope_tol=0.2, offset_sd=0.25):
    """[(VERDICT, detail)] failures and [(INFO, detail)] information."""
    fails, info = [], []
    null = next((r for r in rows if r["effect"] == 0), None)
    if null is None:
        fails.append(("NO NULL", "effect 0 is not in the planted effects: the null cannot be checked"))
    elif null["truth"] is not None:
        off = null["mean"] - null["truth"]
        if abs(off) > max(3 * null["se"], offset_sd * null["sd"]):
            fails.append(("OFFSET", f"no effect planted, the measure reads {null['mean']:.3g} ± {null['se']:.2g} "
                                    f"(should be {null['truth']:.3g}; offset {off / max(null['sd'], 1e-12):+.2f} s.d.)"))
    if null is not None and null["detect"] is not None:
        n = null["n"]
        bound = alpha + 2.5 * math.sqrt(alpha * (1 - alpha) / n)
        if null["detect"] > bound:
            fails.append(("FALSE POSITIVES", f"null detected in {null['detect']:.0%} of {n} runs "
                                             f"(alpha {alpha}, allowed ≤ {bound:.0%})"))
    with_t = [r for r in rows if r["truth"] is not None]
    if len(with_t) >= 2 and len({r["truth"] for r in with_t}) >= 2:
        x = np.array([r["truth"] for r in with_t])
        y = np.array([r["mean"] for r in with_t])
        slope = np.polyfit(x, y, 1)[0]
        if slope < -slope_tol:
            fails.append(("SIGN FLIP", f"slope {slope:.2f}: the estimate falls as the planted effect grows"))
        elif slope < 1 - slope_tol:
            fails.append(("SHRINKAGE", f"slope {slope:.2f}: the estimate recovers {slope:.0%} of the planted effect"))
        elif slope > 1 + slope_tol:
            fails.append(("INFLATION", f"slope {slope:.2f}"))
        for r in with_t:                                 # 95% nominal, minus 2.5 binomial s.e. at this many runs
            if r["cover"] is not None and r["cover"] < 0.95 - 2.5 * math.sqrt(0.95 * 0.05 / r["n"]):
                fails.append(("UNDERCOVERAGE", f"effect {r['effect']:g}: 95% CI covers the truth in {r['cover']:.0%}"))
    means = [r["mean"] for r in sorted(rows, key=lambda r: r["effect"])]
    tol = 2 * max(r["se"] for r in rows)
    if any(b < a - max(tol, 1e-9 * (1 + abs(a))) for a, b in zip(means, means[1:])) and \
            not any(f[0] == "SIGN FLIP" for f in fails):
        fails.append(("NOT MONOTONE", "a larger planted effect gives a smaller mean estimate: "
                                      + ", ".join(f"{m:.3g}" for m in means)))
    powered = [r["effect"] for r in sorted(rows, key=lambda r: r["effect"])
               if r["effect"] != 0 and r["detect"] is not None and r["detect"] >= 0.8]
    if any(r["detect"] is not None for r in rows):
        info.append(("DETECTABLE", f"smallest planted effect detected with power ≥ 0.8: {powered[0]:g}" if powered
                     else "no planted effect reaches power 0.8: a null result from this pipeline is not evidence "
                          "of absence at these sizes"))
    return fails, info


def report(name, rows, fails, info, secs):
    print(f"GROUND-TRUTH RECOVERY · {name} · {rows[0]['n']} runs per effect · {secs:.1f} s")
    print(f"  {'effect':>8} {'truth':>8} {'mean':>9} {'bias':>8} {'s.d.':>8} {'detect':>7} {'cover':>6}")
    for r in rows:
        t = "—" if r["truth"] is None else f"{r['truth']:.3g}"
        bias = "—" if r["truth"] is None else f"{r['mean'] - r['truth']:+.3g}"
        det = "—" if r["detect"] is None else f"{r['detect']:.0%}"
        cov = "—" if r["cover"] is None else f"{r['cover']:.0%}"
        print(f"  {r['effect']:>8g} {t:>8} {r['mean']:>9.3g} {bias:>8} {r['sd']:>8.3g} {det:>7} {cov:>6}")
    for v, d in fails:
        print(f"  ✗ {v}: {d}")
    for v, d in info:
        print(f"  · {v}: {d}")
    print(f"SUMMARY: {'FAIL — ' + ', '.join(v for v, _ in fails) if fails else 'PASS — recovers the planted effects'}")


def check(path, effects=None, reps=50, alpha=0.05, seed=0, quiet=False):
    mod = load_adapter(path)
    effects = effects or list(getattr(mod, "EFFECTS", [])) or sys.exit("no effects: set EFFECTS or --effects")
    t0 = time.time()
    res = run(mod, effects, reps, seed)
    rows = summarize(res, getattr(mod, "truth", None), getattr(mod, "NULL_VALUE", 0.0), alpha)
    fails, info = verdicts(rows, alpha)
    if not quiet:
        report(os.path.basename(path), rows, fails, info, time.time() - t0)
    return fails, info, rows


DEMO = {
    "good.py": '''
import numpy as np
from scipy import stats
EFFECTS = [0, 0.2, 0.5, 1.0]
def truth(e): return e
def simulate(e, rng):                       # 8 subjects x 2 conditions; the effect is a subject-level difference
    base = rng.normal(0, 1, 8)
    return base + e + rng.normal(0, 0.5, 8), base + rng.normal(0, 0.5, 8)
def estimate(d):
    a, b = d
    diff = a - b
    t = stats.ttest_rel(a, b)
    half = stats.t.ppf(0.975, len(diff) - 1) * diff.std(ddof=1) / np.sqrt(len(diff))
    return {"value": diff.mean(), "p": t.pvalue, "ci": (diff.mean() - half, diff.mean() + half)}
''',
    "offset.py": '''
import numpy as np
EFFECTS = [0, 0.2, 0.5, 1.0]
def truth(e): return e
def simulate(e, rng):                       # a distance between two noisy means: its zero is not at 0
    return rng.normal(e, 1, (20, 5)), rng.normal(0, 1, (20, 5))
def estimate(d):
    a, b = d
    return float(np.linalg.norm(a.mean(0) - b.mean(0)))
''',
    "normalized.py": '''
import numpy as np
from scipy import stats
EFFECTS = [0, 0.2, 0.5, 1.0]
def truth(e): return e
def simulate(e, rng):
    return rng.normal(e, 1, 40), rng.normal(0, 1, 40)
def estimate(d):                            # z-scoring each condition separately removes the mean difference
    a, b = ((x - x.mean()) / x.std() for x in d)
    return {"value": a.mean() - b.mean(), "p": stats.ttest_ind(a, b).pvalue}
''',
    "pseudorep.py": '''
import numpy as np
from scipy import stats
EFFECTS = [0, 0.5]
def simulate(e, rng):                       # 4 mice x 50 trials; mice differ, the effect is per mouse
    mice = rng.normal(0, 1, (2, 4, 1))
    return mice[0] + e + rng.normal(0, 1, (4, 50)), mice[1] + rng.normal(0, 1, (4, 50))
def estimate(d):                            # trials pooled as if independent: the mouse variance is ignored
    a, b = d
    return {"value": a.mean() - b.mean(), "p": stats.ttest_ind(a.ravel(), b.ravel()).pvalue}
''',
}


def _demo():
    want = {"good.py": set(), "offset.py": {"OFFSET"}, "normalized.py": {"SHRINKAGE"},
            "pseudorep.py": {"FALSE POSITIVES"}}
    checks = []
    with tempfile.TemporaryDirectory() as d:
        for name, src in DEMO.items():
            p = os.path.join(d, name)
            with open(p, "w") as f:
                f.write(src)
            fails, info, _ = check(p, reps=60)
            got = {v for v, _ in fails}
            checks.append((f"{name}: expected {sorted(want[name]) or 'PASS'}", want[name] <= got and
                           (bool(want[name]) or not got)))
            print()
        fails, info, _ = check(os.path.join(d, "normalized.py"), reps=60, quiet=True)
        checks.append(("normalized.py: no planted effect reaches power 0.8 (a null result would mean nothing)",
                       any("no planted effect" in i for _, i in info)))
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(c for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", help="the adapter module: simulate(effect, rng), estimate(data)")
    ap.add_argument("--effects", type=float, nargs="+", help="planted effect sizes (default: the adapter's EFFECTS)")
    ap.add_argument("--reps", type=int, default=50, help="runs per effect (default 50)")
    ap.add_argument("--alpha", type=float, default=0.05, help="detection threshold on p (default 0.05)")
    ap.add_argument("--seed", type=int, default=0, help="base seed (each run has its own stream)")
    ap.add_argument("--demo", action="store_true", help="four built-in pipelines: one sound, three with known flaws")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    if not a.adapter:
        ap.error("--adapter is required (or --demo)")
    fails, _, _ = check(a.adapter, a.effects, a.reps, a.alpha, a.seed)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
