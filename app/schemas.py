"""Pydantic models: HTTP request/response + Gemini structured-output schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


# --- Flow 1: OCR ---
class WineLabel(BaseModel):
    producer: str = Field(default="", description="Winery / producer name")
    wine_name: str = Field(default="", description="Cuvee or wine name")
    vintage: str = Field(default="", description="Vintage year, or NV")
    region: str = Field(default="", description="Region / appellation")
    grape_varieties: list[str] = Field(default_factory=list)
    alcohol: str = Field(default="", description="ABV, e.g. 13.5%")
    notes: str = Field(default="", description="Anything else legible on the label")


# --- Flow 2: agent (structured outputs) ---
class CorrectionResponse(BaseModel):
    answer: str = Field(description="Grounded tutor answer for a beginner")
    sources: list[str] = Field(
        default_factory=list, description="Titles of knowledge docs the answer relied on"
    )
    confidence: str = Field(default="medium", description="low | medium | high")


class RoleplayResponse(BaseModel):
    reply: str = Field(description="In-character reply from a fellow dinner guest")
    character: str = Field(default="Dinner guest")
    emotion: str = Field(default="warm")


class AgentRequest(BaseModel):
    user_id: str
    mode: str = Field(description="'correction' or 'roleplay'")
    message: str
    step: str | None = Field(
        default=None, description="Sheet line the learner is on: appearance | nose | palate | liking"
    )


# --- Levels: exams, tasting sheets, bonus ---
class ExamStart(BaseModel):
    user_id: str
    level: int = Field(ge=1, le=2)


class ExamSubmit(BaseModel):
    user_id: str
    attempt_id: int
    answers: dict[str, str] = Field(description='{"<question_id>": "B", ...}')


class SheetIn(BaseModel):
    user_id: str
    id: int | None = None
    wine_name: str = ""
    appearance: str = ""
    nose: str = ""
    palate: str = ""
    palate_because: str = ""
    liking: str = ""


class BonusRead(BaseModel):
    user_id: str
    article_id: int


# --- Flow 4: quiz submit ---
class QuizSubmit(BaseModel):
    user_id: str
    question_id: int
    answer: str
