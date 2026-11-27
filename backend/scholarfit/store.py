"""Storage for the product (SQLite file; the same tables map to PostgreSQL + pgvector in
Assignment 4). Holds programmes, their extracted criteria with review status, checks
(audit log) and the student's calendar token."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .config import DATA
from .schemas import Criterion, Handling, Programme

DB_PATH = Path(os.environ.get("SCHOLARFIT_DB", DATA / "scholarfit.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS programmes (programme_id TEXT PRIMARY KEY, family TEXT, name TEXT, url TEXT,
  snapshot_date TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS criteria (criterion_id TEXT PRIMARY KEY, programme_id TEXT, body TEXT,
  status TEXT, model TEXT, reviewed_by TEXT, updated REAL);
CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, programme_id TEXT,
  overall TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS tokens (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS saved (profile_id TEXT, programme_id TEXT, saved_at REAL,
  last_overall TEXT, last_checked REAL, prev_overall TEXT, changed_at REAL, last_row TEXT,
  PRIMARY KEY (profile_id, programme_id));
"""


def _migrate(con: sqlite3.Connection):
    """Columns added after the first release (databases built earlier lack them)."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(checks)")}
    if "profile_id" not in cols:
        con.execute("ALTER TABLE checks ADD COLUMN profile_id TEXT")


@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _migrate(con)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def upsert_programme(p: Programme):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO programmes VALUES (?,?,?,?,?,?)",
                  (p.programme_id, p.family, p.name, p.url, str(p.snapshot_date or ""), p.text))


def save_criteria(pid: str, crits: list[Criterion], model: str):
    with db() as c:
        c.execute("DELETE FROM criteria WHERE programme_id=?", (pid,))
        for cr in crits:
            needs_review = cr.handling == Handling.MANUAL or (cr.confidence or 0) < 1.0
            c.execute("INSERT INTO criteria VALUES (?,?,?,?,?,?,?)",
                      (cr.criterion_id, pid, cr.model_dump_json(), "needs_review" if needs_review else "published",
                       model, None, time.time()))


def list_programmes() -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT programme_id, family, name, url, snapshot_date FROM programmes ORDER BY family, name").fetchall()
        counts = dict(c.execute("SELECT programme_id, COUNT(*) FROM criteria GROUP BY programme_id").fetchall())
    return [{**dict(r), "n_criteria": counts.get(r["programme_id"], 0)} for r in rows]


def get_programme(pid: str) -> Programme | None:
    with db() as c:
        r = c.execute("SELECT * FROM programmes WHERE programme_id=?", (pid,)).fetchone()
    if not r:
        return None
    return Programme(programme_id=r["programme_id"], family=r["family"], name=r["name"], url=r["url"],
                     snapshot_date=r["snapshot_date"] or None, text=r["text"], criteria=get_criteria(pid))


def get_criteria(pid: str, include_pending: bool = True) -> list[Criterion]:
    with db() as c:
        q = "SELECT body, status FROM criteria WHERE programme_id=?"
        rows = c.execute(q, (pid,)).fetchall()
    return [Criterion.model_validate_json(r["body"]) for r in rows if include_pending or r["status"] == "published"]


def pending_criteria() -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT criterion_id, programme_id, body, model FROM criteria WHERE status='needs_review'").fetchall()
    return [{"criterion_id": r["criterion_id"], "programme_id": r["programme_id"], "model": r["model"],
             "criterion": json.loads(r["body"])} for r in rows]


def review_criterion(cid: str, reviewer: str, approve: bool, body: Criterion | None = None):
    with db() as c:
        if body is not None:
            c.execute("UPDATE criteria SET body=? WHERE criterion_id=?", (body.model_dump_json(), cid))
        c.execute("UPDATE criteria SET status=?, reviewed_by=?, updated=? WHERE criterion_id=?",
                  ("published" if approve else "rejected", reviewer, time.time(), cid))


def log_check(pid: str, overall: str, result_json: str, profile_id: str | None = None):
    with db() as c:
        c.execute("INSERT INTO checks (ts, programme_id, overall, result, profile_id) VALUES (?,?,?,?,?)",
                  (time.time(), pid, overall, result_json, profile_id))


def check_history(profile_id: str, limit: int = 100) -> list[dict]:
    """Past checks of one student, newest first (the dashboard's table of past checks)."""
    with db() as c:
        rows = c.execute("SELECT ch.ts, ch.programme_id, ch.overall, p.name FROM checks ch "
                         "LEFT JOIN programmes p ON p.programme_id = ch.programme_id "
                         "WHERE ch.profile_id=? ORDER BY ch.ts DESC LIMIT ?", (profile_id, limit)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- saved programmes (dashboard, F9)
def _saved_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["last_row"] = json.loads(d["last_row"]) if d.get("last_row") else None
    return d


def save_programme(profile_id: str, pid: str, overall: str | None, row: dict | None):
    now = time.time()
    with db() as c:
        old = c.execute("SELECT saved_at FROM saved WHERE profile_id=? AND programme_id=?", (profile_id, pid)).fetchone()
        c.execute("INSERT OR REPLACE INTO saved (profile_id, programme_id, saved_at, last_overall, last_checked, "
                  "prev_overall, changed_at, last_row) VALUES (?,?,?,?,?,?,?,?)",
                  (profile_id, pid, old["saved_at"] if old else now, overall, now if overall else None, None, None,
                   json.dumps(row) if row is not None else None))


def list_saved(profile_id: str) -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT * FROM saved WHERE profile_id=? ORDER BY saved_at DESC", (profile_id,)).fetchall()
    return [_saved_dict(r) for r in rows]


def delete_saved(profile_id: str, pid: str) -> bool:
    with db() as c:
        n = c.execute("DELETE FROM saved WHERE profile_id=? AND programme_id=?", (profile_id, pid)).rowcount
    return n > 0


def update_saved_status(profile_id: str, pid: str, overall: str, row: dict) -> dict | None:
    """After a new check of a saved programme: store the new verdict and report a change.
    Returns {"from": old, "to": new} when the overall verdict differs from last_overall."""
    now = time.time()
    with db() as c:
        old = c.execute("SELECT last_overall FROM saved WHERE profile_id=? AND programme_id=?",
                        (profile_id, pid)).fetchone()
        if old is None:
            return None
        before = old["last_overall"]
        changed = before is not None and before != overall
        if changed:
            c.execute("UPDATE saved SET prev_overall=?, changed_at=?, last_overall=?, last_checked=?, last_row=? "
                      "WHERE profile_id=? AND programme_id=?", (before, now, overall, now, json.dumps(row), profile_id, pid))
        else:
            c.execute("UPDATE saved SET last_overall=?, last_checked=?, last_row=? WHERE profile_id=? AND programme_id=?",
                      (overall, now, json.dumps(row), profile_id, pid))
    return {"from": before, "to": overall} if changed else None


def set_token(k: str, v: str):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO tokens VALUES (?,?)", (k, v))


def get_token(k: str) -> str | None:
    with db() as c:
        r = c.execute("SELECT v FROM tokens WHERE k=?", (k,)).fetchone()
    return r["v"] if r else None
