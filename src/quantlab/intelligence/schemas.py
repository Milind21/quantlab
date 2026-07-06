"""schemas — typed data contracts for the intelligence layer.

`Post` is a normalized third-party item (treated as UNTRUSTED data). `ParamProposal` is the
safety core: a bounded, evidence-linked suggestion that is INERT until a human approves it.
Validation reuses config.validate_proposal so bounds + tighten_only live in ONE place.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ..config import Bound, validate_proposal

Sentiment = Literal["bull", "bear", "neutral"]


class Post(BaseModel):
    id: str
    source: str
    ticker: str
    author: str
    created_utc: float
    text: str
    native_tag: Sentiment | None = None  # e.g. StockTwits bull/bear label


class Evidence(BaseModel):
    post_id: str
    source: str
    quote: str


class ParamProposal(BaseModel):
    """A bounded suggestion to nudge ONE pre-approved knob. Inert until human-approved."""
    param: str
    current: float
    proposed: float
    direction: Literal["any", "tighten_only"]
    rationale: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    expires_at: str  # ISO date; proposal is void after this

    @field_validator("rationale")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("rationale required")
        return v

    def check_against(self, bound: Bound) -> tuple[bool, str]:
        """Validate this proposal against the frozen config bound (bounds + direction)."""
        if self.param != bound.param:
            return False, f"param mismatch {self.param} != {bound.param}"
        return validate_proposal(bound, self.current, self.proposed)
