"""Check every number in a manuscript against the numbers log a script produced.

Each number in the text (.md / .tex / .html / .txt) is classified against the log values:
  MATCH       a log value rounds to the text's number at the text's precision (also % ↔ fraction, |sign| not ignored)
  MISMATCH    no exact match, but a log value is close (within --rel_close): likely stale or mis-rounded
  UNSOURCED   no log value anywhere near it: the number has no recorded source
Skipped by default: figure/panel/section/equation references, years and dates, citation brackets, and small
integers (≤ --max_trivial_int, e.g. "two", "8 seeds" counts are often unsourced on purpose — use --strict to include).

Numbers log = JSON (any nesting; the key path is reported as the source) and/or a plain-text report (every number
on every line is a value; the line is the source). Regenerate it from the numbers script before every audit.

Usage:
    python audit_numbers.py --text docs/paper/results.md --log paper/draft_numbers_log.json [more logs …]
    python audit_numbers.py --text main.tex --log numbers.json report.txt --only MISMATCH UNSOURCED
    python audit_numbers.py --demo
"""
import argparse
import html
import json
import math
import os
import re
import sys
import tempfile

NUM = re.compile(r"(?<![A-Za-z0-9_.])([-−–+]?)(\d+(?:[.,]\d+)?|\.\d+)(\s*%)?(?![A-Za-z0-9_])")   # ASCII bounds: "3.4σ" counts, "5b" does not
SKIP_BEFORE = re.compile(r"(?:Fig(?:ure)?s?\.?|Ext(?:ended)?\.? ?Data ?Fig\.?|ED ?Fig\.?|Supp(?:lementary)?\.? ?Fig\.?|"
                         r"Table|Tab\.|Sec(?:tion)?\.?|§|Eq(?:uation)?s?\.?|ref\.?|panel|stage|step|v)\s*\(?$", re.I)
YEAR = re.compile(r"^(19|20)\d\d$")


def strip_markup(text, ext):
    if ext in (".html", ".htm"):
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    elif ext == ".tex":
        text = re.sub(r"(?<!\\)%.*", "", text)                                       # comments
        text = re.sub(r"\\(cite\w*|ref|eqref|label|includegraphics|url)\*?(\[[^\]]*\])?\{[^}]*\}", " ", text)
    text = re.sub(r"\[\d+(?:[,–-]\s*\d+)*\]", " ", text)                             # numeric citations [3,4]
    text = re.sub(r"\b\d{4}-\d\d-\d\d\b", " ", text)                                 # dates
    text = re.sub(r"`[^`]*`", " ", text)                                             # inline code
    return text


def extract_text_numbers(text, max_trivial_int=10, strict=False):
    """Yield dict(value, shown, decimals, pct, context, line)."""
    out = []
    for ln, line in enumerate(text.splitlines(), 1):
        for m in NUM.finditer(line):
            sign, digits, pct = m.group(1), m.group(2).replace(",", "."), bool(m.group(3))
            if not strict:
                if SKIP_BEFORE.search(line[:m.start()].rstrip()[-30:]):
                    continue
                if YEAR.match(digits) and not pct:
                    continue
                if "." not in digits and not pct and abs(int(digits)) <= max_trivial_int:
                    continue
            val = float(digits) * (-1 if sign in "-−–" and sign else 1)
            dec = len(digits.split(".")[1]) if "." in digits else 0
            ctx = line[max(0, m.start() - 40):m.end() + 25].strip()
            out.append(dict(value=val, shown=m.group(0).strip(), decimals=dec, pct=pct, context=ctx, line=ln))
    return out


