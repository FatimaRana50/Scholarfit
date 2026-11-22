"""ScholarFit API.  Run:  uvicorn app.main:app --reload --port 8000  (from backend/)"""
from __future__ import annotations

import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from scholarfit import store
from scholarfit.config import default_model
from scholarfit.integrations import gcal
from scholarfit.llm.client import LLMError
from scholarfit.pipelines.cv import extract_profile_llm, read_cv_text
from scholarfit.pipelines.systems import make_judge
from scholarfit.rules.engine import evaluate
from scholarfit.schemas import CriterionType, Label, Profile

app = FastAPI(title="ScholarFit API", version="0.3")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
                   allow_methods=["*"], allow_headers=["*"])
MAX_CV_BYTES = 5 * 1024 * 1024
ORDER = {Label.ELIGIBLE: 0, Label.INSUFFICIENT: 1, Label.NOT_ELIGIBLE: 2}


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


@app.post("/api/check")
def check(req: CheckRequest):
    ids = req.programme_ids or [p["programme_id"] for p in store.list_programmes()]
    model, today, results = default_model(), date.today(), []
    for pid in ids:
        prog = store.get_programme(pid)
        if not prog:
            continue
        crits = store.get_criteria(pid, include_pending=False)
        judge = make_judge(model, today, 0.0, None, True, "app", [])
        res = evaluate(pid, crits, req.profile, semantic_judge=judge, today=today, system="S2",
                       skip_judge_if_failed=True)
        deadline = next((c.deadline for c in prog.criteria if c.type == CriterionType.DEADLINE and c.deadline), None)
        row = {**res.model_dump(mode="json"), "name": prog.name, "family": prog.family, "url": prog.url,
               "snapshot_date": str(prog.snapshot_date or ""), "deadline": str(deadline) if deadline else None}
        store.log_check(pid, res.overall.value, res.model_dump_json())
        results.append(row)
    results.sort(key=lambda r: (ORDER.get(Label(r["overall"]), 3), r["name"]))
    return results


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
@app.get("/api/curator/pending")
def curator_pending():
    return store.pending_criteria()


class Review(BaseModel):
    reviewer: str
    approve: bool


@app.post("/api/curator/review/{cid}")
def curator_review(cid: str, r: Review):
    store.review_criterion(cid, r.reviewer, r.approve)
    return {"ok": True}
