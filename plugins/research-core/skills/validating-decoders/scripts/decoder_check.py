"""Decoder validation: probe a decoding pipeline with inputs whose answer is known, before its score is believed.

You write a small adapter module next to the analysis:
    def load():                         -> dict(X=trials × features [× time], y=labels per trial,
                                                groups=session / mouse per trial (optional),
                                                nuisance={name: value per trial} (optional: licks, running, …))
    def evaluate(X, y, groups, rng):    -> the pipeline's cross-validated score (your real code, its own CV)
optional:
    CHANCE = 0.5                        the score at chance for this metric
    def evaluate_across(X_train, y_train, X_test, y_test) -> score     enables the held-out-group probe
The script calls evaluate() on:
  real data                 the score being validated
  shuffled labels           (within groups) → the null: mean, s.d., 95th percentile, permutation p
  pure-noise X              same shape and per-feature scale, real labels and groups → must sit in the null band
  noise X, 75/25 classes    → must stay at CHANCE: a metric that rewards the majority class drifts toward 0.75
  nuisance-matched trials   the nuisance distribution equalized across classes (quantile bins) → the score that
                            does not come from the nuisance
  fewer trials              n, n/2, n/4 → how much the score depends on the trial count
  held-out groups           (evaluate_across) train on all groups but one, test on it
Verdicts (fail):
  LEAKAGE             noise X scores above CHANCE (beyond its sampling band; not the null, which a leak inflates
                      too): labels reach the decoder through
                      preprocessing, feature selection or hyper-parameter tuning on all trials, or through
                      resampled (pseudo-)trials that land in both train and test
  CHANCE MISPLACED    the shuffle null is not at CHANCE: the metric or the class balance is not what you assume
  METRIC UNBALANCED   with 75/25 classes and no signal the score leaves the chance band
  CONFOUNDED          the real score is above the null but the nuisance-matched score falls into the null band
Information: NOT ABOVE NULL (real ≤ null 95th: no evidence of decoding), NUISANCE (how well the nuisance
itself is decoded, its correlation with the labels, the score drop after matching), N-DEPENDENCE,
HELD-OUT GROUPS (generalization across sessions or mice).

Usage:
    python decoder_check.py --adapter analysis/decoder_adapter.py [--perms 50] [--draws 5] [--seed 0]
    python decoder_check.py --demo
Exit 1 on any fail verdict.
"""
import argparse
import importlib.util
import os
import sys
import tempfile
import time

import numpy as np


def load_adapter(path):
    spec = importlib.util.spec_from_file_location("decoder_adapter", path)
    if spec is None or spec.loader is None:
        sys.exit(f"{path}: not a Python module")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(mod)
    for fn in ("load", "evaluate"):
        if not callable(getattr(mod, fn, None)):
            sys.exit(f"{path}: the adapter must define {fn}()")
    return mod


def _shuffle_within(y, groups, rng):
    y = y.copy()
    for g in (np.unique(groups) if groups is not None else [None]):
        idx = np.flatnonzero(groups == g) if g is not None else np.arange(len(y))
        y[idx] = y[rng.permutation(idx)]
    return y


def _noise_like(X, rng):
    """Gaussian noise with each feature's mean and s.d. (over trials, and time if present)."""
    mu, sd = X.mean(axis=0, keepdims=True), X.std(axis=0, keepdims=True)
    return mu + sd * rng.standard_normal(X.shape)


def _sub(d, idx):
    return {"X": d["X"][idx], "y": d["y"][idx], "groups": None if d["groups"] is None else d["groups"][idx]}


def _bins(v, q=4):
    v = np.asarray(v, float)
    if len(np.unique(v)) <= q:
        return np.unique(v, return_inverse=True)[1]
    return np.searchsorted(np.quantile(v, np.linspace(0, 1, q + 1)[1:-1]), v, side="right")