def flatten_json(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten_json(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from flatten_json(v, f"{path}[{i}]")
    elif isinstance(obj, bool) or obj is None:
        return
    elif isinstance(obj, (int, float)) and math.isfinite(obj):
        yield path, float(obj)


def load_log(path):
    if path.endswith((".py", ".ipynb")):    # the script, not its output: every literal in code would "match"
        sys.exit(f"{path} is the numbers SCRIPT; run it and pass its output (JSON or the saved report) as --log")
    vals = []
    raw = open(path).read()
    try:
        vals += list(flatten_json(json.loads(raw)))
    except json.JSONDecodeError:
        for ln, line in enumerate(raw.splitlines(), 1):
            for m in NUM.finditer(line):
                digits = m.group(2).replace(",", ".")
                v = float(digits) * (-1 if m.group(1) in ("-", "−", "–") else 1)
                vals.append((f"{os.path.basename(path)}:{ln}: {line.strip()[:60]}", v))
    return vals


def candidates(t):
    """Values the text number may stand for: itself, and fraction ↔ percent."""
    c = [(t["value"], t["decimals"])]
    if t["pct"]:
        c.append((t["value"] / 100, t["decimals"] + 2))
    return c


def classify(t, log_vals, rel_close=0.10):
    """MATCH if a log value rounds to the text number at its precision. An unsigned text number may quote a
    magnitude (|log value|); a signed one must match the sign. Else MISMATCH if one is within rel_close."""
    signed = t["shown"][:1] in "+-−–"
    for tv, dec in candidates(t):
        tol = 0.5 * 10 ** (-dec) + 1e-12
        for src, lv in log_vals:
            if abs(lv - tv) <= tol or (not signed and abs(abs(lv) - tv) <= tol):
                return "MATCH", src, lv
    best = None
    for tv, _ in candidates(t):
        for src, lv in log_vals:
            d = abs(abs(lv) - abs(tv)) / max(abs(tv), 1e-12)
            if d <= rel_close and (best is None or d < best[0]):
                best = (d, src, lv)
    return ("MISMATCH", best[1], best[2]) if best else ("UNSOURCED", None, None)


def audit(text_path, log_paths, only=None, rel_close=0.10, max_trivial_int=10, strict=False, verbose=True):
    ext = os.path.splitext(text_path)[1].lower()
    nums = extract_text_numbers(strip_markup(open(text_path).read(), ext), max_trivial_int, strict)
    log_vals = [v for p in log_paths for v in load_log(p)]
    rows = []
    for t in nums:
        status, src, lv = classify(t, log_vals, rel_close)
        rows.append(dict(t, status=status, source=src, log_value=lv))
    if verbose:
        print(f"audit_numbers: {len(nums)} numbers in {text_path}, {len(log_vals)} values in {len(log_paths)} log(s)")
        for r in rows:
            if only and r["status"] not in only:
                continue
            extra = f"  ← {r['source']} = {r['log_value']:.6g}" if r["source"] else ""
            print(f"  [{r['status']:<9}] L{r['line']:<4} {r['shown']:>8}   …{r['context']}…{extra}")
        n = {s: sum(r["status"] == s for r in rows) for s in ("MATCH", "MISMATCH", "UNSOURCED")}
        print(f"SUMMARY: {n['MATCH']} match, {n['MISMATCH']} mismatch, {n['UNSOURCED']} unsourced")
    return rows


def _demo():
    d = tempfile.mkdtemp()
    log = os.path.join(d, "numbers.json")
    json.dump({"acc": {"s0": {"dpa": 0.9734, "dual": 0.81}}, "well_depth_sigma": -3.42,
               "pr": {"dpa": 37.2, "dual": 48.9}, "p_value": 0.004, "n_mice": 9}, open(log, "w"))
    txt = os.path.join(d, "results.md")
    open(txt, "w").write(
        "Networks reached 97.3% on DPA (Fig. 2b) and 0.81 on the dual task.\n"
        "The well sat at −3.4σ below the line (Liu et al. 2014 [12]).\n"
        "Participation ratio rose from 37 to 52 (p = 0.004, 9 mice).\n"
        "A stale effect size of 0.63 remains in the text.\n")
    rows = audit(txt, [log])
    st = {r["shown"]: r["status"] for r in rows}
    assert st["97.3%"] == "MATCH" and st["0.81"] == "MATCH" and st["−3.4"] == "MATCH", st
    assert st["37"] == "MATCH" and st["0.004"] == "MATCH", st
    assert st["52"] == "MISMATCH", st                    # 48.9 is close: stale or wrong
    assert st["0.63"] == "UNSOURCED", st
    assert "2014" not in st and "2" not in st and "12" not in st, st   # year, figure ref, citation skipped
    print("demo OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", help="manuscript file (.md/.tex/.html/.txt)")
    ap.add_argument("--log", nargs="*", default=[], help="numbers log(s): JSON and/or text reports")
    ap.add_argument("--only", nargs="*", choices=["MATCH", "MISMATCH", "UNSOURCED"], help="print only these classes")
    ap.add_argument("--rel_close", type=float, default=0.10, help="relative distance counted as a near miss")
    ap.add_argument("--max_trivial_int", type=int, default=10, help="skip integers up to this (counts, list items)")
    ap.add_argument("--strict", action="store_true", help="check every number, no skipping rules")
    ap.add_argument("--demo", action="store_true", help="run the built-in self-test")
    a = ap.parse_args()
    if a.demo:
        _demo(); return
    if not a.text or not a.log:
        ap.error("--text and --log are required (or --demo)")
    rows = audit(a.text, a.log, a.only, a.rel_close, a.max_trivial_int, a.strict)
    sys.exit(1 if any(r["status"] != "MATCH" for r in rows) else 0)


if __name__ == "__main__":
    main()
