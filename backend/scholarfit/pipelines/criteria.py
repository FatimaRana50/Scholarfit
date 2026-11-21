"""Programme call text -> list of Criterion in the general schema (retrieval-augmented)."""
from __future__ import annotations

from ..llm.client import CallMeta, chat_json
from ..retrieval import Section, format_sections, quote_in_text, retrieve, split_sections
from ..schemas import Criterion, Programme
from .common import CriteriaOut, build_messages


def extract_criteria(programme: Programme, model: str, context: str = "retrieved", k: int = 6,
                     use_cache: bool = True, run_tag: str = "") -> tuple[list[Criterion], CallMeta]:
    """context = 'retrieved' (top-k eligibility sections) or 'full' (whole call)."""
    sections: list[Section] = retrieve(programme.text, k=k) if context == "retrieved" else split_sections(programme.text)
    msgs = build_messages("criteria_extract", programme_name=programme.name,
                          sections=format_sections(sections))
    # Extraction runs once per programme per snapshot, as in the product; it is cached and reused
    # by every repeated run, so repeated runs vary the decision step only.
    out, meta = chat_json(msgs, CriteriaOut, component=f"criteria_extract_{context}", model=model,
                          use_cache=True, run_tag=run_tag)
    crits = out.criteria
    supported = 0
    for i, c in enumerate(crits, 1):
        c.criterion_id = f"{programme.programme_id}-c{i}"
        ok = quote_in_text(c.source_quote, programme.text)
        supported += ok
        # citation check is deterministic: an unsupported quote lowers confidence and is flagged
        c.confidence = 1.0 if ok else 0.3
    meta.extra["n_criteria"] = len(crits)
    meta.extra["citation_supported"] = supported
    return crits, meta
