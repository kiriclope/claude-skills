"""Claims ledger: every claim of a paper with the controls that could falsify it, run and recorded.

The ledger (YAML, one entry per claim) says, for each claim: its kind, its unit of replication and n, the
number it rests on, and its controls — what result would falsify the claim, the command that runs the control,
the output it wrote, the result and a status. This script checks the ledger against the rules and the files:

  CONTROLLED     every control type the claim's kind requires was run and passed; outputs exist and are newer
                 than the data the claim rests on
  FAILED         a control came out against the claim: change the claim (weaken, qualify, remove), never the control
  UNCONTROLLED   a required control type is missing from the ledger
  PENDING        a required control is listed but not run yet (status pending, or no result)
  STALE          a control's output is missing, or older than the claim's source (the data changed after the control)
and, with --text:
  GONE           the claim's text fragment is no longer in the manuscript (the ledger is out of date)
  UNLEDGERED     a manuscript sentence that reads like a claim (a statistic or a claim verb) and that no ledger
                 entry covers — a candidate, judged by a person

Required control types per kind (defaults; `validation: {required: {kind: [types]}}` in .claude/project.yaml):
  effect          null              X is above chance / non-zero / increases
  difference      null, confound    A differs from B (arms, conditions, groups)
  null-result     positive          X does not change: the method can detect a change of the size that matters
  generalization  held-out          holds across sessions / animals / seeds / noise levels it was not fit on
  mechanism       ablation          X happens because of Y: removing Y removes X
  correlation     null, confound    X tracks Y: not through a third variable
Control types: null (shuffle, permutation, null model), confound (nuisance or arm difference matched), positive
(planted effect recovered), held-out, ablation, metric (same claim under the alternative metric), matched-n,
units (unit-by-unit table, k/N), ground-truth. Also flagged: n below `validation.min_n` (default 5) for the unit.

Usage:
    python claims_ledger.py --ledger docs/paper/claims.yaml [--text docs/paper/results_draft.md]
    python claims_ledger.py [--text …]                  # ledger from validation.claims_file in .claude/project.yaml
    python claims_ledger.py --init --text docs/paper/results_draft.md > claims.yaml    # skeleton from the text
    … --start '^## Abstract' --stop '^## Methods'      # only that part of the text (revision notes, methods out)
    python claims_ledger.py --demo
Exit 1 when any claim is not CONTROLLED or the text has GONE / UNLEDGERED items.
"""
import argparse
import datetime as dt
import os
import re
import sys
import tempfile

import yaml

REQUIRED = {"effect": ["null"], "difference": ["null", "confound"], "null-result": ["positive"],
            "generalization": ["held-out"], "mechanism": ["ablation"], "correlation": ["null", "confound"]}
TYPES = {"null", "confound", "positive", "held-out", "ablation", "metric", "matched-n", "units", "ground-truth"}
MIN_N = 5
ORDER = ["FAILED", "UNCONTROLLED", "STALE", "PENDING", "CONTROLLED"]
STAT = re.compile(r"\bp\s*[<=>≤]\s*0?\.\d|±|\bn\s*=\s*\d|\d\s*%|\bCI\b|\bσ\b|\bd\s*=\s*\d")
VERB = re.compile(r"\b(shows?|showed|reveals?|demonstrates?|increase[sd]?|decrease[sd]?|predicts?|explains?|"
                  r"requires?|caused?|because|above chance|significant(ly)?|robust(ly)?|generali[sz]es?|"
                  r"consistent with|does not|did not|no (?:change|effect|difference)|depends? on|tracks?)\b", re.I)
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def _norm(s):
    return " ".join(re.sub(r"[*_`]", "", s).split()).lower()


def _mtime(path, base):
    p = os.path.join(base, os.path.expanduser(path)) if path else ""
    return os.path.getmtime(p) if p and os.path.exists(p) else None


