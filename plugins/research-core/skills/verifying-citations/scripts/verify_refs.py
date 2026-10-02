"""Verify references against Crossref and OpenAlex before they are cited.

Input (one of):
  * a BibTeX file (.bib)                       → checks title, first-author surname, year, venue, DOI
  * a text file, one reference per line        → free text ("Mastrogiuseppe & Ostojic 2018 Neuron",
                                                  a full formatted reference, or a bare DOI)
  * references given on the command line with --ref

Verdict per entry:
  VERIFIED              a record matches on every field the entry gives (title ≥ 0.90 similar,
                        first-author surname, year ±1 for online-first vs print, venue)
  VERIFIED (no title)   matched on author + year (+ venue) only — CONFIRM the printed title is
                        the paper you mean before citing it
  MISMATCH(field,…)     a record exists but the entry gets these fields wrong — fix the entry
  NOT FOUND             no record matches — do not cite until a human finds the source

Every verdict prints the resolved DOI, title, first author, year and venue so you can read it.

Usage:
    python verify_refs.py refs.bib
    python verify_refs.py refs.txt
    python verify_refs.py --ref "Bernardi et al. 2020 Cell" --ref 10.1016/j.neuron.2018.07.003
    python verify_refs.py --demo                     # offline self-test, no network

Polite API use: set VERIFY_REFS_MAILTO=you@example.org (sent in the User-Agent, puts you in the
Crossref "polite pool"). No API keys. Requests time out after 20 s and are retried once.
"""
import argparse
import difflib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

CROSSREF = "https://api.crossref.org/works"
OPENALEX = "https://api.openalex.org/works"
TITLE_OK = 0.90          # SequenceMatcher ratio on normalized titles
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>{}]+)", re.I)
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")

FETCH = None             # replaced in --demo


# ── text helpers ──────────────────────────────────────────────────────────────
def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[{}\\]", "", s)
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).split()


def title_sim(a, b):
    return difflib.SequenceMatcher(None, " ".join(norm(a)), " ".join(norm(b))).ratio()


def venue_match(given, names):
    """Full name, containment, or abbreviation ("Nat Neurosci" ~ "Nature Neuroscience")."""
    g = [t for t in norm(given) if t not in ("the", "of", "and", "j")]
    if not g:
        return True
    for name in names:
        n = [t for t in norm(name) if t not in ("the", "of", "and")]
        if not n:
            continue
        if g == n or " ".join(g) in " ".join(n) or " ".join(n) in " ".join(g):
            return True
        i = 0                                   # each given token is a prefix of a later name token
        for t in g:
            while i < len(n) and not n[i].startswith(t):
                i += 1
            if i == len(n):
                break
            i += 1
        else:
            return True
    return False


# ── HTTP ──────────────────────────────────────────────────────────────────────
def _ua():
    mail = os.environ.get("VERIFY_REFS_MAILTO", "")
    return "verify_refs/0.1" + (f" (mailto:{mail})" if mail else "")


def fetch(url):
    if FETCH is not None:
        return FETCH(url)
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _ua()})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.5)
        except Exception:
            time.sleep(1.5)
    return None


# ── record normalization ──────────────────────────────────────────────────────
def from_crossref(it):
    au = it.get("author") or [{}]
    year = None
    for k in ("published-print", "published-online", "issued", "created"):
        dp = (it.get(k) or {}).get("date-parts") or [[None]]
        if dp[0] and dp[0][0]:
            year = int(dp[0][0]); break
    return {"doi": (it.get("DOI") or "").lower(), "title": (it.get("title") or [""])[0],
            "first_author": au[0].get("family") or au[0].get("name") or "",
            "year": year, "venues": (it.get("container-title") or []) + (it.get("short-container-title") or []),
            "source": "crossref"}


def from_openalex(w):
    au = w.get("authorships") or []
    name = au[0]["author"]["display_name"] if au else ""
    venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
    return {"doi": (w.get("doi") or "").replace("https://doi.org/", "").lower(),
            "title": w.get("title") or "", "first_author": name.split()[-1] if name else "",
            "year": w.get("publication_year"), "venues": [venue] if venue else [], "source": "openalex"}


def lookup_doi(doi):
    js = fetch(f"{CROSSREF}/{urllib.parse.quote(doi)}")
    if js and js.get("message"):
        return [from_crossref(js["message"])]
    js = fetch(f"{OPENALEX}/doi:{urllib.parse.quote(doi)}")
    return [from_openalex(js)] if js and js.get("id") else []


