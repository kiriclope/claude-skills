"""Pin a numbers log and check it later: which numbers moved since the snapshot the user approved.

A code edit, a new seed or a changed default can move a paper's numbers without anyone noticing.
`--pin` stores every numeric leaf of a JSON numbers log (key path → value) with the date and the git commit;
`--check` regenerated log against that snapshot:
  CHANGED   |new − old| > atol + rtol·|old|
  NEW       a key that was not pinned
  GONE      a pinned key no longer in the log
Re-pin only after the user has looked at the changes and accepted them.

Usage:
    python pin_numbers.py --pin   --log paper/numbers.json --snapshot paper/numbers.pinned.json
    python pin_numbers.py --check --log paper/numbers.json --snapshot paper/numbers.pinned.json [--rtol 1e-3] [--atol 1e-9]
    python pin_numbers.py --demo
Exit 1 when --check finds CHANGED or GONE numbers.
"""
import argparse
import datetime as dt
import json
import math
import os
import subprocess
import sys
import tempfile


def flatten(obj, prefix=""):
    """{key path: float} for every numeric leaf (bools excluded); lists are indexed key[0], key[1]."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool) and math.isfinite(obj):
        out[prefix] = float(obj)
    return out


def _commit(path):
    try:
        r = subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(path)), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip()


def pin(log, snapshot):
    with open(log) as f:
        values = flatten(json.load(f))
    with open(snapshot, "w") as f:
        json.dump({"pinned": dt.datetime.now().isoformat(timespec="seconds"), "commit": _commit(log),
                   "log": os.path.basename(log), "values": values}, f, indent=1, sort_keys=True)
    print(f"pinned {len(values)} numbers from {log} → {snapshot}")


def compare(log, snapshot, rtol=1e-3, atol=1e-9):
    with open(log) as f:
        new = flatten(json.load(f))
    with open(snapshot) as f:
        snap = json.load(f)
    old = snap["values"]
    changed = [(k, old[k], new[k]) for k in sorted(old.keys() & new.keys())
               if abs(new[k] - old[k]) > atol + rtol * abs(old[k])]
    gone = sorted(old.keys() - new.keys())
    added = sorted(new.keys() - old.keys())
    print(f"PINNED NUMBERS · {log} vs snapshot of {snap.get('pinned', '?')} (commit {snap.get('commit') or '?'})")
    for k, a, b in changed:
        rel = f"{(b - a) / abs(a):+.1%}" if a else "from 0"
        print(f"  CHANGED  {k}: {a:.6g} → {b:.6g} ({rel})")
    for k in gone:
        print(f"  GONE     {k} (was {old[k]:.6g})")
    for k in added:
        print(f"  NEW      {k} = {new[k]:.6g}")
    print(f"SUMMARY: {len(changed)} changed, {len(gone)} gone, {len(added)} new, "
          f"{len(old.keys() & new.keys()) - len(changed)} unchanged")
    return changed, gone, added


def _demo():
    checks = []
    with tempfile.TemporaryDirectory() as d:
        log, snap = os.path.join(d, "numbers.json"), os.path.join(d, "pinned.json")
        with open(log, "w") as f:
            json.dump({"fig3": {"acc": 0.8134, "n_mice": 9, "p": 0.0012}, "fig4": {"push": [-0.06, 0.02]},
                       "ok": True}, f)
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            pin(log, snap)
        with open(log, "w") as f:                                       # an edit moved one number, dropped one
            json.dump({"fig3": {"acc": 0.7921, "n_mice": 9, "p": 0.0012}, "fig4": {"push": [-0.06]},
                       "fig5": {"wells": 0.75}, "ok": True}, f)
        changed, gone, added = compare(log, snap)
        checks += [("a moved number is CHANGED", [c[0] for c in changed] == ["fig3.acc"]),
                   ("a dropped number is GONE", gone == ["fig4.push[1]"]),
                   ("a new number is NEW; booleans are not numbers", added == ["fig5.wells"])]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(c for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pin", action="store_true", help="store the log's numbers as the approved snapshot")
    mode.add_argument("--check", action="store_true", help="compare the log against the snapshot")
    mode.add_argument("--demo", action="store_true", help="self-test")
    ap.add_argument("--log", help="numbers log (JSON)")
    ap.add_argument("--snapshot", help="snapshot file (JSON) written by --pin")
    ap.add_argument("--rtol", type=float, default=1e-3, help="relative tolerance (default 1e-3)")
    ap.add_argument("--atol", type=float, default=1e-9, help="absolute tolerance (default 1e-9)")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    if not (a.log and a.snapshot):
        ap.error("--log and --snapshot are required")
    if a.pin:
        pin(a.log, a.snapshot)
        return 0
    changed, gone, _ = compare(a.log, a.snapshot, a.rtol, a.atol)
    return 1 if changed or gone else 0


if __name__ == "__main__":
    sys.exit(main())
