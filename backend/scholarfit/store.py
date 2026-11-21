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
"""


@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
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


def log_check(pid: str, overall: str, result_json: str):
    with db() as c:
        c.execute("INSERT INTO checks (ts, programme_id, overall, result) VALUES (?,?,?,?)",
                  (time.time(), pid, overall, result_json))


def set_token(k: str, v: str):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO tokens VALUES (?,?)", (k, v))


def get_token(k: str) -> str | None:
    with db() as c:
        r = c.execute("SELECT v FROM tokens WHERE k=?", (k,)).fetchone()
    return r["v"] if r else None