def check_claim(c, base, required, min_n):
    """(verdict, [reasons]) for one ledger entry. Paths are relative to base (the ledger's folder)."""
    reasons, verdicts = [], set()
    kind = c.get("kind")
    controls = c.get("controls") or []
    for t in sorted({x.get("type") for x in controls} - TYPES - {None}):
        reasons.append(f"unknown control type '{t}' (known: {', '.join(sorted(TYPES))})")
    if kind not in required:
        reasons.append(f"kind '{kind}' unknown: one of {', '.join(required)}")
        verdicts.add("UNCONTROLLED")
    for t in required.get(kind, []):
        if not any(x.get("type") == t for x in controls):
            reasons.append(f"no '{t}' control (required for {kind} claims)")
            verdicts.add("UNCONTROLLED")
    src_path = str(c.get("source", "")).split(":")[0]
    src_t = _mtime(src_path, base)
    for x in controls:
        name = x.get("name") or x.get("type")
        status = (x.get("status") or "pending").lower()
        if not x.get("falsifies_if"):
            reasons.append(f"'{name}': no falsifies_if — write what result would refute the claim before running it")
        if status == "failed":
            reasons.append(f"'{name}' FAILED: {x.get('result', 'no result recorded')}")
            verdicts.add("FAILED")
            continue
        if status != "passed" or not x.get("result"):
            reasons.append(f"'{name}' not run yet" + (f" (command: {x['command']})" if x.get("command") else ""))
            verdicts.add("PENDING")
            continue
        out_t = _mtime(x.get("output"), base)
        if x.get("output") and out_t is None:
            reasons.append(f"'{name}': output {x['output']} is missing")
            verdicts.add("STALE")
        elif out_t is not None and src_t is not None and out_t < src_t - 1:      # 1 s: same-run writes
            reasons.append(f"'{name}': output older than the claim's source {src_path} (re-run the control)")
            verdicts.add("STALE")
        elif not x.get("output"):
            reasons.append(f"'{name}': no output file recorded (cannot tell whether it is current)")
    n, unit = c.get("n"), c.get("unit")
    if isinstance(n, int) and n < min_n:
        reasons.append(f"n = {n} {unit or 'units'}: below {min_n}, exploratory only — say so in the text")
    if c.get("source") and src_path and src_t is None:
        reasons.append(f"source {src_path} not found")
    verdict = next((v for v in ORDER if v in verdicts), "CONTROLLED")
    return verdict, reasons


