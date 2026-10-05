"""Check Python files against the house readability conventions — the mechanical part of a review.

What it flags, by severity:
  error  a comment that swallowed code (`a = 1  # note; b = 2`)
         a silent fallback (bare `except:`, or `except Exception:` whose body is only pass/continue)
         a hard-coded value for a quantity the run's config derives (project.yaml code_check.derived_names)
  warn   an opaque name (a part of ≥ 4 letters with no vowel: k1zcnl, sclnl)
         a CLI script without a module docstring, or whose docstring has no Usage line
         argparse.ArgumentParser without description=__doc__
         lines longer than max_line; control flow nested deeper than max_depth
         hex colors in a plotting file outside the project's style modules (use cbstyle / project colors)
  info   functions longer than max_function_lines, TODO/FIXME, commented-out code,
         British spelling in comments and docstrings (identifiers are left alone)

By default only lines changed since git HEAD are checked (the review of what was just written);
untracked files are checked whole. --all audits every line.

Settings come from `code_check:` in .claude/project.yaml (found by walking up from each file):
  max_line (120), max_depth (4), max_function_lines (80), derived_names ([]),
  derived_callees ([] = any non-plotting call), config_files ([]), style_modules ([]).

Usage:
    python readability_check.py FILE [FILE ...] [--all] [--project_yaml PATH]
    python readability_check.py --demo
"""
import argparse
import ast
import io
import os
import re
import subprocess
import sys
import tempfile
import tokenize

DEFAULTS = dict(max_line=120, max_depth=4, max_function_lines=80, derived_names=[], derived_callees=[],
                config_files=[], style_modules=[])
# matplotlib / seaborn calls: their alpha= is transparency, not a model rate
PLOT_CALLS = {"plot", "scatter", "fill_between", "fill_betweenx", "fill", "axhline", "axvline", "axhspan", "axvspan",
              "imshow", "matshow", "bar", "barh", "errorbar", "hist", "hist2d", "text", "annotate", "streamplot",
              "quiver", "contour", "contourf", "pcolormesh", "pcolor", "legend", "add_patch", "add_collection",
              "Rectangle", "Circle", "Ellipse", "Polygon", "Wedge", "Arc", "FancyArrowPatch", "FancyBboxPatch",
              "Line2D", "Patch", "LineCollection", "PolyCollection", "set_alpha", "violinplot", "boxplot", "step",
              "stairs", "hexbin", "plot_surface", "plot_trisurf", "eventplot", "vlines", "hlines", "arrow",
              "tripcolor", "tricontourf", "stem", "kdeplot", "lineplot", "scatterplot", "heatmap", "regplot",
              "histplot", "colorbar", "plot_fixed_points", "plot_manifold", "plot_mean_sem", "sem_band"}
AMBIGUOUS_NAMES = {"alpha"}     # also a matplotlib keyword: plain `alpha = 0.3` assignments are not flagged
VOWELS = set("aeiouy")
OK_PARTS = {"ckpt", "ckpts", "fpts", "pths", "msgs", "cfgs", "rngs", "srcs", "dsts", "ctxs", "lsts", "txts"}   # standard abbreviations
BRITISH_ONLY = re.compile(r"\b(behaviours?|behaviour|analys(e|ed|es|ing)|colours?|coloured|normalis(e|ed|ing|ation)|"
                          r"centre[sd]?|modelling|labelled|labelling|neighbours?|optimis(e|ed|ing|ation)|"
                          r"initialis(e|ed|ing|ation)|grey)\b", re.I)
HEX = re.compile(r"#[0-9a-fA-F]{6}")
CODE_IN_COMMENT = re.compile(r";\s*[A-Za-z_]\w*\s*(=[^=]|\()")
CONTROL = (ast.For, ast.AsyncFor, ast.While, ast.If, ast.With, ast.AsyncWith, ast.Try)


# ── settings ────────────────────────────────────────────────────────────────────────────────────

def find_project_yaml(path):
    d = os.path.dirname(os.path.abspath(path))
    while True:
        p = os.path.join(d, ".claude", "project.yaml")
        if os.path.exists(p):
            return p
        if os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


def load_settings(yaml_path):
    cfg = dict(DEFAULTS)
    if not yaml_path:
        return cfg, None
    try:
        import yaml
        cfg.update((yaml.safe_load(open(yaml_path)) or {}).get("code_check") or {})
    except ImportError:
        print(f"note: PyYAML not installed — using default settings, not {yaml_path}", file=sys.stderr)
    return cfg, os.path.dirname(os.path.dirname(os.path.abspath(yaml_path)))   # project root


