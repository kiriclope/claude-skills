"""Collect the verdict cards on one question from a project's verdict log — the first step of concluding-research.

A card is a section starting with a '## ' heading (auditing-results §0). A card matches when its heading matches the
--match regex (case-insensitive; with --body, its body too). For each match the script prints its line, date, title,
and the first line of its Verdict / Criterion / Plan fields (Plan falls back to Question or Claim tested), and flags
what limits pooling:
  after-data   the hypotheses or criterion were written after the data, or the card says exploratory
  open-card    a pre-run card still marked RUNNING (no verdict yet)
  corrected    the card mentions a correction, supersession or re-reading (of itself or another card): read it
Reading the cards themselves is still required: the table only says which ones to read.

Usage:
    python collect_cards.py --log docs/verdicts.md --match "curriculum|pin|stop"           # headings
    python collect_cards.py --log docs/verdicts.md --match "curriculum" --body             # + bodies
    python collect_cards.py --log docs/verdicts.md --match "pin" --since 2026-10-28
    python collect_cards.py --demo
"""
import argparse
import re
import sys
import tempfile

FIELDS = ("Verdict", "Criterion", "Plan")
FLAGS = {
    "after-data": r"after the data|set after the run|exploratory|none was written before",
    "open-card": r"—\s*RUNNING",
    "corrected": r"supersed|correct(ed|ion)|was wrong|overstat|withdrawn|reads differently|partly came from|revis|re-?read",
}


def read_cards(path):
    """[(line_no, heading, body)] for every '## ' section of the log."""
    cards, lines = [], open(path).read().splitlines()
    starts = [i for i, l in enumerate(lines) if l.startswith("## ")] + [len(lines)]
    for a, b in zip(starts, starts[1:]):
        cards.append((a + 1, lines[a][3:].strip(), "\n".join(lines[a + 1:b])))
    return cards


ALIASES = {"Plan": ("Plan", "Question", "Claim tested")}


def field(body, name):
    """First line of a '**Name...:**' field (bullet or paragraph form), shortened; falls back to the name's aliases."""
    for n in ALIASES.get(name, (name,)):
        m = re.search(rf"\*\*{n}[^*]*:\*\*\s*(.+)", body)
        if m:
            return m.group(1).strip()[:110]
    return "—"


def collect(path, match, since="", body_too=False):
    rx = re.compile(match, re.I)
    out = []
    for line, head, body in read_cards(path):
        date = (re.match(r"(\d{4}-\d{2}-\d{2})", head) or [""])[0]
        if (since and date and date < since) or not (rx.search(head) or (body_too and rx.search(body))):
            continue
        flags = [k for k, r in FLAGS.items() if re.search(r, head + "\n" + body, re.I)]
        out.append({"line": line, "date": date, "title": re.sub(r"^\d{4}-\d{2}-\d{2}\s*[—·-]\s*", "", head),
                    "flags": flags, **{f: field(body, f) for f in FIELDS}})
    return out


def report(cards):
    for c in cards:
        print(f"L{c['line']:<5} {c['date']}  {c['title'][:100]}")
        print(f"        flags: {', '.join(c['flags']) or '—'}")
        for f in FIELDS:
            print(f"        {f}: {c[f]}")
    print(f"SUMMARY: {len(cards)} card(s); after-data {sum('after-data' in c['flags'] for c in cards)}, "
          f"open {sum('open-card' in c['flags'] for c in cards)}, corrected {sum('corrected' in c['flags'] for c in cards)}")


def _demo():
    log = ("# Verdicts\n\n## 2026-10-27 — lever A solves the task: SOLVED\n- **Criterion (set after the run):** P ≥ 0.95\n"
           "- **Verdict:** kept\n\n## 2026-10-28 · lever B on the task — RUNNING\nWHY x\n\n"
           "## 2026-10-29 — unrelated card\n**Question:** about lever A again\n**Verdict:** open\n")
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(log)
    cards = collect(f.name, r"lever")
    checks = [("2 of 3 cards match 'lever'", len(cards) == 2),
              ("card 1: after-data flag, verdict and criterion read",
               cards[0]["flags"] == ["after-data"] and cards[0]["Verdict"] == "kept" and cards[0]["Criterion"] == "P ≥ 0.95"),
              ("card 2: open pre-run card", cards[1]["flags"] == ["open-card"] and cards[1]["date"] == "2026-10-28"),
              ("--since drops the earlier card", len(collect(f.name, r"lever", since="2026-10-28")) == 1),
              ("--body also finds the card that names the lever in its body, Plan from Question",
               len(collect(f.name, r"lever", body_too=True)) == 3
               and collect(f.name, r"lever", body_too=True)[2]["Plan"] == "about lever A again")]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", help="the verdict log (project.yaml → verdict_log, default docs/verdicts.md)")
    ap.add_argument("--match", help="regex matched against each card's heading and body (case-insensitive)")
    ap.add_argument("--body", action="store_true", help="match card bodies too, not only headings")
    ap.add_argument("--since", default="", help="only cards dated on or after YYYY-MM-DD")
    ap.add_argument("--demo", action="store_true", help="run the built-in self-test")
    a = ap.parse_args()
    if a.demo:
        sys.exit(_demo())
    if not (a.log and a.match):
        ap.print_help()
        sys.exit(0)
    report(collect(a.log, a.match, a.since, a.body))
