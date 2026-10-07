---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---
Review this probe for readability and our conventions:

```python
def probe(cfg, ckpt):
    model = LowRankModel(N=cfg["N"], rank=2, alpha=0.075, alpha_rec=0.075)
    model.load_state_dict(torch.load(ckpt))
    k1zcnl = model.kappa()[1]; sclnl = 2  # pin the cue; nolick = 1
    return k1zcnl * sclnl * nolick
```
