"""Second crawl pass for pages that need JavaScript or failed the first time.

  pip install playwright
  python -m playwright install chromium
  python ingest/crawl_rendered.py --snapshot 2026-11-21

It opens each page in a headless Chromium browser, waits until the page has loaded,
and saves the rendered HTML into the same dated snapshot. Same rules as crawl.py:
robots.txt is respected, 10 seconds between requests, families without
terms_checked are skipped. By default it only fetches pages that are missing from
the snapshot or came out (almost) empty; use --all to re-fetch everything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from crawl import UA, allowed  # noqa: E402
from parse import html_to_text, pdf_to_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DELAY_S = 10.0


def needs_fetch(snap: Path, pid: str) -> bool:
    files = [p for p in snap.glob(f"{pid}.*") if p.suffix in (".html", ".pdf")]
    if not files:
        return True
    f = files[0]
    try:
        text = pdf_to_text(f) if f.suffix == ".pdf" else html_to_text(f.read_bytes())
    except Exception:
        return True
    return len(text.split()) < 80


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", default=date.today().isoformat())
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    cfg = yaml.safe_load((ROOT / "data" / "sources.yaml").read_text(encoding="utf-8"))["families"]
    snap = ROOT / "data" / "snapshots" / args.snapshot
    snap.mkdir(parents=True, exist_ok=True)
    manual = ROOT / "data" / "programmes" / "manual"
    todo = []
    for fam, info in cfg.items():
        if not info.get("terms_checked"):
            continue
        for p in info.get("programmes") or []:
            if (manual / f"{p['id']}.md").exists():
                continue                      # a hand-copied version exists; keep it
            if args.all or needs_fetch(snap, p["id"]):
                todo.append((fam, p))
    print(f"{len(todo)} pages to fetch with a rendering browser")

    with sync_playwright() as pw, (snap / "manifest.jsonl").open("a", encoding="utf-8") as mf:
        browser = pw.chromium.launch()
        page = browser.new_page(user_agent=UA)
        for fam, p in todo:
            url = p["url"]
            rec = {"id": p["id"], "family": fam, "name": p.get("name"), "url": url, "renderer": "playwright"}
            if not allowed(url):
                rec["status"] = "robots_disallowed"
                print(f"[robots] {p['id']}: copy this page by hand")
            elif url.lower().split("?")[0].endswith(".pdf"):
                try:
                    r = page.request.get(url, timeout=60000)
                    if r.ok:
                        (snap / f"{p['id']}.pdf").write_bytes(r.body())
                        rec.update(status=r.status, file=f"{p['id']}.pdf", sha256=hashlib.sha256(r.body()).hexdigest())
                    else:
                        rec["status"] = r.status
                    print(f"[{r.status}] {p['id']} (pdf)")
                except Exception as e:
                    rec["status"] = f"error: {e}"[:200]
                    print(f"[error] {p['id']}: {e}")
            else:
                try:
                    resp = page.goto(url, wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(2000)
                    html = page.content().encode("utf-8")
                    (snap / f"{p['id']}.html").write_bytes(html)
                    words = len(html_to_text(html).split())
                    rec.update(status=resp.status if resp else "no-response", file=f"{p['id']}.html",
                               sha256=hashlib.sha256(html).hexdigest(), words=words)
                    print(f"[{rec['status']}] {p['id']}: {words} words" + ("  <- still empty, copy by hand" if words < 80 else ""))
                except Exception as e:
                    rec["status"] = f"error: {e}"[:200]
                    print(f"[error] {p['id']}: {e}")
            mf.write(json.dumps(rec) + "\n")
            time.sleep(DELAY_S)
        browser.close()
    print("done -> now run: python ingest/parse.py --snapshot", args.snapshot)


if __name__ == "__main__":
    main()
