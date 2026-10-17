from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Filters(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_score: int = Field(1, ge=1, le=5)
    max_score: int = Field(5, ge=1, le=5)
    purchase_start: date | None = None
    purchase_end: date | None = None
    review_start: date | None = None
    review_end: date | None = None
    category: str | None = Field(None, max_length=100)
    order_status: str | None = Field(None, max_length=30)
    delivery: Literal["any", "late", "on_time", "unknown"] = "any"

    @model_validator(mode="after")
    def ordered(self):
        if self.min_score > self.max_score:
            raise ValueError("Nota mínima maior que a máxima")
        for start, end in ((self.purchase_start, self.purchase_end), (self.review_start, self.review_end)):
            if start and end and start > end:
                raise ValueError("Data inicial maior que a final")
        return self


class Query(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=3, max_length=1000)
    filters: Filters = Field(default_factory=Filters)
    top_k: int = Field(6, ge=1, le=10)
    min_similarity: float = Field(0.35, ge=0, le=1, allow_inf_nan=False)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=1000)
    evidence: list[str] = Field(min_length=1, max_length=1)


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sufficient: bool
    claims: list[Claim] = Field(max_length=3)


class Verification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supported: bool
    reason: str
