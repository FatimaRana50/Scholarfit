"""Make readable pages for labelling.

  python scripts/labelling_pack.py

Writes data/labels/pack/pairs_001-050.html, pairs_051-100.html, pairs_101-150.html
(one per annotator: programme text on the left, the student's profile on the right)
and data/labels/pack/programmes/<id>.txt for checking CriteriaGold rows.
Labels still go into data/labels/pairs.csv and data/labels/criteria_checked.csv.
"""
from __future__ import annotations

import csv
import html
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "labels" / "pack"


def age_on(dob: str | None, ref: date):
    if not dob:
        return "not stated"
    d = date.fromisoformat(dob)
    return ref.year - d.year - ((ref.month, ref.day) < (d.month, d.day))


def profile_html(p: dict, ref: date) -> str:
    rows = [("Date of birth", p.get("date_of_birth") or "not stated"),
            (f"Age on {ref}", age_on(p.get("date_of_birth"), ref)),
            ("Nationality", p.get("nationality") or "not stated"),
            ("Work experience", f"{p.get('work_experience_months', 'not stated')} months"),
            ("Bachelor taught in English (certificate)", {True: "yes", False: "no"}.get(p.get("english_medium_instruction"), "not stated"))]
    for t in p.get("english_tests", []):
        rows.append((t["test"], f"overall {t['overall']}" + (f", lowest band {t['min_band']}" if t.get("min_band") else "")))
    if not p.get("english_tests"):
        rows.append(("English test", "none"))
    out = "<table>" + "".join(f"<tr><th>{html.escape(str(a))}</th><td>{html.escape(str(b))}</td></tr>" for a, b in rows) + "</table>"
    out += "<h4>Degrees</h4><table><tr><th>Level</th><th>Field</th><th>Years</th><th>Completed</th><th>Grade</th><th>Min pass</th></tr>"
    for d in p.get("degrees", []):
        grade = "" if d.get("grade_value") is None else f"{d['grade_value']} ({d.get('grade_scale')}, max {d.get('grade_scale_max')})"
        out += (f"<tr><td>{d['level']}</td><td>{html.escape(str(d.get('field') or ''))}</td><td>{d.get('duration_years', '')}</td>"
                f"<td>{d.get('completed')}</td><td>{grade}</td><td>{d.get('grade_scale_min_pass') or 'not stated'}</td></tr>")
    return out + "</table>"


CSS = """body{font-family:system-ui,sans-serif;margin:20px;color:#1d2433}h2{margin-top:40px;border-top:3px solid #1d2433;padding-top:12px}
.wrap{display:grid;grid-template-columns:1.3fr 1fr;gap:20px}.prog{white-space:pre-wrap;background:#f6f7f9;border:1px solid #ddd;
padding:12px;max-height:520px;overflow:auto;font-size:13px}table{border-collapse:collapse;font-size:13px;margin-bottom:8px}
th,td{border:1px solid #ddd;padding:4px 8px;text-align:left}th{background:#f0f2f5}.meta{color:#5b6475;font-size:13px}"""


def main():
    progs = {json.loads(l)["programme_id"]: json.loads(l)
             for l in (ROOT / "data/programmes/programmes.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    pairs = list(csv.DictReader((ROOT / "data/labels/pairs.csv").open(encoding="utf-8")))
    prof_dir = ROOT / "data/profiles/synthetic"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "programmes").mkdir(exist_ok=True)
    for pid, p in progs.items():
        (OUT / "programmes" / f"{pid}.txt").write_text(f"{p['name']}\n{p.get('url')}\n\n{p['text']}", encoding="utf-8")
    for start in range(0, len(pairs), 50):
        chunk = pairs[start:start + 50]
        parts = [f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>",
                 f"<h1>Pairs {start + 1}-{start + len(chunk)}</h1><p class='meta'>Label in data/labels/pairs.csv following "
                 "data/guidelines/labelling_guideline.md. Use only this programme text and this profile.</p>"]
        for r in chunk:
            p = progs[r["programme_id"]]
            prof = json.loads((prof_dir / f"{r['profile_id']}.json").read_text(encoding="utf-8"))
            ref = date.fromisoformat(str(p.get("snapshot_date") or date.today()))
            parts.append(f"<h2>{r['pair_id']} ({r['split']})</h2><p class='meta'>{html.escape(p['name'])} &middot; "
                         f"family {r['family']} &middot; profile {r['profile_id']} &middot; "
                         f"<a href='{html.escape(str(p.get('url')))}'>source</a></p><div class='wrap'>"
                         f"<div class='prog'>{html.escape(p['text'])}</div><div>{profile_html(prof, ref)}</div></div>")
        parts.append("</body></html>")
        name = f"pairs_{start + 1:03d}-{start + len(chunk):03d}.html"
        (OUT / name).write_text("\n".join(parts), encoding="utf-8")
        print("wrote", OUT / name)
    print(f"programme texts for checking criteria: {OUT / 'programmes'}")


if __name__ == "__main__":
    main()