def matched_idx(y, nuis, rng, q=4):
    """Trial indices with the nuisance distribution equal across classes: per nuisance bin, the same number of
    trials from each class (the smallest class count in that bin)."""
    b, classes, idx = _bins(nuis, q), np.unique(y), []
    for k in np.unique(b):
        cells = [np.flatnonzero((b == k) & (y == c)) for c in classes]
        m = min(len(c) for c in cells)
        idx += [i for c in cells for i in rng.choice(c, m, replace=False)] if m else []
    return np.sort(np.array(idx, int))


def probes(mod, perms=50, draws=5, seed=0, log=print):
    rng = np.random.default_rng(seed)
    d = mod.load()
    d = {"X": np.asarray(d["X"], float), "y": np.asarray(d["y"]),
         "groups": None if d.get("groups") is None else np.asarray(d["groups"]), "nuisance": d.get("nuisance") or {}}
    ev = lambda X, y, g: float(mod.evaluate(X, y, g, rng))
    t0 = time.time()
    r = {"chance": float(getattr(mod, "CHANCE", 0.5)), "n": len(d["y"])}
    r["real"] = ev(d["X"], d["y"], d["groups"])
    log(f"  one evaluate() call: {time.time() - t0:.1f} s; about {perms + 2 * draws + 6} more calls to go")
    r["null"] = np.array([ev(d["X"], _shuffle_within(d["y"], d["groups"], rng), d["groups"]) for _ in range(perms)])
    r["noise_draws"] = draws
    r["noise"] = np.mean([ev(_noise_like(d["X"], rng), d["y"], d["groups"]) for _ in range(draws)])
    classes = np.unique(d["y"])
    if len(classes) == 2:                             # 75/25 classes, no signal
        keep = np.concatenate([np.flatnonzero(d["y"] == classes[0]),
                               rng.choice(np.flatnonzero(d["y"] == classes[1]),
                                          max(2, int((d["y"] == classes[0]).sum() / 3)), replace=False)])
        imb = _sub(d, np.sort(keep))
        r["imbalanced"] = np.mean([ev(_noise_like(imb["X"], rng), imb["y"], imb["groups"]) for _ in range(draws)])
    r["nuisance"] = {}
    for name, v in d["nuisance"].items():
        v = np.asarray(v, float)
        yv = (d["y"] == classes[-1]).astype(float) if len(classes) == 2 else d["y"].astype(float)
        corr = float(np.corrcoef(yv, v)[0, 1]) if v.std() > 0 else 0.0
        decod = ev(d["X"], (v > np.median(v)).astype(int) if len(np.unique(v)) > 2 else v.astype(int), d["groups"])
        scores = []
        for _ in range(draws):
            idx = matched_idx(d["y"], v, rng)
            if len(idx) >= 20:
                m = _sub(d, idx)
                scores.append(ev(m["X"], m["y"], m["groups"]))
        r["nuisance"][name] = {"corr": corr, "decoded": decod, "matched": np.mean(scores) if scores else None,
                               "kept": len(matched_idx(d["y"], v, rng))}
    r["by_n"] = {}
    for frac in (0.5, 0.25):
        n = int(len(d["y"]) * frac)
        if n >= 20:
            subs = [_sub(d, np.sort(rng.choice(len(d["y"]), n, replace=False))) for _ in range(draws)]
            r["by_n"][n] = np.mean([ev(s["X"], s["y"], s["groups"]) for s in subs])
    if callable(getattr(mod, "evaluate_across", None)) and d["groups"] is not None:
        r["across"] = {}
        for g in np.unique(d["groups"]):
            tr, te = d["groups"] != g, d["groups"] == g
            r["across"][g] = float(mod.evaluate_across(d["X"][tr], d["y"][tr], d["X"][te], d["y"][te]))
    r["secs"] = time.time() - t0
    return r


