"""Check a hand-derived Jacobian (or gradient) against the real model, numerically.

Two independent references:
  * torch autograd of the function as the code computes it      → compare_jacobian
  * central finite differences (catches autograd-hidden detaches) → finite_diff_check

Importable:
    sys.path.insert(0, "<skill_dir>/scripts")
    from check_jacobian import compare_jacobian, finite_diff_check
    compare_jacobian(F, x0, J_analytic(x0))          # F: torch (d,) -> (k,), J_analytic: (k, d)
    finite_diff_check(F, x0, J_analytic(x0), eps=1e-5)

Each prints the max abs error, the relative error ‖ΔJ‖/‖J‖, the worst entry, and PASS/FAIL.
Use float64: float32 round-off alone gives relative errors ~1e-6.

Smoke test (low-rank tanh RNN mean field F(κ) = (1/N) nᵀ tanh(g m κ) − κ):
    python check_jacobian.py --demo
"""
import argparse

import numpy as np
import torch


def _as_np(J):
    return J.detach().cpu().numpy() if torch.is_tensor(J) else np.asarray(J, dtype=float)


def _report(name, J_ref, J_an, rtol):
    J_ref, J_an = _as_np(J_ref), _as_np(J_an)
    if J_ref.shape != J_an.shape:
        print(f"{name}: SHAPE MISMATCH reference {J_ref.shape} vs analytic {J_an.shape}  FAIL")
        return False, np.inf
    d = np.abs(J_ref - J_an)
    rel = np.linalg.norm(J_ref - J_an) / max(np.linalg.norm(J_ref), 1e-300)
    i = np.unravel_index(np.argmax(d), d.shape)
    ok = rel < rtol
    print(f"{name}: max|ΔJ| = {d.max():.2e}  rel = {rel:.2e}  worst entry {tuple(int(k) for k in i)}: "
          f"ref {J_ref[i]:+.6g} vs analytic {J_an[i]:+.6g}  {'PASS ✓' if ok else 'FAIL ✗'} (rtol {rtol:g})")
    return ok, rel


def compare_jacobian(f, x, J_analytic, rtol=1e-6):
    """Autograd Jacobian of f at x vs J_analytic. Returns (ok, rel_err)."""
    x = torch.as_tensor(x, dtype=torch.float64).detach().clone()
    J_ag = torch.autograd.functional.jacobian(f, x)
    J_ag = J_ag.reshape(-1, x.numel()) if J_ag.dim() != 2 else J_ag
    return _report("autograd   ", J_ag, J_analytic, rtol)


def finite_diff_check(f, x, J_analytic, eps=1e-5, rtol=1e-5):
    """Central-difference Jacobian of f at x vs J_analytic. Returns (ok, rel_err)."""
    x = torch.as_tensor(x, dtype=torch.float64).detach().clone().reshape(-1)
    cols = []
    with torch.no_grad():
        for j in range(x.numel()):
            e = torch.zeros_like(x); e[j] = eps
            cols.append(((f(x + e) - f(x - e)) / (2 * eps)).reshape(-1))
    J_fd = torch.stack(cols, dim=1)
    return _report("finite diff", J_fd, J_analytic, rtol)


def _demo():
    torch.manual_seed(0)
    N, R, g = 500, 2, 2.0
    m = torch.randn(N, R, dtype=torch.float64); n = torch.randn(N, R, dtype=torch.float64) + 0.5 * m

    def F(kap):                                   # (R,) -> (R,)
        return n.T @ torch.tanh(g * (m @ kap)) / N - kap

    def J_true(kap):                              # (1/N) g nᵀ diag(1 − tanh²) m − I
        s = 1 - torch.tanh(g * (m @ kap)) ** 2
        return g * (n * s[:, None]).T @ m / N - torch.eye(R, dtype=torch.float64)

    def J_wrong(kap):                             # classic slip: forgot the chain-rule factor g
        s = 1 - torch.tanh(g * (m @ kap)) ** 2
        return (n * s[:, None]).T @ m / N - torch.eye(R, dtype=torch.float64)

    kap0 = torch.tensor([0.3, -0.2], dtype=torch.float64)
    print("correct Jacobian:")
    ok1, _ = compare_jacobian(F, kap0, J_true(kap0))
    ok2, _ = finite_diff_check(F, kap0, J_true(kap0))
    print("Jacobian missing the gain g (must FAIL):")
    bad1, _ = compare_jacobian(F, kap0, J_wrong(kap0))
    # at the origin, the overlap form g·nᵀm/N − I must match too
    ok3, _ = compare_jacobian(F, torch.zeros(R, dtype=torch.float64), g * n.T @ m / N - torch.eye(R, dtype=torch.float64))
    assert ok1 and ok2 and ok3 and not bad1
    print("SUMMARY: demo OK — correct form passes, wrong form caught")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="run the low-rank RNN smoke test")
    if ap.parse_args().demo:
        _demo()
    else:
        ap.print_help()