def search(query, rows=8):
    q = urllib.parse.quote(query)
    out = []
    js = fetch(f"{CROSSREF}?query.bibliographic={q}&rows={rows}")
    if js:
        out += [from_crossref(it) for it in js.get("message", {}).get("items", [])]
    js = fetch(f"{OPENALEX}?search={q}&per-page={rows}")
    if js:
        out += [from_openalex(w) for w in js.get("results", [])]
    return out


# ── parsing inputs ────────────────────────────────────────────────────────────
def parse_bib(text):
    entries = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", text, re.S):
        body = m.group(3)
        f = {k.lower(): re.sub(r"\s+", " ", v).strip() for k, v in
             re.findall(r"(\w+)\s*=\s*[{\"]((?:[^{}]|\{[^{}]*\})*)[}\"]", body)}
        authors = f.get("author", "")
        first = authors.split(" and ")[0]
        surname = first.split(",")[0] if "," in first else (first.split()[-1] if first.split() else "")
        entries.append({"key": m.group(2).strip(), "title": f.get("title", ""), "surname": surname,
                        "year": int(f["year"][:4]) if f.get("year", "")[:4].isdigit() else None,
                        "venue": f.get("journal") or f.get("booktitle") or "", "doi": f.get("doi", ""),
                        "raw": f.get("title", "") or m.group(2)})
    return entries


def parse_free(line):
    line = line.strip()
    doi = DOI_RE.search(line)
    if doi and len(line) - len(doi.group(1)) < 12:                  # a bare DOI
        return {"key": doi.group(1), "doi": doi.group(1).rstrip(".,;"), "title": "", "surname": "",
                "year": None, "venue": "", "raw": line}
    year = YEAR_RE.search(line)
    words = re.findall(r"[A-Z][A-Za-z'\-]+", line)
    return {"key": line[:50], "doi": doi.group(1).rstrip(".,;") if doi else "", "title": "",
            "surname": words[0] if words else "", "year": int(year.group(1)) if year else None,
            "venue": "", "raw": line}


# ── verdict ───────────────────────────────────────────────────────────────────
def compare(e, c):
    """Return list of mismatched fields of entry e against candidate record c."""
    bad = []
    if e["title"] and title_sim(e["title"], c["title"]) < TITLE_OK:
        bad.append("title")
    if e["surname"] and norm(e["surname"]) and norm(c["first_author"]) and \
            norm(e["surname"])[-1] != norm(c["first_author"])[-1]:
        bad.append("author")
    if e["year"] and c["year"] and abs(e["year"] - c["year"]) > 1:
        bad.append("year")
    if e["venue"] and c["venues"] and not venue_match(e["venue"], c["venues"]):
        bad.append("venue")
    return bad


def free_text_score(e, c):
    """For a free-text line: how well does the candidate explain it."""
    line = " ".join(norm(e["raw"]))
    tw = [t for t in norm(c["title"]) if len(t) > 3]
    title_cov = sum(t in line for t in tw) / len(tw) if tw else 0
    author_ok = bool(norm(c["first_author"])) and norm(c["first_author"])[-1] in line.split()
    year_ok = e["year"] is None or (c["year"] is not None and abs(e["year"] - c["year"]) <= 1)
    venue_ok = any(venue_match(v, [e["raw"]]) or " ".join(norm(v)) in line for v in c["venues"])
    return title_cov, author_ok, year_ok, venue_ok


def verify(e):
    if e["doi"]:
        recs = lookup_doi(e["doi"])
        if not recs:
            return "NOT FOUND", None, "DOI does not resolve"
        c = recs[0]
        if not (e["title"] or e["surname"] or e["year"] or e["venue"]):
            return "VERIFIED (no title)", c, "bare DOI — confirm the title"
        bad = compare(e, c) if (e["title"] or e["venue"]) else []
        if not e["title"] and not e["venue"]:
            ts, a, y, _ = free_text_score(e, c)
            bad = [f for f, ok in (("author", a or not e["surname"]), ("year", y)) if not ok]
        return ("VERIFIED" if not bad else f"MISMATCH({','.join(bad)})"), c, ""

    if e["title"]:                                              # structured entry (bib)
        q = " ".join(filter(None, [e["title"], e["surname"], str(e["year"] or "")]))
        cands = search(q)
        if not cands:
            return "NOT FOUND", None, "no search results"
        best = max(cands, key=lambda c: title_sim(e["title"], c["title"]))
        if title_sim(e["title"], best["title"]) < 0.6:
            return "NOT FOUND", best, "closest record has a different title"
        bad = compare(e, best)
        return ("VERIFIED" if not bad else f"MISMATCH({','.join(bad)})"), best, ""

    cands = search(e["raw"])                                    # free text
    scored = []
    for c in cands:
        ts, a, y, v = free_text_score(e, c)
        scored.append((ts >= 0.8 and a and y, a and y and v, ts, c))
    full = [s for s in scored if s[0]]
    if full:
        return "VERIFIED", max(full, key=lambda s: s[2])[3], ""
    weak = [s for s in scored if s[1]]
    if weak:
        return "VERIFIED (no title)", weak[0][3], "matched author+year+venue — confirm the title"
    partial = [s for s in scored if s[2] >= 0.8]
    if partial:
        _, c = None, partial[0][3]
        ts, a, y, v = free_text_score(e, c)
        bad = [f for f, ok in (("author", a), ("year", y)) if not ok]
        return f"MISMATCH({','.join(bad) or 'venue'})", c, ""
    return "NOT FOUND", None, "no record explains this reference"


