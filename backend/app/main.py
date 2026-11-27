"""ScholarFit API.  Run:  uvicorn app.main:app --reload --port 8000  (from backend/)"""
from __future__ import annotations

import hmac
import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from scholarfit import ranking, store
from scholarfit.breakdown import breakdown
from scholarfit.config import DATA, default_model
from scholarfit.integrations import gcal
from scholarfit.llm.client import LLMError
from scholarfit.pipelines.cv import extract_profile_llm, read_cv_text
from scholarfit.pipelines.systems import make_judge
from scholarfit.rules.engine import evaluate, missing_requirements
from scholarfit.schemas import CriterionType, Label, Profile

app = FastAPI(title="ScholarFit API", version="0.4")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
                   allow_methods=["*"], allow_headers=["*"])
MAX_CV_BYTES = 5 * 1024 * 1024
CHANGES_FILE = DATA / "programmes" / "changes.json"
NO_JUDGE = "Needs a semantic judgement; no judge configured."


@app.get("/api/health")
def health():
    return {"ok": True, "model": default_model(), "programmes": len(store.list_programmes()),
            "calendar_configured": gcal.configured()}


@app.post("/api/profile/extract", response_model=Profile)
async def profile_extract(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt"):
        raise HTTPException(400, "Upload a PDF, DOCX or TXT CV")
    data = await file.read()
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(400, "CV larger than 5 MB")
    with tempfile.TemporaryDirectory() as tmpdir:   # the CV is not kept on disk
        path = Path(tmpdir) / f"cv{suffix}"          # closed before reading: Windows cannot reopen an open temp file
        path.write_bytes(data)
        text = read_cv_text(str(path))
    try:
        prof, _ = extract_profile_llm(text, default_model(), run_tag="app")
    except LLMError as e:
        raise HTTPException(502, f"Profile extraction failed: {e}")
    return prof


@app.get("/api/programmes")
def programmes():
    return store.list_programmes()


@app.get("/api/programmes/{pid}")
def programme(pid: str):
    p = store.get_programme(pid)
    if not p:
        raise HTTPException(404, "Unknown programme")
    return {**p.model_dump(mode="json", exclude={"text"})}


class CheckRequest(BaseModel):
    profile: Profile
    programme_ids: Optional[list[str]] = None


def load_changes() -> dict:
    """Output of ingest/check_changes.py (empty structure before its first run)."""
    if CHANGES_FILE.exists():
        try:
            return json.loads(CHANGES_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {"checked_at": None, "changed": [], "new": [], "removed": []}


def _catalogue_docs() -> dict[str, str]:
    """Programme name + start of its text, for the relevance part of the ranking."""
    with store.db() as c:
        rows = c.execute("SELECT programme_id, name, substr(text, 1, ?) AS t FROM programmes",
                         (ranking.TEXT_CHARS,)).fetchall()
    return {r["programme_id"]: ranking.programme_doc(r["name"], r["t"]) for r in rows}


def _evaluate(pid, crits, profile, model, today):
    """Rule-based criteria first: if one already fails, the overall verdict cannot change, so the
    (slow, paid) semantic judge is not called. Groups of alternatives keep a semantic member at
    'not enough information' in this pass, so a group the judge could still rescue never fails here."""
    res = evaluate(pid, crits, profile, semantic_judge=None, today=today, system="S2")
    if res.overall == Label.NOT_ELIGIBLE:
        for v in res.criteria:
            if v.reason == NO_JUDGE:
                v.reason, v.rule_used = "Not checked: another requirement is already not met.", "skipped"
        return res
    judge = make_judge(model, today, 0.0, None, True, "app", [])
    return evaluate(pid, crits, profile, semantic_judge=judge, today=today, system="S2")


@app.post("/api/check")
def check(req: CheckRequest):
    """One row per programme: the engine's verdicts with evidence (breakdown), what the student
    still needs (missing), whether the deadline has passed (outdated), change notices from
    check_changes.py, and the ranking components. Rows are sorted by ranking.sort_key."""
    ids = req.programme_ids or [p["programme_id"] for p in store.list_programmes()]
    model, today, results = default_model(), date.today(), []
    profile_id = req.profile.profile_id
    docs = _catalogue_docs()
    changed = {c["programme_id"]: c for c in load_changes().get("changed", [])}
    saved = {s["programme_id"] for s in store.list_saved(profile_id)} if profile_id else set()
    for pid in ids:
        prog = store.get_programme(pid)
        if not prog:
            continue
        crits = store.get_criteria(pid, include_pending=False)
        res = _evaluate(pid, crits, req.profile, model, today)
        deadline = next((c.deadline for c in prog.criteria if c.type == CriterionType.DEADLINE and c.deadline), None)
        row = {**res.model_dump(mode="json"), "name": prog.name, "family": prog.family, "url": prog.url,
               "snapshot_date": str(prog.snapshot_date or ""), "deadline": str(deadline) if deadline else None,
               "outdated": bool(deadline and deadline < today),          # F10: shown, never listed as eligible
               "missing": missing_requirements(res, crits),              # F8: what the student still needs
               "criteria": breakdown(res, crits, req.profile, today),    # F3: requirement / profile / result / evidence
               "ranking": ranking.score(req.profile, pid, deadline, today, docs),
               "call_changed": changed.get(pid), "saved": pid in saved, "status_change": None}
        if pid in saved:
            row["status_change"] = store.update_saved_status(profile_id, pid, res.overall.value, row)
        store.log_check(pid, res.overall.value, res.model_dump_json(), profile_id)
        results.append(row)
    results.sort(key=ranking.sort_key)
    return results


# ---------------------------------------------------------------- saved programmes and dashboard (F9)
class SaveRequest(BaseModel):
    profile_id: str
    programme_id: str
    overall: Optional[str] = None
    row: Optional[dict] = None


@app.post("/api/saved")
def saved_add(req: SaveRequest):
    if not store.get_programme(req.programme_id):
        raise HTTPException(404, "Unknown programme")
    store.save_programme(req.profile_id, req.programme_id, req.overall, req.row)
    return {"ok": True}


@app.get("/api/saved")
def saved_list(profile_id: str):
    changed = {c["programme_id"]: c for c in load_changes().get("changed", [])}
    out = []
    for s in store.list_saved(profile_id):
        prog = store.get_programme(s["programme_id"])
        deadline = next((c.deadline for c in prog.criteria if c.type == CriterionType.DEADLINE and c.deadline),
                        None) if prog else None
        out.append({**s, "name": prog.name if prog else s["programme_id"], "family": prog.family if prog else None,
                    "url": prog.url if prog else None, "deadline": str(deadline) if deadline else None,
                    "outdated": bool(deadline and deadline < date.today()),
                    "call_changed": changed.get(s["programme_id"])})
    return out


@app.delete("/api/saved/{programme_id}")
def saved_delete(programme_id: str, profile_id: str):
    if not store.delete_saved(profile_id, programme_id):
        raise HTTPException(404, "Not saved")
    return {"ok": True}


@app.get("/api/history")
def history(profile_id: str, limit: int = 100):
    return store.check_history(profile_id, min(limit, 500))


# ---------------------------------------------------------------- change detection (F10)
@app.get("/api/changes")
def changes():
    return load_changes()


# ---------------------------------------------------------------- calendar (rubric C4)
def _deadline(pid: str):
    prog = store.get_programme(pid)
    if not prog:
        raise HTTPException(404, "Unknown programme")
    d = next((c.deadline for c in prog.criteria if c.type == CriterionType.DEADLINE and c.deadline), None)
    if not d:
        raise HTTPException(404, "No deadline found in this call")
    return prog, d


@app.get("/api/programmes/{pid}/deadline.ics")
def deadline_ics(pid: str):
    prog, d = _deadline(pid)
    return PlainTextResponse(gcal.ics(prog.name, d, prog.url), media_type="text/calendar",
                             headers={"Content-Disposition": f'attachment; filename="{pid}-deadline.ics"'})


@app.get("/api/calendar/status")
def calendar_status():
    return {"configured": gcal.configured(), "connected": store.get_token("google") is not None,
            "auth_url": gcal.auth_url() if gcal.configured() else None}


@app.get("/api/calendar/callback")
def calendar_callback(code: str):
    gcal.exchange_code(code)
    return RedirectResponse(os.environ.get("FRONTEND_URL", "http://localhost:3000") + "?calendar=connected")


class CalendarAdd(BaseModel):
    programme_id: str


@app.post("/api/calendar/add")
def calendar_add(req: CalendarAdd):
    prog, d = _deadline(req.programme_id)
    try:
        ev = gcal.add_deadline(prog.name, d, prog.url)
    except PermissionError:
        raise HTTPException(401, "Connect Google Calendar first")
    except requests.RequestException as e:       # Google refused (API disabled, expired token, ...): report it, do not crash
        resp = getattr(e, "response", None)
        try:
            msg = resp.json()["error"]["message"] if resp is not None else str(e)
        except Exception:
            msg = str(e)
        raise HTTPException(502, f"Google Calendar error: {msg}")
    return {"ok": True, "event_link": ev.get("htmlLink")}


# ---------------------------------------------------------------- curator (human approval point)
# Students never use these endpoints. Until accounts exist (Assignment 4), a shared curator key set
# in .env (CURATOR_KEY) separates the curator role: without it nobody can see or approve criteria.
def require_curator(x_curator_key: Optional[str] = Header(None)):
    key = os.environ.get("CURATOR_KEY")
    if not key:
        raise HTTPException(503, "Curator access is not configured: set CURATOR_KEY in .env")
    if not x_curator_key or not hmac.compare_digest(x_curator_key, key):
        raise HTTPException(401, "Wrong curator key")


@app.get("/api/curator/pending", dependencies=[Depends(require_curator)])
def curator_pending():
    return store.pending_criteria()


class Review(BaseModel):
    reviewer: str
    approve: bool


@app.post("/api/curator/review/{cid}", dependencies=[Depends(require_curator)])
def curator_review(cid: str, r: Review):
    store.review_criterion(cid, r.reviewer, r.approve)
    return {"ok": True}
