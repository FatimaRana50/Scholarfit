"""Ranking of programmes in the results (feature F5).

The ranking orders programmes; it does not score the student. Within a verdict group,
programmes are sorted by

    score = 0.6 * relevance + 0.25 * funding + 0.15 * urgency

- relevance: cosine similarity (0..1) between the student's degree fields + interests and the
  programme name + the first 2,000 characters of its text. Dense embeddings when
  sentence-transformers and EMBED_MODEL are available, otherwise TF-IDF (pure Python).
- funding: from `funding:` in data/sources.yaml (programme entry, else family);
  1.0 full, 0.6 partial, 0.3 tuition only, 0.5 unknown.
- urgency: 1.0 if the deadline is within 30 days, 0.5 within 90 days, 0.2 later, 0 unknown or passed.

The weights live in WEIGHTS so they can be tuned in one place. The verdict itself always
comes from the rule engine; nothing here changes it.
"""
from __future__ import annotations

import math
import os
from collections import Counter
from datetime import date
from functools import lru_cache
from typing import Optional

import yaml

from .config import DATA
from .retrieval import tokenize
from .schemas import DegreeLevel, Label, Profile

WEIGHTS = {"relevance": 0.6, "funding": 0.25, "urgency": 0.15}
FUNDING_VALUE = {"full": 1.0, "partial": 0.6, "tuition": 0.3}
FUNDING_UNKNOWN = 0.5
TEXT_CHARS = 2000
VERDICT_ORDER = {Label.ELIGIBLE.value: 0, Label.CONDITIONAL.value: 1, Label.INSUFFICIENT.value: 2,
                 Label.NOT_ELIGIBLE.value: 3}

STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to was
were will with your you our we their they which who may must can all any not no other such these those
been more than also into per each""".split())


# --------------------------------------------------------------------------- funding
@lru_cache(maxsize=1)
def funding_table() -> dict[str, str]:
    """programme_id -> full|partial|tuition, read from data/sources.yaml."""
    path = DATA / "sources.yaml"
    if not path.exists():
        return {}
    src = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = {}
    for fam in (src.get("families") or {}).values():
        fam_funding = fam.get("funding")
        for p in fam.get("programmes") or []:
            f = p.get("funding") or fam_funding
            if f:
                out[p["id"]] = f
    return out


def funding_score(programme_id: str) -> tuple[float, Optional[str]]:
    kind = funding_table().get(programme_id)
    return FUNDING_VALUE.get(kind, FUNDING_UNKNOWN), kind


# --------------------------------------------------------------------------- urgency
def urgency_score(deadline: Optional[date], today: date) -> float:
    if deadline is None or deadline < today:
        return 0.0
    days = (deadline - today).days
    return 1.0 if days <= 30 else 0.5 if days <= 90 else 0.2


# --------------------------------------------------------------------------- relevance
def _terms(text: str) -> list[str]:
    return [t for t in tokenize(text) if t not in STOP and len(t) > 1 and not t.replace(".", "").isdigit()]


def programme_doc(name: str, text: str) -> str:
    return f"{name}\n{(text or '')[:TEXT_CHARS]}"


def profile_doc(p: Profile) -> str:
    parts = []
    for d in p.degrees:
        if d.level in (DegreeLevel.BACHELOR, DegreeLevel.MASTER, DegreeLevel.PHD):
            parts += [d.field or "", d.title or ""]
    parts += p.interests
    return " ".join(x for x in parts if x)


class TfidfIndex:
    """TF-IDF over the programme documents (sublinear tf, smoothed idf), cosine similarity."""

    def __init__(self, docs: dict[str, str]):
        toks = {k: _terms(v) for k, v in docs.items()}
        n = len(toks)
        df = Counter(t for ts in toks.values() for t in set(ts))
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        self.vecs = {k: self._vec(ts) for k, ts in toks.items()}

    def _vec(self, toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        v = {t: (1 + math.log(c)) * self.idf.get(t, 0.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items() if x}

    def similarity(self, query: str, key: str) -> float:
        q = self._vec(_terms(query))
        d = self.vecs.get(key, {})
        return max(0.0, min(1.0, sum(w * d.get(t, 0.0) for t, w in q.items())))


class DenseIndex:
    def __init__(self, docs: dict[str, str], model_name: str):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        keys = list(docs)
        embs = self.model.encode([docs[k] for k in keys], normalize_embeddings=True)
        self.vecs = dict(zip(keys, embs))

    def similarity(self, query: str, key: str) -> float:
        if key not in self.vecs:
            return 0.0
        q = self.model.encode([query], normalize_embeddings=True)[0]
        return max(0.0, min(1.0, float(q @ self.vecs[key])))


_INDEX: dict = {"key": None, "index": None}


def relevance_index(docs: dict[str, str]):
    """Cached index over the catalogue; rebuilt when the set of programmes changes."""
    key = tuple(sorted(docs))
    if _INDEX["key"] != key:
        index = None
        name = os.environ.get("EMBED_MODEL")
        if name:
            try:
                index = DenseIndex(docs, name)
            except Exception:       # model or package missing: fall back to TF-IDF
                index = None
        _INDEX.update(key=key, index=index or TfidfIndex(docs))
    return _INDEX["index"]


def relevance_score(profile: Profile, programme_id: str, docs: dict[str, str]) -> float:
    query = profile_doc(profile)
    if not query.strip():
        return 0.0
    return relevance_index(docs).similarity(query, programme_id)


# --------------------------------------------------------------------------- score and order
def score(profile: Profile, programme_id: str, deadline: Optional[date], today: date,
          docs: dict[str, str]) -> dict:
    rel = relevance_score(profile, programme_id, docs)
    fund, kind = funding_score(programme_id)
    urg = urgency_score(deadline, today)
    total = WEIGHTS["relevance"] * rel + WEIGHTS["funding"] * fund + WEIGHTS["urgency"] * urg
    return {"score": round(total, 4), "relevance": round(rel, 4), "funding": fund, "funding_kind": kind,
            "urgency": urg}


def sort_key(row: dict):
    """Not outdated before outdated; then verdict group; then score (high first); then name."""
    return (bool(row.get("outdated")), VERDICT_ORDER.get(row.get("overall"), 4),
            -(row.get("ranking") or {}).get("score", 0.0), row.get("name", ""))