def changed_lines(path):
    """Set of changed line numbers vs HEAD; None = check every line (untracked, new, or not in git)."""
    d, f = os.path.dirname(os.path.abspath(path)), os.path.basename(path)
    tracked = subprocess.run(["git", "-C", d, "ls-files", "--error-unmatch", f], capture_output=True)
    if tracked.returncode != 0:
        return None
    diff = subprocess.run(["git", "-C", d, "diff", "-U0", "HEAD", "--", f], capture_output=True, text=True).stdout
    lines = set()
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff, re.M):
        start, n = int(m.group(1)), int(m.group(2) or 1)
        lines.update(range(start, start + n))
    return lines


# ── checks ──────────────────────────────────────────────────────────────────────────────────────

def _num(node):
    """Numeric value of a literal (incl. -x), else None."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _num(node.operand)
        return -v if v is not None else None
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    return None


def _opaque(name):
    for part in name.strip("_").lower().split("_"):
        letters = re.sub(r"[^a-z]", "", part)
        if len(letters) >= 4 and not (set(letters) & VOWELS) and letters not in OK_PARTS:
            return part
    return None


def check_ast(tree, cfg, rel, is_config_file):
    out = []                                    # (line, severity, rule, message, span_end)
    derived = set(cfg["derived_names"])

    # silent fallbacks
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            body_trivial = all(isinstance(s, (ast.Pass, ast.Continue)) for s in node.body)
            if node.type is None:
                out.append((node.lineno, "error", "silent-except", "bare `except:` — catch the specific error and "
                            "say what failed", node.lineno))
            elif isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException") and body_trivial:
                out.append((node.lineno, "error", "silent-except", f"`except {node.type.id}: pass` hides failures — "
                            "let it raise or report it", node.lineno))

    # hard-coded derived quantities (call keywords and plain assignments outside class bodies / config files)
    if derived and not is_config_file:
        class_body_lines = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for s in node.body:
                    if isinstance(s, (ast.Assign, ast.AnnAssign)):
                        class_body_lines.add(s.lineno)
        callees = set(cfg["derived_callees"])
        for node in ast.walk(tree):
            hits = []
            if isinstance(node, ast.Call):
                fn = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                plotting = fn in PLOT_CALLS or re.search(r"plot|draw|arrow|overlay|line|patch|legend|annot|^_|^dict$",
                                                         fn, re.I)
                watched = fn in callees if callees else not plotting
                if watched:
                    hits = [(k.arg, k.value, node.lineno) for k in node.keywords if k.arg in derived]
            elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.lineno not in class_body_lines:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                hits = [(t.id, node.value, node.lineno) for t in targets
                        if isinstance(t, ast.Name) and t.id in derived and t.id not in AMBIGUOUS_NAMES
                        and node.value is not None]
            for name, value, line in hits:
                v = _num(value)
                if v is not None and v not in (0, 1):
                    out.append((line, "error", "hard-coded-derived", f"`{name} = {v}` is hard-coded — derive it "
                                "from the run's config (single source of truth)", line))

    # opaque names (first store of each name)
    seen = set()
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names = [(node.id, node.lineno)]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [(node.name, node.lineno)]
        elif isinstance(node, ast.arg):
            names = [(node.arg, node.lineno)]
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            names = [(node.attr, node.lineno)]
        for name, line in names:
            part = _opaque(name)
            if part and name not in seen:
                seen.add(name)
                out.append((line, "warn", "opaque-name", f"`{name}`: '{part}' reads as an initialism — use words "
                            "or the paper's symbol", line))

    # CLI scripts: docstring with Usage; ArgumentParser(description=__doc__)
    is_cli = any(isinstance(n, ast.If) and "__main__" in ast.unparse(n.test) for n in tree.body)
    doc = ast.get_docstring(tree)
    if is_cli and not doc:
        out.append((1, "warn", "module-docstring", "CLI script without a module docstring (what it decides, "
                    "conventions, Usage: exact command)", 1))
    elif is_cli and not re.search(r"(?im)^\s*(usage|run)\b", doc or ""):
        out.append((1, "warn", "usage-block", "module docstring has no `Usage:` line with the exact command", 1))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and ast.unparse(node.func).endswith("ArgumentParser"):
            if not any(k.arg == "description" for k in node.keywords):
                out.append((node.lineno, "warn", "argparse-help", "ArgumentParser without description=__doc__ "
                            "(and formatter_class=RawDescriptionHelpFormatter)", node.lineno))

    # function length and nesting depth
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            n = (node.end_lineno or node.lineno) - node.lineno + 1
            if n > cfg["max_function_lines"]:
                out.append((node.lineno, "info", "long-function", f"`{node.name}` is {n} lines — split where it "
                            "changes subject (load / compute / plot)", node.lineno))   # change review: new defs only
            deepest = [0, node.lineno]

            def walk(n_, depth):
                for child in ast.iter_child_nodes(n_):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                        continue                        # nested definitions are checked on their own
                    d = depth + isinstance(child, CONTROL)
                    if d > deepest[0]:
                        deepest[:] = [d, getattr(child, "lineno", deepest[1])]
                    walk(child, d)
            walk(node, 0)
            if deepest[0] > cfg["max_depth"]:
                out.append((deepest[1], "warn", "deep-nesting", f"`{node.name}` nests {deepest[0]} levels deep — "
                            "return early or extract the inner loop", deepest[1]))

    # hex colors in plotting files outside the style modules
    imports_mpl = any(isinstance(n, (ast.Import, ast.ImportFrom)) and "matplotlib" in ast.unparse(n)
                      for n in ast.walk(tree))
    if imports_mpl and rel not in cfg["style_modules"]:
        hex_lines = sorted({n.lineno for n in ast.walk(tree)                 # string literals only, never comments
                            if isinstance(n, ast.Constant) and isinstance(n.value, str) and HEX.fullmatch(n.value)})
        for i in hex_lines:
            out.append((i, "warn", "hex-color", "hard-coded hex color — use cbstyle / the project's color "
                        "constants (colorblind-safe, one map)", i))
    return out


def _scope(tree, line):
    """Innermost function containing `line`, else the module."""
    best = tree
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno <= line <= (node.end_lineno or 0):
            if best is tree or node.lineno > best.lineno:
                best = node
    return best


def _swallowed(text, tree, line):
    """Name assigned after `;` in a trailing comment that the code later reads but never assigns, else None.

    `a = 1  # note; b = 2` hides the definition of b; a prose formula (`# prefactor; sigma = noise * √…`)
    is left alone because nothing in the scope reads an otherwise undefined `sigma`."""
    seg = text.split(";", 1)[1].strip()
    try:
        stored = {n.id for n in ast.walk(ast.parse(seg)) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    except SyntaxError:
        return None
    scope = _scope(tree, line)
    for name in stored:
        defined = any(isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Store) for n in ast.walk(scope))
        defined |= any(isinstance(n, ast.arg) and n.arg == name for n in ast.walk(scope))
        used_later = any(isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load) and n.lineno > line
                         for n in ast.walk(scope))
        if used_later and not defined:
            return name
    return None


def check_tokens(src, cfg, tree):
    out = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError):
        return out
    code_lines = {t.start[0] for t in toks if t.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                                                              tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER)}
    for t in toks:
        if t.type == tokenize.STRING and t.string.startswith(('"""', "'''", 'r"""')):
            for k, line in enumerate(t.string.splitlines()):
                m = BRITISH_ONLY.search(line)
                if m:
                    out.append((t.start[0] + k, "info", "spelling", f"'{m.group(0)}' — American English in "
                                "comments and docs (leave identifiers as they are)", t.start[0] + k))
        if t.type != tokenize.COMMENT:
            continue
        line, text = t.start[0], t.string.lstrip("#").strip()
        name = _swallowed(text, tree, line) if line in code_lines and CODE_IN_COMMENT.search(text) else None
        if name:
            out.append((line, "error", "code-in-comment", f"`{name}` is defined only inside this comment but used "
                        "below — the comment swallowed its definition", line))
        if re.search(r"\b(TODO|FIXME|XXX)\b", text):
            out.append((line, "info", "todo", f"{text[:60]}", line))
        m = BRITISH_ONLY.search(text)
        if m:
            out.append((line, "info", "spelling", f"'{m.group(0)}' — American English in comments and docs "
                        "(leave identifiers as they are)", line))
        if line not in code_lines and re.search(r"[=(]", text) and len(text.split()) <= 8:
            try:
                ast.parse(text)
                out.append((line, "info", "commented-code", "commented-out code — delete it, or say why it stays",
                            line))
            except SyntaxError:
                pass
    long_lines = [i for i, l in enumerate(src.splitlines(), 1) if len(l) > cfg["max_line"]]
    for i in long_lines:
        out.append((i, "warn", "long-line", f"{len(src.splitlines()[i - 1])} > {cfg['max_line']} characters", i))
    return out


