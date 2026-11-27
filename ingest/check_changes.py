"""Detect programme pages that changed since the last snapshot (feature F10).

  python ingest/crawl.py && python ingest/parse.py      # make a new snapshot first
  python ingest/check_changes.py                         # compare it with the stored hashes

For every programme in data/programmes/programmes.jsonl the script hashes the parsed text and
compares it with data/programmes/text_hashes.json (written by the previous run). It writes
data/programmes/changes.json:

  {"checked_at": "...", "changed": [...], "new": [...], "removed": [...], "unchanged": N}

and updates text_hashes.json. Changed and new programmes must have their criteria re-extracted
and approved by the curator before the new criteria replace the old ones; the app shows a
"criteria changed, under review" badge for programmes in "changed". Whitespace-only changes are
ignored. The first run only records hashes.

For a demo without waiting for a real page update:

  python ingest/check_changes.py --simulate-change sh-call      # marks one programme as changed
  python ingest/check_changes.py --clear-simulated              # removes simulated entries

Simulated entries carry "simulated": true and leave text_hashes.json untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGS = ROOT / "data/programmes/programmes.jsonl"
HASHES = ROOT / "data/programmes/text_hashes.json"
CHANGES = ROOT / "data/programmes/changes.json"


def text_hash(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().lower().encode("utf-8")).hexdigest()


def simulate(pid: str | None, clear: bool):
    report = json.loads(CHANGES.read_text(encoding="utf-8")) if CHANGES.exists() else \
        {"checked_at": None, "first_run": False, "changed": [], "new": [], "removed": [], "unchanged": 0}
    report["changed"] = [c for c in report.get("changed", []) if not c.get("simulated")]
    if pid and not clear:
        ids = {json.loads(l)["programme_id"] for l in PROGS.read_text(encoding="utf-8").splitlines() if l.strip()}
        if pid not in ids:
            raise SystemExit(f"unknown programme id: {pid}")
        today = datetime.now().date().isoformat()
        report["changed"].append({"programme_id": pid, "old_snapshot": "", "new_snapshot": today, "simulated": True})
        print(f"simulated a change for {pid} (dated {today})")
    else:
        print("removed simulated changes")
    CHANGES.write_text(json.dumps(report, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--simulate-change", metavar="PROGRAMME_ID", help="demo only: mark a programme as changed")
    ap.add_argument("--clear-simulated", action="store_true", help="remove simulated changes")
    args = ap.parse_args()
    if args.simulate_change or args.clear_simulated:
        return simulate(args.simulate_change, args.clear_simulated)
    progs = [json.loads(l) for l in PROGS.read_text(encoding="utf-8").splitlines() if l.strip()]
    now = {p["programme_id"]: {"hash": text_hash(p.get("text", "")), "snapshot_date": str(p.get("snapshot_date") or "")}
           for p in progs}
    before = json.loads(HASHES.read_text(encoding="utf-8")) if HASHES.exists() else {}
    first_run = not before
    changed = sorted(pid for pid in now if pid in before and before[pid]["hash"] != now[pid]["hash"])
    new = [] if first_run else sorted(pid for pid in now if pid not in before)
    removed = sorted(pid for pid in before if pid not in now)
    report = {"checked_at": datetime.now().isoformat(timespec="seconds"), "first_run": first_run,
              "changed": [{"programme_id": pid, "old_snapshot": before[pid]["snapshot_date"],
                           "new_snapshot": now[pid]["snapshot_date"]} for pid in changed],
              "new": new, "removed": removed, "unchanged": len(now) - len(changed) - len(new)}
    CHANGES.write_text(json.dumps(report, indent=1), encoding="utf-8")
    HASHES.write_text(json.dumps(now, indent=1), encoding="utf-8")
    if first_run:
        print(f"first run: recorded hashes for {len(now)} programmes")
    else:
        print(f"changed: {len(changed)}  new: {len(new)}  removed: {len(removed)}  unchanged: {report['unchanged']}")
        for pid in changed + new:
            print("  re-extract and review:", pid)
    print("wrote", CHANGES)


if __name__ == "__main__":
    main()
