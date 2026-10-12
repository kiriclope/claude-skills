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
  noise X, imbalanced       all of the larger class, a third as many of the other (≥ 75/25) → must stay at CHANCE:
                            a metric that rewards the majority class drifts toward the majority share
  nuisance-matched trials   the nuisance distribution equalized across classes (quantile bins) → the score that
                            does not come from the nuisance, against shuffled labels on those same trials and
                            against unmatched subsets of the same size (does matching remove the signal, or only
                            trials?)
  fewer trials              n, n/2, n/4 → how much the score depends on the trial count
  held-out groups           (evaluate_across) train on all groups but one, test on it
Verdicts (fail):
  LEAKAGE             noise X scores above CHANCE (beyond its sampling band; not the null, which a leak inflates
                      too): labels reach the decoder through
                      preprocessing, feature selection or hyper-parameter tuning on all trials, or through
                      resampled (pseudo-)trials that land in both train and test
  CHANCE MISPLACED    the shuffle null is not at CHANCE: the metric or the class balance is not what you assume
  METRIC UNBALANCED   with 75/25 classes and no signal the score leaves the chance band
  CONFOUNDED          the real score is above the null, the nuisance itself is decoded above it, and the
                      nuisance-matched score falls into the null of the matched trials while unmatched subsets
                      of the same size stay above it
  NON-FINITE SCORE    evaluate() returned nan or inf (a failed fit): nothing else is judged
