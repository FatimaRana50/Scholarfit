"""Turn a snapshot into data/programmes/programmes.jsonl (one Programme per line).

  python ingest/parse.py --snapshot 2026-11-21

HTML: scripts, navigation, headers and footers are removed; headings become "# ..."
lines so retrieval can split the call into sections. PDF: text per page via pdfplumber
(scanned PDFs need OCR - list them in data/snapshots/<date>/needs_ocr.txt).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def html_to_text(raw: bytes) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    # NOTE: <form> is NOT removed: SharePoint sites (HEC) wrap the whole page in one form.
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "aside", "svg", "button"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    lines = []
    for el in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th"]):
        txt = " ".join(el.get_text(" ", strip=True).split())
        if not txt:
            continue
        if el.name in ("h1", "h2", "h3", "h4"):
            lines.append("\n# " + txt)
        elif el.name == "li":
            lines.append("- " + txt)
        else:
            lines.append(txt)
    text = "\n".join(lines)
    if len(text.split()) < 50:
        # pages that put their text in <div>/<span>/<br> instead of <p>/<li>: take all visible text
        raw = main.get_text("\n", strip=True)
        text = "\n".join(l for l in raw.splitlines() if len(l.split()) > 1 or l.endswith(":"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def pdf_to_text(path: Path) -> str:
    out = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            t = page.extract_text() or ""
            out.append(f"\n# Page {i}\n{t}")
    return "\n".join(out).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    args = ap.parse_args()
    snap = ROOT / "data" / "snapshots" / args.snapshot
    mpath = snap / "manifest.jsonl"
    manifest = [json.loads(l) for l in mpath.read_text(encoding="utf-8").splitlines() if l.strip()] if mpath.exists() else []
    # keep the LAST successful record per page (a rendered re-crawl replaces the first attempt)
    latest = {}
    for rec in manifest:
        if rec.get("file"):
            latest[rec["id"]] = rec
    manifest = list(latest.values())
    manual_ids = {p.stem for p in (ROOT / "data" / "programmes" / "manual").glob("*.md")}
    out_path = ROOT / "data" / "programmes" / "programmes.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    needs_ocr, n = [], 0
    with out_path.open("w", encoding="utf-8") as f:
        # Pages that block crawlers (JavaScript sites, Cloudflare) can be saved by hand as
        # data/programmes/manual/<id>.md with a YAML header: id, family, name, url, snapshot_date.
        for md in sorted((ROOT / "data" / "programmes" / "manual").glob("*.md")):
            raw = md.read_text(encoding="utf-8")
            if raw.startswith("---"):
                _, head, body = raw.split("---", 2)
                import yaml
                meta = yaml.safe_load(head)
                prog = {"programme_id": meta["id"], "family": meta["family"], "name": meta.get("name", meta["id"]),
                        "url": meta.get("url"), "snapshot_date": str(meta.get("snapshot_date", args.snapshot)),
                        "text": body.strip()}
                f.write(json.dumps(prog, ensure_ascii=False) + "\n")
                n += 1
        for rec in manifest:
            if not rec.get("file") or rec["id"] in manual_ids or str(rec.get("status")) in ("403", "404"):
                continue
            path = snap / rec["file"]
            text = pdf_to_text(path) if path.suffix == ".pdf" else html_to_text(path.read_bytes())
            if len(text.split()) < 50:
                needs_ocr.append(rec["file"])
                continue          # too little text to use: kept out of programmes.jsonl
            prog = {"programme_id": rec["id"], "family": rec["family"], "name": rec.get("name") or rec["id"],
                    "url": rec["url"], "snapshot_date": args.snapshot, "text": text}
            f.write(json.dumps(prog, ensure_ascii=False) + "\n")
            n += 1
    if needs_ocr:
        (snap / "needs_ocr.txt").write_text("\n".join(needs_ocr), encoding="utf-8")
    print(f"wrote {n} programmes to {out_path}; {len(needs_ocr)} need OCR or manual text")


if __name__ == "__main__":
    main()
