"""Run card: what exactly was trained — per stage, read from the code that trains it.

For a sweep directory, reads every run's config.json and prints, for each training stage (DPA, GNG,
Dual-paired when present, Dual), the config fields that feed that stage's trial generator (targets,
windows, trial types), its loss (UnifiedLoss terms, weights, thresholds) and its training call (epochs,
optimizer, lr, clip, scheduler, stop loss, freezing, symmetry), with their values.

The field → stage map is PARSED from the repository's sweep.py (`run_single`), not hard-coded: stage
regions are the `_stage_header("NAME", …)` calls; generator, loss and training calls are matched to them;
local variables and `**dict` kwargs are resolved transitively; a module function that receives the whole
`config` is followed into its body. A field the parser cannot place is reported as not placed — never
guessed. Fields read elsewhere in run_single (model, dynamics, init) are listed as SHARED.

The baseline run (first, or --baseline) gets the full card; the other runs are grouped by their
differences from it (runs that differ in the same way form one arm), each difference tagged with the
stages it feeds.

Usage:
    python run_card.py --sweep_dir results/dual/sweep_x [--run_ids s0_x s1_x] [--baseline s0_x]
                       [--sweep_py path/to/sweep.py] [--diff_only]
    python run_card.py --demo
"""
import argparse
import ast
import datetime as dt
import io
import json
import os
import subprocess
import sys
import tempfile
import tokenize

STAGE_OF_GENERATOR = {"generate_dpa_trials": "DPA", "generate_gng_trials": "GNG", "generate_dual_trials": "Dual"}
IGNORE_WHOLE_CONFIG = {"asdict", "print", "repr", "str", "dict", "vars", "copy", "deepcopy", "replace"}
QUIET_FIELDS = {"run_id", "seed"}                 # differ by design between runs of one arm
OBJECT_PARAMS = {"model", "train_loader", "val_loader", "criterion", "self"}   # objects, not settings


# ── parsing sweep.py ────────────────────────────────────────────────────────────────────────────

def _fn_name(call):
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")