# ── driver ──────────────────────────────────────────────────────────────────────────────────────

def check_file(path, all_lines=False, yaml_path=None):
    cfg, root = load_settings(yaml_path or find_project_yaml(path))
    rel = os.path.relpath(os.path.abspath(path), root) if root else os.path.basename(path)
    src = open(path, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [(e.lineno or 1, "error", "syntax", str(e.msg))], "all lines"
    findings = check_ast(tree, cfg, rel, rel in cfg["config_files"]) + check_tokens(src, cfg, tree)
    scope = None if all_lines else changed_lines(path)
    if scope is not None:
        findings = [f for f in findings if any(l in scope for l in range(f[0], f[4] + 1))]
    # collapse long-line findings to one row per file
    ll = [f for f in findings if f[2] == "long-line"]
    findings = [f for f in findings if f[2] != "long-line"]
    if ll:
        findings.append((ll[0][0], "warn", "long-line", f"{len(ll)} line(s) > {cfg['max_line']} characters "
                         f"(first at L{ll[0][0]})", ll[0][0]))
    order = {"error": 0, "warn": 1, "info": 2}
    findings = sorted({(f[0], f[1], f[2], f[3]) for f in findings}, key=lambda f: (order[f[1]], f[0]))
    label = "all lines" if scope is None else f"{len(scope)} changed line(s) vs HEAD"
    return findings, label


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="Python files to check")
    ap.add_argument("--all", action="store_true", help="check every line, not only lines changed since HEAD")
    ap.add_argument("--project_yaml", default=None, help="settings file (default: nearest .claude/project.yaml)")
    ap.add_argument("--demo", action="store_true", help="run the built-in self-test")
    args = ap.parse_args(argv)
    if args.demo:
        return _demo()
    if not args.files:
        ap.print_help()
        return 0
    totals = {"error": 0, "warn": 0, "info": 0}
    for path in args.files:
        findings, label = check_file(path, args.all, args.project_yaml)
        print(f"{path}  ({label})" + ("  ✓" if not findings else ""))
        for line, sev, rule, msg in findings:
            print(f"  L{line:<5d} {sev:5s}  {rule:18s} {msg}")
            totals[sev] += 1
    print(f"SUMMARY: {totals['error']} error, {totals['warn']} warn, {totals['info']} info "
          f"in {len(args.files)} file(s)" + ("  ✓" if not totals["error"] and not totals["warn"] else ""))
    return 1 if totals["error"] else 0


