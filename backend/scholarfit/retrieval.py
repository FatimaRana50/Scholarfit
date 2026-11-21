"""Retrieval of eligibility sections from a programme call (the R in RAG).

Calls are long; only a few sections state eligibility. We split the call into
sections, score them with BM25 (and dense embeddings when sentence-transformers is
installed), fuse the rankings with reciprocal rank fusion, and pass the top-k
sections to the criteria extractor. Every extracted criterion must quote one of
these sections, which lets us check citations deterministically.
"""
from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass

ELIGIBILITY_QUERY = (
    "eligibility eligible requirements criteria applicants must candidates who bachelor degree "
    "years of education ECTS credits CGPA GPA grade percentage division class German grade "
    "IELTS TOEFL English proficiency language test waiver medium of instruction age limit born "
    "under years old nationality citizens country work experience professional experience "
    "deadline final year students who can apply not eligible")

TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


@dataclass
class Section:
    section_id: str
    heading: str
    text: str


def tokenize(s: str) -> list[str]:
    return TOKEN.findall(s.lower())


def split_sections(text: str, max_words: int = 220) -> list[Section]:
    """Split on markdown-style headings produced by the parser, then cap length."""
    blocks, heading, buf = [], "Introduction", []
    for line in text.splitlines():
        if line.startswith("#"):
            if buf:
                blocks.append((heading, "\n".join(buf).strip()))
            heading, buf = line.lstrip("# ").strip(), []
        else:
            buf.append(line)
    if buf:
        blocks.append((heading, "\n".join(buf).strip()))
    out, n = [], 0
    for h, body in blocks:
        words = body.split()
        if not words:
            continue
        for i in range(0, len(words), max_words):
            n += 1
            out.append(Section(f"s{n}", h, " ".join(words[i:i + max_words])))
    return out


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.docs, self.k1, self.b = docs, k1, b
        self.N = len(docs)
        self.avgdl = sum(map(len, docs)) / max(self.N, 1)
        df = Counter(t for d in docs for t in set(d))
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        self.tf = [Counter(d) for d in docs]

    def scores(self, query: list[str]) -> list[float]:
        out = []
        for d, tf in zip(self.docs, self.tf):
            s = 0.0
            for t in query:
                if t in tf:
                    f = tf[t]
                    s += self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(d) / self.avgdl))
            out.append(s)
        return out


def _dense_scores(query: str, sections: list[Section]):
    """Optional dense retrieval; returns None when no embedding model is installed."""
    name = os.environ.get("EMBED_MODEL")
    if not name:
        return None
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    model = SentenceTransformer(name)
    q = model.encode([query], normalize_embeddings=True)[0]
    docs = model.encode([s.heading + "\n" + s.text for s in sections], normalize_embeddings=True)
    return [float(q @ d) for d in docs]


def rrf(rankings: list[list[int]], k: int = 60) -> list[int]:
    score = Counter()
    for r in rankings:
        for rank, idx in enumerate(r):
            score[idx] += 1 / (k + rank + 1)
    return [i for i, _ in score.most_common()]


def retrieve(text: str, k: int = 6, mode: str = "hybrid") -> list[Section]:
    sections = split_sections(text)
    if not sections:
        return []
    bm = BM25([tokenize(s.heading + " " + s.text) for s in sections])
    bm_scores = bm.scores(tokenize(ELIGIBILITY_QUERY))
    bm_rank = sorted(range(len(sections)), key=lambda i: -bm_scores[i])
    rankings = [bm_rank]
    if mode in ("hybrid", "dense"):
        dense = _dense_scores(ELIGIBILITY_QUERY, sections)
        if dense is not None:
            d_rank = sorted(range(len(sections)), key=lambda i: -dense[i])
            rankings = [d_rank] if mode == "dense" else [bm_rank, d_rank]
    order = rrf(rankings) if len(rankings) > 1 else rankings[0]
    top = sorted(order[:k])            # keep document order for readability
    return [sections[i] for i in top]


def format_sections(sections: list[Section]) -> str:
    return "\n\n".join(f"[{s.section_id}] {s.heading}\n{s.text}" for s in sections)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_in_text(quote: str | None, text: str) -> bool:
    return bool(quote) and norm(quote) in norm(text)