class SweepModel:
    """The RunConfig fields and the field → stage-site map of run_single."""

    def __init__(self, src, signatures=None):
        self.signatures = signatures or {}
        self.src = src
        self.tree = ast.parse(src)
        self.comments = self._comments(src)
        self.fields = self._runconfig_fields()
        self.helpers = {n.name: n for n in self.tree.body if isinstance(n, ast.FunctionDef)}
        rs = self.helpers.get("run_single")
        if rs is None:
            raise ValueError("no run_single() in sweep.py")
        self.run_single = rs
        self.cfg = rs.args.args[0].arg if rs.args.args else "config"
        self._helper_cache = {}
        self.closures = {}                                     # nested functions reading config from the enclosing scope
        for n in ast.walk(rs):
            if isinstance(n, ast.FunctionDef) and n is not rs:
                self.closures[n.name] = {m.attr for m in ast.walk(n) if isinstance(m, ast.Attribute)
                                         and isinstance(m.value, ast.Name) and m.value.id == self.cfg}
        self.parents = {c: p for p in ast.walk(rs) for c in ast.iter_child_nodes(p)}
        self.locals_direct, self.locals_dicts = self._locals(rs)
        self.tainted = self._tainted()
        self.locals_fields = self._close(self.locals_direct)
        self.unresolved = set()
        self.stages = self._stage_sites(rs)

    @staticmethod
    def _comments(src):
        out = {}
        for t in tokenize.generate_tokens(io.StringIO(src).readline):
            if t.type == tokenize.COMMENT:
                out[t.start[0]] = t.string.lstrip("#").strip()
        return out

    def _runconfig_fields(self):
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "RunConfig":
                out = {}
                for s in node.body:
                    if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
                        out[s.target.id] = {"default": ast.unparse(s.value) if s.value is not None else "",
                                            "comment": self.comments.get(s.lineno, "")}
                return out
        raise ValueError("no RunConfig dataclass in sweep.py")

    # — field references —

    def _helper_fields(self, name, depth=0):
        """Fields a module helper reads from the config it receives (first param that is passed config)."""
        if name in self._helper_cache:
            return self._helper_cache[name]
        node = self.helpers.get(name)
        if node is None or depth > 3:
            return None
        self._helper_cache[name] = set()                       # cycle guard
        params = [a.arg for a in node.args.args]
        out = set()
        for p in params[:2]:                                   # config is the first or second parameter
            for n in ast.walk(node):
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == p:
                    out.add(n.attr)
        out &= set(self.fields)
        self._helper_cache[name] = out
        return out

    def refs(self, node):
        """Config fields an expression depends on: direct, via locals, via helpers given the config."""
        fields, unresolved = set(), set()
        for n in ast.walk(node):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == self.cfg:
                fields.add(n.attr)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in self.locals_fields:
                if n.id == "model":                            # the object itself carries no stage setting
                    continue
                fields |= (self.locals_direct[n.id][0] if n.id in self.tainted else self.locals_fields[n.id])
            elif isinstance(n, ast.Call) and _fn_name(n) in self.closures:
                fields |= self.closures[_fn_name(n)]
            elif isinstance(n, ast.Call) and any(isinstance(a, ast.Name) and a.id == self.cfg for a in n.args):
                fn = _fn_name(n)
                if fn in IGNORE_WHOLE_CONFIG:
                    continue
                hf = self._helper_fields(fn)
                if hf is None:
                    unresolved.add(fn)
                else:
                    fields |= hf
        return fields & set(self.fields), unresolved

    def _attrs(self, node):
        out = set()
        for m in ast.walk(node):
            if isinstance(m, ast.Attribute) and isinstance(m.value, ast.Name) and m.value.id == self.cfg:
                out.add(m.attr)
            elif isinstance(m, ast.Call) and _fn_name(m) in self.closures:
                out |= self.closures[_fn_name(m)]
            elif isinstance(m, ast.Call) and any(isinstance(a, ast.Name) and a.id == self.cfg for a in m.args):
                hf = self._helper_fields(_fn_name(m))
                out |= hf or set()
        return out

    def _locals(self, fn):
        """name → [direct config fields (incl. enclosing if-conditions), names read]; dict-valued assignments."""
        direct, dicts = {}, {}

        def visit(stmts, cond):
            for n in stmts:
                if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign)) and n.value is not None:
                    targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                    names = [t.id for t in targets if isinstance(t, ast.Name)]
                    names += [e.id for t in targets if isinstance(t, ast.Tuple) for e in t.elts if isinstance(e, ast.Name)]
                    deps_cfg = self._attrs(n.value) | cond
                    deps_names = {m.id for m in ast.walk(n.value) if isinstance(m, ast.Name) and isinstance(m.ctx, ast.Load)}
                    for name in names:
                        d = direct.setdefault(name, [set(), set()])
                        d[0] |= deps_cfg; d[1] |= deps_names
                        if len(names) == 1:
                            dicts.setdefault(name, []).append(n.value)
                if isinstance(n, (ast.If, ast.While)):
                    c = cond | self._attrs(n.test)
                    visit(n.body, c); visit(n.orelse, c)
                elif isinstance(n, (ast.For, ast.With, ast.Try)):
                    for block in ("body", "orelse", "finalbody"):
                        visit(getattr(n, block, []) or [], cond)
                    for h in getattr(n, "handlers", []) or []:
                        visit(h.body, cond)
        visit(fn.body, set())
        return direct, dicts

    def _tainted(self):
        """Locals derived from the model object: their transitive closure is everything, so only direct fields count."""
        bad = {"model"}
        changed = True
        while changed:
            changed = False
            for k, (_, names) in self.locals_direct.items():
                if k not in bad and names & bad:
                    bad.add(k); changed = True
        return bad

    def _close(self, direct):
        out = {k: set(v[0]) for k, v in direct.items()}
        changed = True
        while changed:
            changed = False
            for k, (_, names) in direct.items():
                for nm in names:
                    if nm in out and nm != k and not out[nm] <= out[k]:
                        out[k] |= out[nm]; changed = True
        return {k: v & set(self.fields) for k, v in out.items()}

    def _dict_keys(self, name, seen=()):
        """{key: fields} for a local dict built with dict(...), {...}, {**other, ...} or A if c else B."""
        out = {}
        for value in self.locals_dicts.get(name, []):
            for k, f in self._dict_value_keys(value, seen + (name,)).items():
                out.setdefault(k, set()).update(f)
        return out

    def _dict_value_keys(self, v, seen):
        out = {}
        if isinstance(v, ast.IfExp):
            cond, _ = self.refs(v.test)
            for branch in (v.body, v.orelse):
                for k, f in self._dict_value_keys(branch, seen).items():
                    out.setdefault(k, set()).update(f | cond)
        elif isinstance(v, ast.Call) and _fn_name(v) == "dict":
            for kw in v.keywords:
                if kw.arg is None and isinstance(kw.value, ast.Name) and kw.value.id not in seen:
                    for k, f in self._dict_keys(kw.value.id, seen).items():
                        out.setdefault(k, set()).update(f)
                elif kw.arg is not None:
                    out[kw.arg] = self.refs(kw.value)[0]
        elif isinstance(v, ast.Dict):
            for k, val in zip(v.keys, v.values):
                if k is None and isinstance(val, ast.Name) and val.id not in seen:
                    for kk, f in self._dict_keys(val.id, seen).items():
                        out.setdefault(kk, set()).update(f)
                elif isinstance(k, ast.Constant) and isinstance(k.value, str):
                    out[k.value] = self.refs(val)[0]
        return out

    def _call_rows(self, call, param_names=()):
        """[(kwarg, fields)] for a call: keyword args, **dict locals expanded, named positionals."""
        rows = []
        param_names = self.signatures.get(_fn_name(call)) or param_names
        for i, a in enumerate(call.args):
            name = param_names[i] if i < len(param_names) else f"arg{i}"
            if name in OBJECT_PARAMS:
                continue
            f, u = self.refs(a); self.unresolved |= u
            if f:
                rows.append((name, f))
        for kw in call.keywords:
            if kw.arg in OBJECT_PARAMS:
                continue
            if kw.arg is None and isinstance(kw.value, ast.Name):
                for k, f in sorted(self._dict_keys(kw.value.id).items()):
                    if f:
                        rows.append((k, f))
            elif kw.arg is not None:
                f, u = self.refs(kw.value); self.unresolved |= u
                if f:
                    rows.append((kw.arg, f))
        return rows

    def _stage_sites(self, fn):
        calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)]
        headers = sorted((c.lineno, c.args[0].value) for c in calls if _fn_name(c) == "_stage_header"
                         and c.args and isinstance(c.args[0], ast.Constant))
        end = fn.end_lineno or 10 ** 9

        def region(line):
            name = None
            for start, label in headers:
                if line >= start:
                    name = label
            return name

        criteria = {}                                          # criterion variable → UnifiedLoss call
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and _fn_name(n.value) == "UnifiedLoss":
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        criteria[t.id] = n.value
        stages = {label: {"header": [], "trials": [], "loss": [], "train": []} for _, label in headers}
        self.stage_cond = {}
        for c in calls:
            if _fn_name(c) == "_stage_header" and c.args and isinstance(c.args[0], ast.Constant):
                cond, node = set(), c
                while node in self.parents:
                    node = self.parents[node]
                    if isinstance(node, (ast.If, ast.While)):
                        cond |= self._attrs(node.test)
                self.stage_cond[c.args[0].value] = cond & set(self.fields)
        for c in calls:
            name = _fn_name(c)
            label = region(c.lineno)
            if name == "_stage_header" and c.args and isinstance(c.args[0], ast.Constant):
                stages[c.args[0].value]["header"] += self._call_rows(c, ("name", "epochs", "freeze_inputs", "freeze_rank_cols"))
            elif name in STAGE_OF_GENERATOR and label:
                stages[label]["trials"] += self._call_rows(c)
            elif name == "Optimization" and label:
                stages[label]["train"] += self._call_rows(c, ("model", "train_loader", "val_loader", "criterion",
                                                              "optimizer", "scheduler"))
                if len(c.args) > 3 and isinstance(c.args[3], ast.Name) and c.args[3].id in criteria:
                    stages[label]["loss"] += self._call_rows(criteria[c.args[3].id])
        return stages

    def placed(self):
        out = set()
        for st in self.stages.values():
            for rows in st.values():
                for _, f in rows:
                    out |= f
        return out

    def stages_of(self, field):
        return [s for s, st in self.stages.items() if any(field in f for rows in st.values() for _, f in rows)]

    def read_in_run_single(self):
        return self.refs(self.run_single)[0]


