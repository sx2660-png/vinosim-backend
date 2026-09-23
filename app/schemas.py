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
    answer: str = Field(description="Grounded sommelier answer for a beginner")
    wine_recommendations: list[str] = Field(default_factory=list)
    sources: list[str] = Field(
        default_factory=list, description="Titles of knowledge docs the answer relied on"
    )
    confidence: str = Field(default="medium", description="low | medium | high")


class RoleplayResponse(BaseModel):
    reply: str = Field(description="In-character sommelier reply")
    character: str = Field(default="Sommelier")
    emotion: str = Field(default="warm")


class AgentRequest(BaseModel):
    user_id: str
    mode: str = Field(description="'correction' or 'roleplay'")
    message: str


# --- Flow 4: quiz submit ---
class QuizSubmit(BaseModel):
    user_id: str
    question_id: int
    answer: str