def verdicts(r):
    fails, info = [], []
    null = r["null"]
    mu, sd, hi = null.mean(), null.std(ddof=1), np.quantile(null, 0.95)
    band = max(2.5 * sd / np.sqrt(len(null)), 0.5 * sd)
    p = (1 + np.sum(null >= r["real"])) / (1 + len(null))
    # noise X has no signal, so it is judged against CHANCE, not the null: a leak inflates the null as well
    leak_bound = r["chance"] + 2.5 * sd / np.sqrt(r["noise_draws"]) + 0.02
    leak = r["noise"] > leak_bound
    if leak:
        fails.append(("LEAKAGE", f"pure-noise X scores {r['noise']:.3f} (chance {r['chance']:.3f}, allowed ≤ "
                                 f"{leak_bound:.3f}): labels reach the decoder outside the held-out fold"))
    if abs(mu - r["chance"]) > band:
        fails.append(("CHANCE MISPLACED", f"shuffle null {mu:.3f} ± {sd:.3f}, assumed chance {r['chance']:.3f}"
                      + (" — the leak inflates the null too" if leak else
                         " — the metric or the class balance is not what you assume")))
    if leak and "imbalanced" in r:
        info.append(("METRIC", "class-balance probe not judged: the leak inflates it"))
    elif "imbalanced" in r and abs(r["imbalanced"] - r["chance"]) > max(2 * sd, 0.05):
        fails.append(("METRIC UNBALANCED", f"75/25 classes, no signal: {r['imbalanced']:.3f} (chance {r['chance']:.3f})"
                                           " — use balanced accuracy or AUC, or subsample the classes"))
    for name, n in r["nuisance"].items():
        line = (f"{name}: correlation with the labels {n['corr']:+.2f}; decoded at {n['decoded']:.3f}; "
                + (f"score after matching {n['matched']:.3f} on {n['kept']} trials (real {r['real']:.3f})"
                   if n["matched"] is not None else "too few trials to match"))
        info.append(("NUISANCE", line))
        if n["matched"] is not None and r["real"] > hi and n["matched"] <= hi:
            fails.append(("CONFOUNDED", f"with {name} matched across classes the score falls to {n['matched']:.3f}, "
                                        f"inside the null band (≤ {hi:.3f}): the decoder reads {name}"))
    info.insert(0, ("REAL", f"{r['real']:.3f} vs shuffle null {mu:.3f} ± {sd:.3f} (95th {hi:.3f}), "
                            f"permutation p = {p:.3g} over {len(null)} shuffles"))
    if r["real"] <= hi:
        info.append(("NOT ABOVE NULL", "the real score is inside the shuffle null: no evidence of decoding"))
    if r["by_n"]:
        info.append(("N-DEPENDENCE", f"n = {r['n']}: {r['real']:.3f}; " + "; ".join(
            f"n = {n}: {s:.3f}" for n, s in r["by_n"].items()) + " — compare conditions at matched n"))
    if r.get("across"):
        vals = list(r["across"].values())
        info.append(("HELD-OUT GROUPS", f"{len(vals)} groups held out: mean {np.mean(vals):.3f} "
                                        f"(min {min(vals):.3f}); {sum(v > hi for v in vals)}/{len(vals)} above the null"))
    return fails, info


def report(name, r, fails, info):
    print(f"DECODER CHECK · {name} · {r['n']} trials · {r['secs']:.1f} s")
    for v, d in info:
        print(f"  · {v}: {d}")
    for v, d in fails:
        print(f"  ✗ {v}: {d}")
    print(f"SUMMARY: {'FAIL — ' + ', '.join(v for v, _ in fails) if fails else 'PASS — no leakage, chance where assumed'}")


def check(path, perms=50, draws=5, seed=0, quiet=False):
    mod = load_adapter(path)
    r = probes(mod, perms, draws, seed, log=(lambda *a: None) if quiet else print)
    fails, info = verdicts(r)
    if not quiet:
        report(os.path.basename(path), r, fails, info)
    return fails, info, r