def report(entries):
    counts = {}
    for e in entries:
        status, c, note = verify(e)
        key = status.split("(")[0].strip() if not status.startswith("VERIFIED (") else "VERIFIED (no title)"
        counts[key] = counts.get(key, 0) + 1
        print(f"{status:<22} {e['key'][:60]}")
        if c:
            print(f"    → {c['first_author']} {c['year']} · {c['title'][:90]} · "
                  f"{(c['venues'] or ['?'])[0]} · doi:{c['doi'] or '—'}")
        if note:
            print(f"    ({note})")
    print("SUMMARY: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())) + f" of {len(entries)}")
    return counts


# ── offline demo ──────────────────────────────────────────────────────────────
def _demo():
    global FETCH
    rec = {"DOI": "10.1016/j.neuron.2018.07.003",
           "title": ["Linking Connectivity, Dynamics, and Computations in Low-Rank Recurrent Neural Networks"],
           "author": [{"family": "Mastrogiuseppe"}, {"family": "Ostojic"}],
           "issued": {"date-parts": [[2018, 8]]}, "container-title": ["Neuron"]}

    def fake(url):
        if "10.1016%2Fj.neuron.2018.07.003" in url or "10.1016/j.neuron.2018.07.003" in url:
            return {"message": rec}
        if "query.bibliographic" in url:
            return {"message": {"items": [rec] if "Mastrogiuseppe" in urllib.parse.unquote(url)
                                or "Low-Rank" in urllib.parse.unquote(url) else []}}
        if "openalex" in url:
            return {"results": []}
        return None
    FETCH = fake
    bib = """@article{mo18,
  title = {Linking Connectivity, Dynamics, and Computations in Low-Rank Recurrent Neural Networks},
  author = {Mastrogiuseppe, Francesca and Ostojic, Srdjan},
  journal = {Neuron}, year = {2018}, doi = {10.1016/j.neuron.2018.07.003}
}
@article{wrongyear,
  title = {Linking Connectivity, Dynamics, and Computations in Low-Rank Recurrent Neural Networks},
  author = {Mastrogiuseppe, Francesca}, journal = {Neuron}, year = {2015}
}
"""
    entries = parse_bib(bib) + [parse_free("Mastrogiuseppe & Ostojic 2018 Neuron"),
                                parse_free("Smithson & Quark 2019 Neuron, Ring attractors in mouse cerebellum")]
    counts = report(entries)
    assert counts.get("VERIFIED") == 1 and counts.get("MISMATCH") == 1, counts
    assert counts.get("VERIFIED (no title)") == 1 and counts.get("NOT FOUND") == 1, counts
    print("demo OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help=".bib file, or text file with one reference per line")
    ap.add_argument("--ref", action="append", default=[], help="a reference or DOI (repeatable)")
    ap.add_argument("--demo", action="store_true", help="offline self-test with canned responses")
    args = ap.parse_args()
    if args.demo:
        return _demo()
    entries = []
    if args.path:
        text = open(args.path).read()
        if args.path.endswith(".bib") or text.lstrip().startswith("@"):
            entries += parse_bib(text)
        else:
            entries += [parse_free(l) for l in text.splitlines() if l.strip() and not l.startswith("#")]
    entries += [parse_free(r) for r in args.ref]
    if not entries:
        ap.print_help(); sys.exit(2)
    counts = report(entries)
    sys.exit(0 if set(counts) <= {"VERIFIED"} else 1)


if __name__ == "__main__":
    main()
