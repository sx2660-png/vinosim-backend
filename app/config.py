"""Central config + shared clients (Gemini, Postgres pool)."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    chat_model: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    vision_model: str = os.getenv("GEMINI_VISION_MODEL", "gemini-2.0-flash")
    embed_model: str = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    embed_dim: int = int(os.getenv("EMBED_DIM", "768"))
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://vinosim:vinosim@localhost:5432/vinosim"
    )
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "4"))


settings = Settings()


@lru_cache(maxsize=1)
def gemini_client():
    """A single shared google-genai client."""
    from google import genai

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in.")
    return genai.Client(api_key=settings.gemini_api_key)