DEMO_DATA = '''
import numpy as np
def make(rng, n=240, p=60, signal=0.6, lick_drives_y=False):
    y = np.repeat([0, 1], n // 2)
    groups = np.tile(np.arange(4), n // 4)
    lick = rng.random(n) < np.where(y == 1, 0.8, 0.2) if lick_drives_y else rng.random(n) < 0.5
    X = rng.standard_normal((n, p))
    if lick_drives_y:
        X[:, :5] += 1.2 * lick[:, None]              # the neurons carry licks, not the label
    else:
        X[:, :5] += signal * y[:, None]
    return {"X": X, "y": y, "groups": groups, "nuisance": {"lick": lick.astype(float)}}
'''
DEMO_ADAPTERS = {
    "good.py": '''
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import balanced_accuracy_score
import numpy as np, demo_data
def load(): return demo_data.make(np.random.default_rng(1))
def evaluate(X, y, groups, rng):
    clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500))
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    return cross_val_score(clf, X, y, cv=cv, scoring="balanced_accuracy").mean()
def evaluate_across(Xtr, ytr, Xte, yte):
    clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500)).fit(Xtr, ytr)
    return balanced_accuracy_score(yte, clf.predict(Xte))
''',
    "leaky_selection.py": '''
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
import numpy as np, demo_data
def load(): return demo_data.make(np.random.default_rng(1))
def evaluate(X, y, groups, rng):                  # features chosen on ALL trials, then cross-validated
    Xs = SelectKBest(f_classif, k=5).fit_transform(X, y)
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    return cross_val_score(LogisticRegression(max_iter=500), Xs, y, cv=cv, scoring="balanced_accuracy").mean()
''',
    "plain_accuracy.py": '''
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
import numpy as np, demo_data
def load(): return demo_data.make(np.random.default_rng(1))
def evaluate(X, y, groups, rng):                  # plain accuracy: the majority class wins with no signal
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    return cross_val_score(LogisticRegression(C=0.01, max_iter=500), X, y, cv=cv, scoring="accuracy").mean()
''',
    "pseudotrials.py": '''
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
import numpy as np, demo_data
def load(): return demo_data.make(np.random.default_rng(1))
def evaluate(X, y, groups, rng):                  # pseudo-trials resampled from one pool BEFORE the split
    idx = np.concatenate([rng.choice(np.flatnonzero(y == c), 300) for c in (0, 1)])
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    return cross_val_score(LogisticRegression(C=1.0, max_iter=1000), X[idx], y[idx], cv=cv,
                           scoring="balanced_accuracy").mean()
''',
    "lick_confound.py": '''
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
import numpy as np, demo_data
def load(): return demo_data.make(np.random.default_rng(1), lick_drives_y=True)
def evaluate(X, y, groups, rng):
    clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500))
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    return cross_val_score(clf, X, y, cv=cv, scoring="balanced_accuracy").mean()
''',
}


def _demo():
    want = {"good.py": set(), "leaky_selection.py": {"LEAKAGE"}, "plain_accuracy.py": {"METRIC UNBALANCED"},
            "pseudotrials.py": {"LEAKAGE"}, "lick_confound.py": {"CONFOUNDED"}}
    checks = []
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "demo_data.py"), "w") as f:
            f.write(DEMO_DATA)
        for name, src in DEMO_ADAPTERS.items():
            p = os.path.join(d, name)
            with open(p, "w") as f:
                f.write(src)
            fails, info, _ = check(p, perms=30, draws=3)
            got = {v for v, _ in fails}
            checks.append((f"{name}: expected {sorted(want[name]) or 'PASS'}, got {sorted(got) or 'PASS'}",
                           want[name] <= got and (bool(want[name]) or not got)))
            if name == "good.py":
                checks.append(("good.py: held-out sessions reported", any(v == "HELD-OUT GROUPS" for v, _ in info)))
            print()
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(c for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", help="the adapter module: load(), evaluate(X, y, groups, rng)")
    ap.add_argument("--perms", type=int, default=50, help="label shuffles for the null (default 50)")
    ap.add_argument("--draws", type=int, default=5, help="draws per noise / matching / subsampling probe (default 5)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--demo", action="store_true", help="five built-in pipelines: one sound, four with known flaws")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    if not a.adapter:
        ap.error("--adapter is required (or --demo)")
    fails, _, _ = check(a.adapter, a.perms, a.draws, a.seed)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