# ── runs ────────────────────────────────────────────────────────────────────────────────────────

def find_sweep_py(start):
    d = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(d, "sweep.py")):
            return os.path.join(d, "sweep.py")
        if os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


def repo_signatures(sweep_py):
    """Parameter names of functions and class constructors in the repo (sweep.py and src/*.py)."""
    root = os.path.dirname(os.path.abspath(sweep_py))
    files = [sweep_py] + [os.path.join(root, "src", f) for f in sorted(os.listdir(os.path.join(root, "src")))
                          if f.endswith(".py")] if os.path.isdir(os.path.join(root, "src")) else [sweep_py]
    sig = {}
    for f in files:
        try:
            tree = ast.parse(open(f).read())
        except (SyntaxError, OSError):
            continue
        for n in tree.body:
            if isinstance(n, ast.FunctionDef):
                sig.setdefault(n.name, [a.arg for a in n.args.args])
            elif isinstance(n, ast.ClassDef):
                for m in n.body:
                    if isinstance(m, ast.FunctionDef) and m.name == "__init__":
                        sig.setdefault(n.name, [a.arg for a in m.args.args][1:])
    return sig


def load_runs(sweep_dir, run_ids=None):
    runs = {}
    for name in sorted(os.listdir(sweep_dir)):
        p = os.path.join(sweep_dir, name, "config.json")
        if os.path.exists(p) and (not run_ids or name in run_ids):
            runs[name] = (json.load(open(p)), p)
    return runs


