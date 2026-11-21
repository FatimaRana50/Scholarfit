"""Download programme pages into a dated snapshot.

  python ingest/crawl.py                       # all programmes in data/sources.yaml
  python ingest/crawl.py --family daad         # one family

Respects robots.txt, waits between requests, skips families whose terms have not been
checked (fill `terms_checked` in sources.yaml), and never re-downloads a file that is
already in today's snapshot. Output: data/snapshots/<YYYY-MM-DD>/<programme_id>.(html|pdf)
plus manifest.jsonl with URL, status and hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
UA = "ScholarFit-research-crawler/0.1 (FAST-NUCES student project; contact in README)"
DELAY_S = 10.0
_robots: dict[str, RobotFileParser] = {}


def allowed(url: str) -> bool:
    base = "{0.scheme}://{0.netloc}".format(urlparse(url))
    if base not in _robots:
        rp = RobotFileParser(base + "/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None
        _robots[base] = rp
    rp = _robots[base]
    return True if rp is None else rp.can_fetch(UA, url)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--family")
    ap.add_argument("--snapshot", default=date.today().isoformat())
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "data" / "sources.yaml").read_text(encoding="utf-8"))["families"]
    out_dir = ROOT / "data" / "snapshots" / args.snapshot
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = out_dir / "manifest.jsonl"

    for fam, info in cfg.items():
        if args.family and fam != args.family:
            continue
        progs = info.get("programmes") or []
        if progs and not info.get("terms_checked"):
            print(f"[skip] {fam}: fill terms_checked in sources.yaml first")
            continue
        for p in progs:
            url = p["url"]
            ext = ".pdf" if url.lower().split("?")[0].endswith(".pdf") else ".html"
            path = out_dir / f"{p['id']}{ext}"
            if path.exists():
                continue
            if not allowed(url):
                print(f"[robots] disallowed: {url}")
                rec = {"id": p["id"], "family": fam, "url": url, "status": "robots_disallowed"}
            else:
                try:
                    r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
                    if r.ok and "pdf" in r.headers.get("content-type", "") and ext == ".html":
                        path = path.with_suffix(".pdf")
                    if r.ok:
                        path.write_bytes(r.content)
                    rec = {"id": p["id"], "family": fam, "name": p.get("name"), "url": url,
                           "status": r.status_code, "file": path.name if r.ok else None,
                           "sha256": hashlib.sha256(r.content).hexdigest() if r.ok else None}
                    print(f"[{r.status_code}] {p['id']}")
                except requests.RequestException as e:
                    rec = {"id": p["id"], "family": fam, "url": url, "status": f"error: {e}"}
                time.sleep(DELAY_S)
            with manifest.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    main()