def claim_sentences(text):
    """Sentences that read like claims: a statistic or a claim verb, outside headings, code and captions' labels."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    out = []
    for para in re.split(r"\n\s*\n", text):
        if para.lstrip().startswith(("#", "|", "<!--")):
            continue
        for s in SENT.split(" ".join(para.split())):
            if len(s) > 30 and (STAT.search(s) or VERB.search(s)):
                out.append(s.strip())
    return out


def section(text, start=None, stop=None):
    """The text from the first heading matching start (regex) to the first later heading matching stop."""
    lines = text.splitlines()
    heads = [i for i, l in enumerate(lines) if l.startswith("#")]
    a = next((i for i in heads if start and re.search(start, lines[i])), 0 if not start else None)
    if a is None:
        sys.exit(f"--start '{start}': no heading matches")
    b = next((i for i in heads if i > a and stop and re.search(stop, lines[i])), len(lines))
    return "\n".join(lines[a:b])


def check_text(claims, text, start=None, stop=None):
    """(gone, unledgered): ledger fragments missing from the whole text; claim-like sentences in the
    start–stop section that no fragment covers."""
    t = _norm(text)
    frags = [(c.get("id"), _norm(c.get("text", ""))) for c in claims]
    gone = [cid for cid, f in frags if f and f not in t]
    unledgered = [s for s in claim_sentences(section(text, start, stop))
                  if not any(f and f in _norm(s) for _, f in frags)]
    return gone, unledgered


def report(ledger_path, text_path=None, cfg=None, start=None, stop=None):
    cfg = cfg or {}
    with open(ledger_path) as f:
        led = yaml.safe_load(f) or {}
    claims = led.get("claims") or []
    base = os.path.dirname(os.path.abspath(ledger_path))
    required = {**REQUIRED, **(cfg.get("required") or {})}
    min_n = cfg.get("min_n", MIN_N)
    rows = [(c.get("id", f"#{i}"), *check_claim(c, base, required, min_n)) for i, c in enumerate(claims, 1)]
    print(f"CLAIMS LEDGER · {ledger_path} · {len(claims)} claim(s)")
    for cid, verdict, reasons in sorted(rows, key=lambda r: ORDER.index(r[1])):
        print(f"  {verdict:12} {cid}")
        for r in reasons:
            print(f"               - {r}")
    gone = unledgered = []
    if text_path:
        with open(text_path) as f:
            gone, unledgered = check_text(claims, f.read(), start, stop)
        for cid in gone:
            print(f"  GONE         {cid}: its text fragment is not in {os.path.basename(text_path)}")
        for s in unledgered:
            print(f"  UNLEDGERED   \"{s[:150]}{'…' if len(s) > 150 else ''}\"")
    counts = {v: sum(r[1] == v for r in rows) for v in ORDER}
    bad = len(rows) - counts["CONTROLLED"] + len(gone) + len(unledgered)
    print("SUMMARY: " + ", ".join(f"{counts[v]} {v.lower()}" for v in ORDER if counts[v]) +
          (f"; text: {len(gone)} gone, {len(unledgered)} unledgered" if text_path else "") +
          (" — all claims controlled" if not bad else ""))
    return {"rows": rows, "gone": gone, "unledgered": unledgered, "bad": bad}


def init(text_path, start=None, stop=None):
    """A skeleton ledger: one entry per claim-like sentence, to be classified and given controls by hand."""
    with open(text_path) as f:
        sents = claim_sentences(section(f.read(), start, stop))
    entries = [{"id": f"c{i:02d}", "text": s[:120], "kind": "TODO: effect | difference | null-result | "
                "generalization | mechanism | correlation", "unit": "TODO", "n": None, "source": "TODO",
                "controls": []} for i, s in enumerate(sents, 1)]
    print(f"# claims ledger for {text_path} — generated {dt.date.today()}; keep one entry per claim, drop non-claims")
    print(yaml.safe_dump({"claims": entries}, sort_keys=False, allow_unicode=True, width=120))


def _project_cfg(start):
    """The `validation:` block of the nearest .claude/project.yaml above `start`, and that project's root."""
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, ".claude", "project.yaml")
        if os.path.exists(p):
            with open(p) as f:
                return (yaml.safe_load(f) or {}).get("validation") or {}, d
        if os.path.dirname(d) == d:
            return {}, None
        d = os.path.dirname(d)


