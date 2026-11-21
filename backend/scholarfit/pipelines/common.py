from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, Field

from ..config import prompt
from ..schemas import Criterion, CriterionType, Label, Profile


def build_messages(name: str, **values) -> list[dict]:
    text = prompt(name)
    system, user = text.split("### USER", 1)
    for k, v in values.items():
        user = user.replace(f"<<{k}>>", str(v))
        system = system.replace(f"<<{k}>>", str(v))
    return [{"role": "system", "content": system.strip()}, {"role": "user", "content": user.strip()}]


def profile_json(p: Profile) -> str:
    d = p.model_dump(mode="json", exclude_none=True)
    d.pop("profile_id", None)
    return json.dumps(d, indent=1)


# ----- LLM output schemas
class CriteriaOut(BaseModel):
    criteria: list[Criterion] = Field(default_factory=list)


class LabelOut(BaseModel):
    label: Label
    reason: str = ""


class B1Criterion(BaseModel):
    type: CriterionType = CriterionType.OTHER
    label: Label
    reason: str = ""


class B1Out(BaseModel):
    reasoning: Optional[str] = None
    criteria: list[B1Criterion] = Field(default_factory=list)
    overall: Label
