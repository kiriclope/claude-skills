"""Verify that "frozen" parameters really stay frozen, and inspect gradients per parameter group.

Pitfall this exists for: zeroing a parameter's gradient does NOT freeze it under AdamW —
decoupled weight decay (p ← p − lr·wd·p) still moves it, and Adam's running moments move it for
steps after its gradient was zeroed. Masked/partially frozen tensors (freeze rows/columns of one
tensor) are the usual victims. Fix: restore the frozen values after optimizer.step(), or put
frozen tensors in a param group with weight_decay=0 and requires_grad=False.

Importable:
    sys.path.insert(0, "<skill_dir>/scripts")
    from freeze_check import snapshot, diff_report, grad_norm_table
    before = snapshot(model)                 # clone of every parameter
    loss.backward(); grad_norm_table(model)  # per-parameter grad norms, NaN/inf flagged
    opt.step()
    diff_report(model, before, frozen={"m": mask_or_None, ...})   # what moved, and frozen violations

Smoke test (demonstrates the AdamW weight-decay pitfall):
    python freeze_check.py --demo
"""
import argparse

import torch


def snapshot(model):
    """Detached clones of all parameters, by name."""
    return {k: p.detach().clone() for k, p in model.named_parameters()}


def checksum(model):
    """Cheap per-parameter fingerprint (sum, sum of squares) for logging across steps."""
    return {k: (float(p.detach().double().sum()), float(p.detach().double().pow(2).sum()))
            for k, p in model.named_parameters()}


def grad_norm_table(model, verbose=True):
    """Per-parameter gradient norms; flags None, zero and non-finite gradients. Returns dict."""
    rows = {}
    for k, p in model.named_parameters():
        if p.grad is None:
            rows[k] = None
        else:
            g = p.grad.detach()
            rows[k] = float("nan") if not torch.isfinite(g).all() else float(g.norm())
    if verbose:
        print(f"{'parameter':30s} {'shape':>14s} {'|grad|':>10s}")
        for (k, p), v in zip(model.named_parameters(), rows.values()):
            tag = "  (no grad)" if v is None else ("  NON-FINITE ✗" if v != v else ("  zero" if v == 0 else ""))
            print(f"{k:30s} {str(tuple(p.shape)):>14s} {('—' if v is None else f'{v:.3e}'):>10s}{tag}")
    return rows


def diff_report(model, before, frozen=None, atol=0.0, verbose=True):
    """Compare parameters to a snapshot. `frozen`: {name: None (whole tensor) or bool mask of frozen
    entries}. Returns the list of frozen-parameter violations [(name, max_abs_change)]."""
    frozen = frozen or {}
    violations = []
    for k, p in model.named_parameters():
        d = (p.detach() - before[k]).abs()
        moved = float(d.max()) if d.numel() else 0.0
        line = f"{k:30s} max|Δ| = {moved:.3e}"
        if k in frozen:
            mask = frozen[k]
            dm = float(d.max()) if mask is None else (float(d[mask].max()) if mask.any() else 0.0)
            if dm > atol:
                violations.append((k, dm)); line += f"   FROZEN PART MOVED {dm:.3e} ✗"
            else:
                line += "   frozen ✓"
        if verbose:
            print(line)
    if verbose:
        print(f"SUMMARY: {len(violations)} frozen-parameter violation(s)" + ("" if violations else " ✓"))
    return violations


def _demo():
    torch.manual_seed(0)
    lin = torch.nn.Linear(4, 3)
    mask = torch.zeros_like(lin.weight, dtype=torch.bool); mask[0] = True     # freeze row 0 of W
    x, y = torch.randn(16, 4), torch.randn(16, 3)

    def step(opt, restore):
        before = snapshot(lin)
        opt.zero_grad(); torch.nn.functional.mse_loss(lin(x), y).backward()
        lin.weight.grad[mask] = 0.0                                           # "freeze" by zeroing grads
        opt.step()
        if restore:
            with torch.no_grad():
                lin.weight[mask] = before["weight"][mask]
        return before

    print("AdamW(weight_decay=0.1), frozen row's grad zeroed — NOT frozen:")
    opt = torch.optim.AdamW(lin.parameters(), lr=1e-2, weight_decay=0.1)
    b = step(opt, restore=False)
    bad = diff_report(lin, b, frozen={"weight": mask})
    print("\nsame, plus restore-after-step — frozen:")
    b = step(opt, restore=True)
    good = diff_report(lin, b, frozen={"weight": mask})
    print("\ngradient table of the last step:")
    grad_norm_table(lin)
    assert bad and not good
    print("demo OK — weight decay moves zero-grad parameters; restore-after-step fixes it")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", action="store_true", help="demonstrate the AdamW weight-decay freezing pitfall")
    if ap.parse_args().demo:
        _demo()
    else:
        ap.print_help()