def _demo():
    text = """# Results

The sample is decoded above chance throughout the delay (0.81 ± 0.04, p < 0.001, n = 9 mice).
Go/No-Go training leaves the DPA memory intact (after_gng/dpa 0.93, 8/8 seeds).
The choice axis does not change with learning.
Optogenetic silencing during the delay reduces performance because it removes the memory.
These results are summarized in Fig. 2.
The lick rate increases in DualGo trials relative to DPA trials (p = 0.02, n = 9 mice).
"""
    checks = []
    with tempfile.TemporaryDirectory() as d:
        for name in ("decoder_out.json", "shuffle.json", "numbers.json", "old_ablation.json"):
            with open(os.path.join(d, name), "w") as f:
                f.write("{}")
        now = dt.datetime.now().timestamp()
        os.utime(os.path.join(d, "numbers.json"), (now - 3600, now - 3600))  # the data the claims rest on
        os.utime(os.path.join(d, "old_ablation.json"), (now - 7200, now - 7200))   # run before the data changed
        ledger = {"claims": [
            {"id": "sample_decoding", "text": "The sample is decoded above chance throughout the delay",
             "kind": "effect", "unit": "mouse", "n": 9, "source": "numbers.json:sample.acc",
             "controls": [{"name": "label shuffle", "type": "null", "falsifies_if": "score within the shuffle 95%",
                           "result": "null 0.50 ± 0.03, real 0.81", "status": "passed", "output": "shuffle.json"}]},
            {"id": "retention", "text": "Go/No-Go training leaves the DPA memory intact", "kind": "effect",
             "unit": "seed", "n": 8, "source": "numbers.json:retention",
             "controls": [{"name": "after_gng/dpa, not dual_dpa", "type": "metric",
                           "falsifies_if": "after_gng/dpa < 0.6 while dual_dpa stays high", "status": "failed",
                           "result": "after_gng/dpa 0.55: Dual retrained rank 0 and hid the damage"}]},
            {"id": "choice_axis_stable", "text": "The choice axis does not change with learning",
             "kind": "null-result", "unit": "mouse", "n": 3, "controls": []},
            {"id": "opto_mechanism", "text": "Optogenetic silencing during the delay reduces performance",
             "kind": "mechanism", "unit": "mouse", "n": 9, "source": "numbers.json:opto",
             "controls": [{"name": "laser-off sessions", "type": "ablation", "falsifies_if": "same drop OFF vs OFF",
                           "result": "shift 3x OFF-vs-OFF noise", "status": "passed",
                           "output": "old_ablation.json"}]},
            {"id": "removed_claim", "text": "Dimensionality collapses after learning", "kind": "effect",
             "unit": "mouse", "n": 9, "controls": [{"name": "matched n", "type": "null", "falsifies_if": "x",
                                                    "result": "ok", "status": "passed"}]},
        ]}
        lp, tp = os.path.join(d, "claims.yaml"), os.path.join(d, "results.md")
        with open(lp, "w") as f:
            yaml.safe_dump(ledger, f, sort_keys=False)
        with open(tp, "w") as f:
            f.write(text)
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()) as out:
            res = report(lp, tp)
        print(out.getvalue())
        v = {cid: verdict for cid, verdict, _ in res["rows"]}
        reasons = {cid: " ".join(r) for cid, _, r in res["rows"]}
        checks += [
            ("a claim with its null control run and current is CONTROLLED", v["sample_decoding"] == "CONTROLLED"),
            ("a control that came out against the claim makes it FAILED (the hidden-damage metric)",
             v["retention"] == "FAILED"),
            ("a null result without a positive control is UNCONTROLLED; n = 3 flagged",
             v["choice_axis_stable"] == "UNCONTROLLED" and "n = 3" in reasons["choice_axis_stable"]),
            ("a control older than the data it controls is STALE", v["opto_mechanism"] == "STALE"),
            ("a ledger claim no longer in the text is GONE", res["gone"] == ["removed_claim"]),
            ("a claim-like sentence with no ledger entry is UNLEDGERED; a figure pointer is not",
             any("lick rate increases" in s for s in res["unledgered"])
             and not any("summarized in Fig" in s for s in res["unledgered"])),
        ]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(c for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger",
                    help="claims ledger (YAML); default: validation.claims_file of the project")
    ap.add_argument("--text", help="manuscript (.md / .tex / .txt): GONE and UNLEDGERED checks, or --init source")
    ap.add_argument("--init", action="store_true",
                    help="print a skeleton ledger from the claim-like sentences of --text")
    ap.add_argument("--start", help="regex: scan the text from the first heading matching it (e.g. '^## Abstract')")
    ap.add_argument("--stop", help="regex: … to the first later heading matching it (e.g. '^## Methods')")
    ap.add_argument("--demo", action="store_true", help="self-test on a throwaway ledger and manuscript")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    if a.init:
        if not a.text:
            ap.error("--init needs --text")
        init(a.text, a.start, a.stop)
        return 0
    if not a.ledger:
        cfg, root = _project_cfg(os.getcwd())
        if not (root and cfg.get("claims_file")):
            ap.error("--ledger is required (or validation.claims_file in .claude/project.yaml, or --init / --demo)")
        a.ledger = os.path.join(root, cfg["claims_file"])
    cfg, _ = _project_cfg(os.path.dirname(os.path.abspath(a.ledger)))
    res = report(a.ledger, a.text, cfg, a.start, a.stop)
    return 1 if res["bad"] else 0


if __name__ == "__main__":
    sys.exit(main())