Information: NOT ABOVE NULL (real ≤ null 95th: no evidence of decoding), NUISANCE (how well the nuisance
itself is decoded, its correlation with the labels, the score after matching against its own null; "too few
trials to tell" when same-size unmatched subsets also fall into it), N-DEPENDENCE,
HELD-OUT GROUPS (generalization across sessions or mice).

The adapter is imported with its own folder and the current folder on the module path, so run the script from
the project root when the adapter imports the project's code (from analysis.decode import …).

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
    sys.path[:0] = [os.path.dirname(os.path.abspath(path)), os.getcwd()]   # the adapter's folder; the project root
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


def _xyg(sub):
    return {"X": sub["X"], "y": sub["y"], "g": sub["groups"]}


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


class NonFiniteScore(ValueError):
    pass


def _n_calls(d, perms, draws):
    """evaluate() calls after the first, for the time estimate."""
    n, n_classes = len(d["y"]), len(np.unique(d["y"]))
    return (perms + draws + (draws if n_classes == 2 else 0)
            + len(d["nuisance"]) * (1 + 2 * draws + max(20, perms // 2))
            + draws * sum(int(n * f) >= 20 for f in (0.5, 0.25)))


def probes(mod, perms=50, draws=5, seed=0, log=print):
    rng = np.random.default_rng(seed)
    d = mod.load()
    d = {"X": np.asarray(d["X"], float), "y": np.asarray(d["y"]),
         "groups": None if d.get("groups") is None else np.asarray(d["groups"]), "nuisance": d.get("nuisance") or {}}

    def ev(X, y, g):
        score = float(mod.evaluate(X, y, g, rng))
        if not np.isfinite(score):          # sklearn's cross_val_score returns nan when a fold's fit fails
            raise NonFiniteScore(f"evaluate() returned {score}: a fit failed; fix the pipeline before validating it")
        return score
    t0 = time.time()
    r = {"chance": float(getattr(mod, "CHANCE", 0.5)), "n": len(d["y"])}
    r["real"] = ev(d["X"], d["y"], d["groups"])
    log(f"  one evaluate() call: {time.time() - t0:.1f} s; about {_n_calls(d, perms, draws)} more calls to go")
    r["null"] = np.array([ev(d["X"], _shuffle_within(d["y"], d["groups"], rng), d["groups"]) for _ in range(perms)])
    r["noise_draws"] = draws
    r["noise"] = np.mean([ev(_noise_like(d["X"], rng), d["y"], d["groups"]) for _ in range(draws)])
    classes = np.unique(d["y"])
    if len(classes) == 2:                             # ≥ 75/25 classes, no signal
        major, minor = sorted((np.flatnonzero(d["y"] == c) for c in classes), key=len, reverse=True)
        keep = np.concatenate([major, rng.choice(minor, min(len(minor), max(2, len(major) // 3)), replace=False)])
        imb = _sub(d, np.sort(keep))
        r["imbalanced"] = np.mean([ev(_noise_like(imb["X"], rng), imb["y"], imb["groups"]) for _ in range(draws)])
        r["majority_share"] = len(major) / len(keep)
    r["nuisance"] = {}
    for name, v in d["nuisance"].items():
        v = np.asarray(v, float)
        yv = (d["y"] == classes[-1]).astype(float) if len(classes) == 2 else d["y"].astype(float)
        corr = float(np.corrcoef(yv, v)[0, 1]) if v.std() > 0 else 0.0
        decod = ev(d["X"], (v > np.median(v)).astype(int) if len(np.unique(v)) > 2 else v.astype(int), d["groups"])
        res = {"corr": corr, "decoded": decod, "matched": None}
        idx = matched_idx(d["y"], v, rng)
        if len(idx) >= 20:
            m = _sub(d, idx)
            res["kept"] = len(idx)
            res["matched"] = np.mean([ev(**_xyg(_sub(d, matched_idx(d["y"], v, rng)))) for _ in range(draws)])
            # the bar for the matched score: shuffled labels on the matched trials (fewer trials, wider null) …
            res["matched_null"] = np.array([ev(m["X"], _shuffle_within(m["y"], m["groups"], rng), m["groups"])
                                            for _ in range(max(20, perms // 2))])
            # … and unmatched subsets of the same size: do they stay above it (matching removed the signal)?
            res["same_n"] = np.mean([ev(**_xyg(_sub(d, np.sort(rng.choice(len(d["y"]), len(idx), replace=False)))))
                                     for _ in range(draws)])
        r["nuisance"][name] = res
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
        share = r["majority_share"]
        fails.append(("METRIC UNBALANCED", f"{share:.0%}/{1 - share:.0%} classes, no signal: {r['imbalanced']:.3f} "
                                           f"(chance {r['chance']:.3f}) — use balanced accuracy or AUC, or subsample "
                                           "the classes"))
    for name, n in r["nuisance"].items():
        line = f"{name}: correlation with the labels {n['corr']:+.2f}; decoded at {n['decoded']:.3f}; "
        if n["matched"] is None:
            info.append(("NUISANCE", line + "too few trials to match"))
            continue
        m_hi = np.quantile(n["matched_null"], 0.95)
        info.append(("NUISANCE", line + f"score after matching {n['matched']:.3f} on {n['kept']} trials (their null "
                                        f"95th {m_hi:.3f}; unmatched subsets of that size {n['same_n']:.3f}; "
                                        f"real {r['real']:.3f})"))
        if r["real"] <= hi or n["matched"] > m_hi:
            continue
        if n["same_n"] <= m_hi:
            info.append(("NUISANCE", f"{name}: too few matched trials to tell — subsets of the same size also fall "
                                     "into the null"))
        elif n["decoded"] > hi:
            fails.append(("CONFOUNDED", f"with {name} matched across classes the score falls to {n['matched']:.3f}, "
                                        f"inside the null of those trials (≤ {m_hi:.3f}), while unmatched subsets of "
                                        f"the same size score {n['same_n']:.3f}: the decoder reads {name}"))
        else:
            info.append(("NUISANCE", f"{name}: the matched score falls into its null, but {name} itself is not "
                                     "decoded above the null — look at which trials matching removed"))
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
    try:
        r = probes(mod, perms, draws, seed, log=(lambda *a: None) if quiet else print)
    except NonFiniteScore as e:
        if not quiet:
            print(f"DECODER CHECK · {os.path.basename(path)}\n  ✗ NON-FINITE SCORE: {e}\n"
                  "SUMMARY: FAIL — NON-FINITE SCORE")
        return [("NON-FINITE SCORE", str(e))], [], None
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
    "failed_fit.py": '''
import numpy as np, demo_data
def load(): return demo_data.make(np.random.default_rng(1))
def evaluate(X, y, groups, rng):                  # one fit in four fails: cross_val_score's error_score is nan
    return float("nan") if rng.random() < 0.25 else 0.5
''',
    "few_nogo.py": '''
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
import numpy as np, demo_data
def load():                                       # 170 trials of the first class, 30 of the second
    d = demo_data.make(np.random.default_rng(1), n=400)
    keep = np.r_[np.flatnonzero(d["y"] == 0)[:170], np.flatnonzero(d["y"] == 1)[:30]]
    return {"X": d["X"][keep], "y": d["y"][keep], "groups": d["groups"][keep]}
def evaluate(X, y, groups, rng):
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    return cross_val_score(LogisticRegression(C=0.1, max_iter=500), X, y, cv=cv, scoring="balanced_accuracy").mean()
''',
    "lick_correlated_only.py": '''
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
import numpy as np, demo_data
def load():               # neurons carry the label only; licks follow it 90/10 (the old rule called this CONFOUNDED)
    d = demo_data.make(np.random.default_rng(22), signal=0.45)
    d["nuisance"]["lick"] = (np.random.default_rng(122).random(len(d["y"])) < np.where(d["y"] == 1, 0.9, 0.1)) * 1.0
    return d
def evaluate(X, y, groups, rng):
    clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=500))
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    return cross_val_score(clf, X, y, cv=cv, scoring="balanced_accuracy").mean()
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
            "pseudotrials.py": {"LEAKAGE"}, "failed_fit.py": {"NON-FINITE SCORE"}, "few_nogo.py": set(),
            "lick_correlated_only.py": set(), "lick_confound.py": {"CONFOUNDED"}}
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
    ap.add_argument("--demo", action="store_true", help="built-in pipelines: sound ones, and ones with known flaws")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    if not a.adapter:
        ap.error("--adapter is required (or --demo)")
    fails, _, _ = check(a.adapter, a.perms, a.draws, a.seed)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
