"""Google Calendar integration (the external integration, rubric C4) plus an .ics fallback.

Setup (once): Google Cloud Console -> new project -> enable "Google Calendar API" ->
OAuth consent screen (External, add your team as test users) -> Credentials -> OAuth
client ID (Web application) with redirect URI http://localhost:8000/api/calendar/callback.
Put the client id and secret in .env as GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET.
"""
from __future__ import annotations

import json
import os
import time
from datetime import date, timedelta
from urllib.parse import urlencode

import requests

from .. import store

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
SCOPE = "https://www.googleapis.com/auth/calendar.events"


def _cfg():
    return (os.environ.get("GOOGLE_CLIENT_ID", ""), os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/calendar/callback"))


def configured() -> bool:
    cid, secret, _ = _cfg()
    return bool(cid and secret)


def auth_url(state: str = "scholarfit") -> str:
    cid, _, redirect = _cfg()
    return AUTH_URL + "?" + urlencode({"client_id": cid, "redirect_uri": redirect, "response_type": "code",
                                       "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state})


def exchange_code(code: str):
    cid, secret, redirect = _cfg()
    r = requests.post(TOKEN_URL, data={"code": code, "client_id": cid, "client_secret": secret,
                                       "redirect_uri": redirect, "grant_type": "authorization_code"}, timeout=30)
    r.raise_for_status()
    tok = r.json()
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600) - 60
    store.set_token("google", json.dumps(tok))


def _access_token() -> str | None:
    raw = store.get_token("google")
    if not raw:
        return None
    tok = json.loads(raw)
    if time.time() > tok["expires_at"] and tok.get("refresh_token"):
        cid, secret, _ = _cfg()
        r = requests.post(TOKEN_URL, data={"client_id": cid, "client_secret": secret, "grant_type": "refresh_token",
                                           "refresh_token": tok["refresh_token"]}, timeout=30)
        r.raise_for_status()
        new = r.json()
        tok.update(access_token=new["access_token"], expires_at=time.time() + new.get("expires_in", 3600) - 60)
        store.set_token("google", json.dumps(tok))
    return tok["access_token"]


def add_deadline(title: str, deadline: date, url: str | None) -> dict:
    token = _access_token()
    if token is None:
        raise PermissionError("not connected to Google Calendar")
    body = {"summary": f"Deadline: {title}",
            "description": f"Added by ScholarFit. Check the official call before applying: {url or ''}",
            "start": {"date": deadline.isoformat()}, "end": {"date": (deadline + timedelta(days=1)).isoformat()},
            "reminders": {"useDefault": False, "overrides": [{"method": "email", "minutes": 7 * 24 * 60},
                                                             {"method": "popup", "minutes": 24 * 60}]}}
    r = requests.post(EVENTS_URL, headers={"Authorization": f"Bearer {token}"}, json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def ics(title: str, deadline: date, url: str | None) -> str:
    d0, d1 = deadline.strftime("%Y%m%d"), (deadline + timedelta(days=1)).strftime("%Y%m%d")
    return "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ScholarFit//EN", "BEGIN:VEVENT",
                        f"UID:{d0}-{abs(hash(title))}@scholarfit", f"DTSTART;VALUE=DATE:{d0}",
                        f"DTEND;VALUE=DATE:{d1}", f"SUMMARY:Deadline: {title}",
                        f"DESCRIPTION:Check the official call: {url or ''}",
                        "BEGIN:VALARM", "TRIGGER:-P7D", "ACTION:DISPLAY", "DESCRIPTION:Deadline in 7 days", "END:VALARM",
                        "END:VEVENT", "END:VCALENDAR", ""])
