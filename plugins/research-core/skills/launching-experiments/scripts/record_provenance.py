"""Write provenance.json into a run directory: everything needed to know what produced a result.

Records: git commit, branch, dirty flag + `git diff --stat` (and the full diff to
provenance.diff when dirty), argv, timestamp, host, user-visible GPU(s), Python / torch / numpy
versions, optional config dict and seed; with --card, a frozen copy of the run's pre-run card
(planning-research Step 1) from the verdict log, as precard.md + its sha256, so the verdict quotes
what was fixed before the data even if the log is edited later.

Run it as a command from the launch script, once per run, before training starts (do not import it
from the skill folder: plugin install paths change with every version):
    python record_provenance.py --run_dir results/my_sweep/s0_arm --repo . --seed 0 --config results/my_sweep/s0_arm/config.json
    python record_provenance.py --run_dir ... --card docs/verdicts.md --card_heading "delay pin at weight 0.2"
    python record_provenance.py --demo
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import socket
import subprocess
import sys
import tempfile


def _git(repo, *args):
    try:
        return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):        # no git, or a hung repo: record it as unknown
        return ""


def _commit(repo):
    h = _git(repo, "rev-parse", "--verify", "-q", "HEAD")
    return h if re.fullmatch(r"[0-9a-f]{40}", h) else None      # None: not a repo or no commits yet


def _versions():
    out = {"python": platform.python_version()}
    for mod in ("torch", "numpy", "scipy", "jax"):
        try:
            out[mod] = __import__(mod).__version__
        except (ImportError, AttributeError):
            out[mod] = None                             # not installed in this environment
    return out


def _gpus():
    try:
        import torch
        if torch.cuda.is_available():
            return [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    except (ImportError, RuntimeError):                 # no torch, or CUDA not usable here
        pass
    return []


def extract_card(path, heading):
    """The section of a Markdown log whose '## ' heading contains `heading` (up to the next '## '); error if not 1 match."""
    sections = re.split(r"(?m)^(?=## )", open(path).read())
    hits = [sec for sec in sections if sec.startswith("## ") and heading in sec.splitlines()[0]]
    if len(hits) != 1:
        raise SystemExit(f"--card_heading {heading!r}: {len(hits)} matching headings in {path}, need exactly 1")
    return hits[0].rstrip() + "\n"


def freeze_card(run_dir, path, heading):
    """Write <run_dir>/precard.md and return its record for provenance.json."""
    text = extract_card(path, heading)
    with open(os.path.join(run_dir, "precard.md"), "w") as f:
        f.write(text)
    return {"source": os.path.abspath(path), "heading": text.splitlines()[0],
            "sha256": hashlib.sha256(text.encode()).hexdigest()}


def record_provenance(run_dir, repo=".", config=None, seed=None, extra=None):
    """Write <run_dir>/provenance.json (+ provenance.diff when the tree is dirty). Returns the dict."""
    os.makedirs(run_dir, exist_ok=True)
    repo = os.path.abspath(repo)
    status = _git(repo, "status", "--porcelain", "--untracked-files=no")
    prov = {
        "timestamp": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "argv": sys.argv,
        "cwd": os.getcwd(),
        "git": {
            "repo": repo,
            "commit": _commit(repo),
            "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD") or None,
            "dirty": bool(status),
            "diff_stat": _git(repo, "diff", "--stat", "HEAD") if status else "",
        },
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "gpus": _gpus(),
        "versions": _versions(),
        "seed": seed,
        "config": config,
    }
    if extra:
        prov.update(extra)
    if status:
        with open(os.path.join(run_dir, "provenance.diff"), "w") as f:
            f.write(_git(repo, "diff", "HEAD"))
    with open(os.path.join(run_dir, "provenance.json"), "w") as f:
        json.dump(prov, f, indent=2, default=str)
    return prov


def _demo():
    with tempfile.TemporaryDirectory() as d:
        p = record_provenance(d, repo=os.path.dirname(os.path.abspath(__file__)),
                              config={"lr": 0.01, "n_epochs": 10}, seed=0)
        back = json.load(open(os.path.join(d, "provenance.json")))
        assert back["seed"] == 0 and back["config"]["lr"] == 0.01 and "python" in back["versions"]
        log = os.path.join(d, "verdicts.md")
        open(log, "w").write("## 2026-10-29 · pin at 0.2 — RUNNING\nWHY x\n\n## 2026-10-28 · older\nWHY y\n")
        card = freeze_card(d, log, "pin at 0.2")
        assert open(os.path.join(d, "precard.md")).read() == "## 2026-10-29 · pin at 0.2 — RUNNING\nWHY x\n"
        assert len(card["sha256"]) == 64
        print(f"commit {p['git']['commit']}  dirty={p['git']['dirty']}  host={p['host']}  "
              f"gpus={p['gpus'] or 'none'}  versions={p['versions']}")
        print("SUMMARY: demo OK — provenance.json written and read back; pre-run card frozen")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run_dir", help="run directory to write provenance.json into")
    ap.add_argument("--repo", default=".", help="git repository of the code that runs")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--config", default=None, help="JSON file with the run's config (e.g. <run_dir>/config.json)")
    ap.add_argument("--card", default=None, help="verdict log holding the run's pre-run card (e.g. docs/verdicts.md)")
    ap.add_argument("--card_heading", default=None, help="text in the card's '## ' heading (must match exactly one)")
    ap.add_argument("--demo", action="store_true", help="write and read back a provenance file in a temp dir")
    args = ap.parse_args()
    if args.demo:
        _demo()
    elif args.run_dir:
        cfg = json.load(open(args.config)) if args.config else None
        os.makedirs(args.run_dir, exist_ok=True)
        card = freeze_card(args.run_dir, args.card, args.card_heading) if args.card else None
        p = record_provenance(args.run_dir, repo=args.repo, config=cfg, seed=args.seed,
                              extra={"precard": card} if card else None)
        print(f"wrote {os.path.join(args.run_dir, 'provenance.json')}  commit {p['git']['commit']}  dirty={p['git']['dirty']}")
    else:
        ap.print_help()
