# The conventions in practice — before / after

Contents: docstring · names · derived constants · swallowed code · new options · one axis = one list ·
labels vs keys · per-unit output · colors · failures

Each pair comes from a real correction in these projects.

## Module docstring (the model)

```python
"""Flow VERDICT — the canonical scoring of a rank-2 sweep against the project goal.

The ONLY success criterion: the SAMPLE-MEMORY wells (the ± κ₀ attractor pair that carries
the A/B bit) sit at κ₁ < 0. Everything else is reported separately so it is never conflated.

Per run: FP finder on a wide box, every root re-verified via |F(κ*)|; attractors split into
memory wells (|κ₀| ≥ --mem_k0) vs extras; behavior at the FIXED boundary 0.

Which field (2026-09-25): trials follow the INPUT-NOISE-AVERAGED field (trials (+0.94,−0.56),
averaged well (+0.93,−0.58), deterministic (+1.23,−0.34)), so it is scored by default.

Usage:
  $ENV_PREFIX python flow_verdict.py --sweep_dir results/dual/sweep_x [--stage expert] [--run_ids ...]
"""
```
What it decides → criterion → procedure → dated decisions with their evidence → exact command.

## Names

```python
k1zcnl = …; sclnl = …                     # before: initialisms nobody can decode
pin_cue_nolick = …; scale_nolick = …      # after: words, or the paper's symbol (kappa, W_rec, alpha)
```

## Derived constants

```python
model = LowRankModel(..., alpha=0.075, alpha_rec=0.075)          # before: typed in, and wrong
DT, alpha, alpha_rec = run_dt_alpha(cfg)                          # after: derived per run, one helper
model = LowRankModel(..., alpha=alpha, alpha_rec=alpha_rec)
```
Why: alpha_rec = dt/tau_rec = 0.1 at the standard tau, not alpha, and tau varies 0.1–1.2 across
sweeps — a constant is wrong for both and fails silently.

## Comments that swallow code

```python
a = f(x); b = g(x)
a = f(x)  # the A axis; b = g(x)          # before: an inserted comment hid `b = …` — four scripts crashed
a = f(x)                                  # after: comment on its own line or after the last statement
b = g(x)  # the A axis is f, the B axis g
```

## New options

```python
def __init__(self, N, rank, fixed_weight_std):               # before: positional — old checkpoints break
def __init__(self, N, rank, use_fixed_weights=False, fixed_weight_scale=1.0):   # after: keyword, old default
```

## One axis = one list

```python
freeze_gng_inputs: bool = False; freeze_dual_inputs: bool = True     # before: flags that combine badly
freeze_input_stages: list = field(default_factory=lambda: ["dual"])  # after: subset of ["dpa", "gng", "dual"]
```

## Labels vs stored keys

```python
results = {k.replace("dist", "GNG"): v for k, v in results.items()}   # before: renamed cache keys
DISPLAY = {"dist": "GNG"}; ax.set_title(DISPLAY.get(key, key))         # after: map at draw time
```

## Per-unit output

```python
print(f"mean occupied κ₁ = {np.mean(k1):+.3f}")        # before: the mean hid a seed at −1.30
for s, k in zip(seeds, k1):                             # after: one row per seed, then the count
    print(f"s{s}: κ₁ {k:+.2f}  {'DOWN ✓' if k < 0 else 'up'}")
print(f"SUMMARY: {sum(k < 0 for k in k1)}/{len(k1)} seeds with the well below the line")
```

## Colors

```python
ax.plot(t, a, color="#d62728"); ax.plot(t, b, color="#2ca02c")   # before: red vs green, hue only
from cbstyle import PAIR                                          # after: blue / vermillion + line style
ax.plot(t, a, color=PAIR[0]); ax.plot(t, b, color=PAIR[1], ls="--")
```

## Failures

```python
try: register_fonts()                                  # before: a missing font silently changes every figure
except Exception: pass
try: register_fonts()                                  # after: catch what you expect, say what happened
except FileNotFoundError as e:
    print(f"font not found ({e}); falling back to DejaVu Sans", file=sys.stderr)
```
