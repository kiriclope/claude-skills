"""The smallest p-value a test can reach at a given sample size — check it BEFORE choosing the test.

At small n an exact test has a floor: with every unit agreeing, p cannot go lower. If the floor is
above α the test cannot detect anything, however large the effect; if it sits just under α, a single
disagreeing unit (one sign flip) decides significance. Knowing this in advance prevents switching to
"a less conservative test" after seeing the result.

Exact floors, two-sided unless --one_sided:
  paired / one-sample (n units):   sign test 2·0.5^n · Wilcoxon signed-rank 2/2^n ·
                                   sign-flip permutation of the mean difference 2/2^n
  two independent groups (n1, n2): Mann-Whitney 2/C(n1+n2, n1) · label permutation 2/C(n1+n2, n1)
  Monte Carlo permutation (B draws): 1/(B+1) — the floor of any p estimated from B shuffles

Usage:
    python stats_floor.py --n 9                  # paired designs at n = 9 (+ effect of sign flips)
    python stats_floor.py --n1 5 --n2 5          # two independent groups
    python stats_floor.py --perm 100             # floor of a 100-draw permutation null
    python stats_floor.py --table                # floors for n = 3..15
    python stats_floor.py --demo
"""
import argparse
import sys
from math import comb


def sign_floor(n, one_sided=False):
    """Smallest p of the sign test (all n units in one direction)."""
    return min(1.0, (1 if one_sided else 2) * 0.5 ** n)


def sign_needed(n, alpha=0.05, one_sided=False):
    """Smallest number k of n units that must agree for p ≤ alpha, or None if unreachable."""
    for k in range(n // 2, n + 1):
        tail = sum(comb(n, j) for j in range(k, n + 1)) * 0.5 ** n
        if min(1.0, tail * (1 if one_sided else 2)) <= alpha:
            return k
    return None


def wilcoxon_counts(n):
    """counts[s] = number of sign patterns whose negative-rank sum equals s (exact null of W−)."""
    top = n * (n + 1) // 2
    counts = [1] + [0] * top
    for r in range(1, n + 1):
        for s in range(top, r - 1, -1):
            counts[s] += counts[s - r]
    return counts


def wilcoxon_p(n, w_minus, one_sided=False):
    """Exact p of the signed-rank test when the negative ranks sum to w_minus (no ties)."""
    c = wilcoxon_counts(n)
    tail = sum(c[: w_minus + 1]) / 2 ** n
    return min(1.0, tail * (1 if one_sided else 2))


def wilcoxon_flips(n, k, one_sided=False):
    """p when the k SMALLEST differences have the minority sign (the best case for k disagreements)."""
    return wilcoxon_p(n, k * (k + 1) // 2, one_sided)


def mw_floor(n1, n2, one_sided=False):
    """Smallest p of Mann-Whitney / exact label permutation (complete separation)."""
    return min(1.0, (1 if one_sided else 2) / comb(n1 + n2, n1))


def perm_floor(b):
    """Smallest p a Monte Carlo permutation test with b draws can report: 1/(b+1)."""
    return 1 / (b + 1)


def fmt(p):
    return f"{p:.4f}" if p >= 1e-4 else f"{p:.1e}"


def report_paired(n, alpha, one_sided):
    side = "one-sided" if one_sided else "two-sided"
    k = sign_needed(n, alpha, one_sided)
    print(f"paired / one-sample design, n = {n} ({side}, α = {alpha})")
    print(f"  sign test           floor p = {fmt(sign_floor(n, one_sided))}   "
          + (f"needs {k}/{n} units in one direction" if k else f"CANNOT reach {alpha} at this n"))
    print(f"  Wilcoxon signed-rank floor p = {fmt(wilcoxon_p(n, 0, one_sided))}")
    for j in range(1, min(4, n)):
        print(f"      {j} smallest difference(s) with the other sign → p = {fmt(wilcoxon_flips(n, j, one_sided))}")
    print(f"  sign-flip permutation (exact) floor p = {fmt(min(1.0, (1 if one_sided else 2) / 2 ** n))}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, help="units in a paired / one-sample design")
    ap.add_argument("--n1", type=int, help="units in group 1 (independent groups)")
    ap.add_argument("--n2", type=int, help="units in group 2 (independent groups)")
    ap.add_argument("--perm", type=int, help="number of draws of a Monte Carlo permutation null")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--one_sided", action="store_true", help="one-sided floors (only if the direction was predicted)")
    ap.add_argument("--table", action="store_true", help="floors for n = 3..15")
    ap.add_argument("--demo", action="store_true", help="run the built-in self-test")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    if not any([a.n, a.n1, a.perm, a.table]):
        ap.print_help()
        return 0
    if a.n:
        report_paired(a.n, a.alpha, a.one_sided)
    if a.n1 and a.n2:
        p = mw_floor(a.n1, a.n2, a.one_sided)
        print(f"two independent groups, n1 = {a.n1}, n2 = {a.n2}: Mann-Whitney / exact label permutation "
              f"floor p = {fmt(p)}" + ("" if p <= a.alpha else f" — CANNOT reach {a.alpha}"))
    if a.perm:
        print(f"Monte Carlo permutation with {a.perm} draws: floor p = {fmt(perm_floor(a.perm))} "
              f"(a margin below this is noise; use ≥ 1000 draws for a p near {a.alpha})")
    if a.table:
        print(f"{'n':>3} {'sign floor':>11} {'needs':>7} {'Wilcoxon floor':>15} {'MW floor n vs n':>16}")
        for n in range(3, 16):
            k = sign_needed(n, a.alpha, a.one_sided)
            print(f"{n:3d} {fmt(sign_floor(n, a.one_sided)):>11} {(f'{k}/{n}' if k else '—'):>7} "
                  f"{fmt(wilcoxon_p(n, 0, a.one_sided)):>15} {fmt(mw_floor(n, n, a.one_sided)):>16}")
    return 0


def _demo():
    checks = [
        ("sign test n = 6: floor .031 and needs 6/6", abs(sign_floor(6) - 0.03125) < 1e-12 and sign_needed(6) == 6),
        ("sign test n = 5 cannot reach .05", sign_needed(5) is None),
        ("Wilcoxon n = 9: floor .0039", abs(wilcoxon_p(9, 0) - 2 / 512) < 1e-12),
        ("Wilcoxon n = 9, 3 smallest ranks flipped: p ≈ .055 (> .05)", abs(wilcoxon_flips(9, 3) - 28 / 512) < 1e-12),
        ("Wilcoxon exact null sums to 2^n", sum(wilcoxon_counts(12)) == 2 ** 12),
        ("Mann-Whitney 3 vs 3: floor .10 — cannot reach .05", abs(mw_floor(3, 3) - 0.1) < 1e-12),
        ("Mann-Whitney 5 vs 5: floor .0079", abs(mw_floor(5, 5) - 2 / 252) < 1e-12),
        ("100-draw permutation null: floor .0099", abs(perm_floor(100) - 1 / 101) < 1e-12),
    ]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