def fmt(v):
    if isinstance(v, float):
        return f"{v:.6g}"
    if isinstance(v, list):
        return "[" + ", ".join(str(x) for x in v) + "]" if v else "[]"
    return "—" if v is None else str(v)


def value(cfg, field, model):
    if field in cfg:
        return fmt(cfg[field])
    return f"(absent; RunConfig default {model.fields[field]['default']})"


def git_info(path):
    d = os.path.dirname(os.path.abspath(path))
    h = subprocess.run(["git", "-C", d, "log", "-1", "--format=%h %cd", "--date=short", "--", path],
                       capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", d, "status", "--porcelain", "--", path], capture_output=True, text=True).stdout.strip()
    return (h or "not in git") + (", uncommitted changes" if dirty else "")


def derived(cfg, sweep_py_src):
    """dt, α, α_rec through the repo's own run_dt_alpha (bifurcation_probe.py), if it is pure arithmetic."""
    probe = os.path.join(os.path.dirname(sweep_py_src), "bifurcation_probe.py")
    if not os.path.exists(probe):
        return None
    for node in ast.parse(open(probe).read()).body:
        if isinstance(node, ast.FunctionDef) and node.name == "run_dt_alpha":
            ns = {}
            try:
                exec(compile(ast.Module(body=[node], type_ignores=[]), probe, "exec"), ns)
                return ns["run_dt_alpha"](cfg)
            except Exception as e:                             # report, never hide
                return f"run_dt_alpha failed: {e}"
    return None


# ── card ────────────────────────────────────────────────────────────────────────────────────────

def card(sweep_dir, run_ids=None, baseline=None, sweep_py=None, diff_only=False):
    sweep_py = sweep_py or find_sweep_py(sweep_dir)
    if not sweep_py:
        print("no sweep.py found above the sweep directory — pass --sweep_py"); return 1
    model = SweepModel(open(sweep_py).read(), repo_signatures(sweep_py))
    runs = load_runs(sweep_dir, run_ids)
    if not runs:
        print(f"no <run>/config.json under {sweep_dir}"); return 1
    base = baseline or next(iter(runs))
    bcfg, bpath = runs[base]
    stamp = dt.datetime.fromtimestamp(os.path.getmtime(bpath)).strftime("%Y-%m-%d")
    print(f"RUN CARD · {os.path.basename(os.path.normpath(sweep_dir))} · {len(runs)} runs · baseline {base} "
          f"(config written {stamp})")
    print(f"field → stage map parsed from {sweep_py} ({git_info(sweep_py)}); runs trained before the last change "
          f"to sweep.py may have used different code")
    absent = [f for f in model.fields if f not in bcfg]
    if absent:
        print(f"WARNING: {len(absent)} of {len(model.fields)} RunConfig fields are absent from {base}'s config.json "
              f"(saved by an older sweep.py). Their values below are TODAY's defaults, not necessarily what that run used.")

    if not diff_only:
        shared = sorted(model.read_in_run_single() - model.placed())
        print("\nSHARED — read in run_single outside the stage sites (model, dynamics, init, I/O)")
        line = "  "
        for f in shared:
            item = f"{f}={value(bcfg, f, model)}  "
            if len(line) + len(item) > 118:
                print(line.rstrip()); line = "  "
            line += item
        print(line.rstrip())
        d = derived(bcfg, sweep_py)
        if isinstance(d, tuple):
            print(f"  derived (run_dt_alpha): dt={d[0]:.4f}  α={d[1]:.4f}  α_rec={d[2]:.4f}")
        elif d:
            print(f"  derived: {d}")
        skip_switches = set().union(*model.stage_cond.values()) if model.stage_cond else set()
        for label, st in model.stages.items():
            cond = model.stage_cond.get(label, set())
            print(f"\n{label.upper()}" + (f"   (runs only when: {', '.join(f'{f}={value(bcfg, f, model)}' for f in sorted(cond))})"
                                            if cond else ""))
            for group in ("header", "trials", "loss", "train"):
                seen = set()
                for kw, fields in st[group]:
                    fields = fields - skip_switches or fields
                    if (kw, tuple(sorted(fields))) in seen:
                        continue
                    seen.add((kw, tuple(sorted(fields))))
                    vals = ", ".join(f"{f}={value(bcfg, f, model)}" for f in sorted(fields))
                    print(f"  {group:7s} {kw:24s} ← {vals}")
        unplaced = sorted(set(model.fields) - model.read_in_run_single() - model.placed())
        if model.unresolved:
            print(f"\nNOT PLACED — config passed whole to functions the parser cannot read: "
                  f"{', '.join(sorted(model.unresolved))} (their fields may belong to any stage)")
        print(f"\nNOT READ by run_single ({len(unplaced)} fields; inert, legacy, or read by code outside sweep.py): "
              + ", ".join(unplaced))

    groups = {}
    for rid, (cfg, _) in runs.items():
        if rid == base:
            continue
        diff = tuple(sorted((f, json.dumps(cfg.get(f, "§absent"), sort_keys=True)) for f in set(cfg) | set(bcfg)
                            if f not in QUIET_FIELDS and cfg.get(f, "§absent") != bcfg.get(f, "§absent")))
        groups.setdefault(diff, []).append(rid)            # same fields AND same values = one arm
    print(f"\nDIFFERENCES FROM {base}  (runs that differ the same way are grouped; seed and run_id ignored)")
    if not groups:
        print("  (no other runs)")
    for diff, rids in groups.items():
        print(f"  {', '.join(rids)}:" + ("  identical config" if not diff else ""))
        for f, _ in diff:
            where = model.stages_of(f) or (["shared"] if f in model.read_in_run_single() else ["not read by run_single"])
            print(f"      {f}: {fmt(bcfg.get(f))} → {fmt(runs[rids[0]][0].get(f))}   [{', '.join(where)}]")
    return 0


# ── demo ────────────────────────────────────────────────────────────────────────────────────────

DEMO_SWEEP = '''
from dataclasses import dataclass, field
@dataclass
class RunConfig:
    lr: float = 0.01            # learning rate, all stages
    epochs_dpa: int = 10
    epochs_gng: int = 10
    dpa_nolick_weight: float = 0.0   # DPA delay don't-lick
    gng_weight: float = 1.0
    nolick_weight: float = 1.0
    kappa1_reg: float = 0.0     # read by a helper
    hidden_size: int = 64
    legacy_thing: int = 3       # never read

def _reg(config, model):
    return config.kappa1_reg

def run_single(config, device):
    model = make_model(config.hidden_size)
    _uw = dict(gng_weight=config.gng_weight, nolick_weight=config.nolick_weight)
    opt = make_opt(config.lr)
    dpa_criterion = UnifiedLoss(t, nolick_weight=config.dpa_nolick_weight)
    gng_criterion = UnifiedLoss(t, **_uw)
    _stage_header("DPA", config.epochs_dpa, [], [])
    X, y = generate_dpa_trials(64, t)
    trainer = Optimization(model, tl, vl, dpa_criterion, opt, None, regularizer=_reg(config, model))
    _stage_header("GNG", config.epochs_gng, [], [])
    X, y = generate_gng_trials(64, t)
    trainer = Optimization(model, tl, vl, gng_criterion, opt, None, extra=unknown_helper(config))
'''


def _demo():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "sweep.py"), "w").write(DEMO_SWEEP)
        sw = os.path.join(d, "results", "sweep_demo")
        base = {"run_id": "s0_a", "seed": 0, "lr": 0.01, "epochs_dpa": 10, "epochs_gng": 10, "dpa_nolick_weight": 0.0,
                "gng_weight": 1.0, "nolick_weight": 1.0, "kappa1_reg": 0.0, "hidden_size": 64, "legacy_thing": 3}
        for rid, change in (("s0_a", {}), ("s1_a", {"seed": 1}), ("s0_b", {"dpa_nolick_weight": 0.5}),
                            ("s0_c", {"dpa_nolick_weight": 0.9})):
            os.makedirs(os.path.join(sw, rid))
            json.dump({**base, **change, "run_id": rid}, open(os.path.join(sw, rid, "config.json"), "w"))
        model = SweepModel(DEMO_SWEEP)
        buf = io.StringIO(); old = sys.stdout; sys.stdout = buf
        try:
            card(sw)
        finally:
            sys.stdout = old
        out = buf.getvalue()
    checks = [
        ("DPA loss row maps nolick_weight ← dpa_nolick_weight", "nolick_weight" in str(model.stages["DPA"]["loss"])
         and "dpa_nolick_weight" in out.split("GNG")[0]),
        ("GNG loss expands **_uw into its keys", {k for k, _ in model.stages["GNG"]["loss"]} >= {"gng_weight", "nolick_weight"}),
        ("helper given the whole config is followed (kappa1_reg → DPA)", "DPA" in model.stages_of("kappa1_reg")),
        ("unreadable helper is reported, not guessed", "unknown_helper" in model.unresolved and "NOT PLACED" in out),
        ("never-read field listed as such", "legacy_thing" in out.split("NOT READ")[1]),
        ("seed-only run reported as identical config", "s1_a:  identical config" in out),
        ("arm difference tagged with its stage", "dpa_nolick_weight: 0 → 0.5   [DPA]" in out),
        ("arms with different values stay separate", "dpa_nolick_weight: 0 → 0.9   [DPA]" in out),
    ]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(c for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweep_dir", help="sweep folder holding <run_id>/config.json")
    ap.add_argument("--run_ids", nargs="*", help="only these runs (default: all)")
    ap.add_argument("--baseline", help="run to compare against (default: the first run)")
    ap.add_argument("--sweep_py", help="sweep.py to parse (default: found above --sweep_dir)")
    ap.add_argument("--diff_only", action="store_true", help="print only the differences between runs")
    ap.add_argument("--demo", action="store_true", help="self-test on a synthetic sweep")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    if not a.sweep_dir:
        ap.print_help(); return 1
    return card(a.sweep_dir, a.run_ids, a.baseline, a.sweep_py, a.diff_only)


if __name__ == "__main__":
    sys.exit(main())