BAD = '''import argparse
import matplotlib.pyplot as plt

def run(cfg):
    model = build(cfg, alpha=0.075, alpha_rec=0.075)     # copied from an old sweep
    k1zcnl = 3; sclnl = 2  # pin the cue; nolick = 1
    print(k1zcnl + sclnl + nolick)
    try:
        x = load()
    except:
        x = None
    for a in range(3):
        for b in range(3):
            if a:
                with open("f") as f:
                    if b:
                        while True:
                            break
    # TODO: normalise the colour axis
    # y = compute(x)
    plt.plot([0, 1], color="#d62728")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
'''

GOOD = '''"""Score every run of a sweep against its own targets.

Usage:
    python score.py --sweep_dir results/x
"""
import argparse

import matplotlib.pyplot as plt
from cbstyle import PAIR


def score(run, alpha):
    """Fraction of trials on the right side of the boundary (alpha comes from run_dt_alpha(cfg))."""
    kappa_end = run.kappa[:, -1]                  # (trials,) end-of-delay readout
    scale = 2.0                                   # input prefactor; sigma = scale * sqrt(1 - exp(-2 alpha))
    plt.fill_between([0, 1], 0, 1, color=PAIR[0], alpha=0.3)   # transparency, not the model rate
    return float((kappa_end > 0).mean()), PAIR[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sweep_dir", required=True)
    return ap.parse_args()


if __name__ == "__main__":
    main()
'''


def _demo():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, ".claude"))
        with open(os.path.join(d, ".claude", "project.yaml"), "w") as f:
            f.write("code_check:\n  derived_names: [alpha, alpha_rec]\n")
        bad, good = os.path.join(d, "bad.py"), os.path.join(d, "good.py")
        open(bad, "w").write(BAD)
        open(good, "w").write(GOOD)
        fb, _ = check_file(bad, all_lines=True)
        fg, _ = check_file(good, all_lines=True)
    rules_bad = {r for _, _, r, _ in fb}
    want = {"hard-coded-derived", "opaque-name", "code-in-comment", "silent-except", "deep-nesting",
            "module-docstring", "argparse-help", "todo", "spelling", "commented-code", "hex-color"}
    missing = want - rules_bad
    for line, sev, rule, msg in fb:
        print(f"  bad  L{line:<3d} {sev:5s} {rule:18s} {msg}")
    print(f"  good: {len(fg)} finding(s)" + (f" {fg}" if fg else ""))
    ok = not missing and not [f for f in fg if f[1] in ("error", "warn")]
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'}" + (f" — missing {sorted(missing)}" if missing else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
