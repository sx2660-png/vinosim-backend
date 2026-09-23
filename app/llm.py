"""Thin wrappers around Gemini: embeddings, structured chat, and vision OCR."""
from __future__ import annotations

from typing import Type, TypeVar

from google.genai import types
from pydantic import BaseModel

from .config import gemini_client, settings

T = TypeVar("T", bound=BaseModel)


def embed(text: str, *, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Embed a single text. Use RETRIEVAL_QUERY for queries, RETRIEVAL_DOCUMENT for docs."""
    client = gemini_client()
    resp = client.models.embed_content(
        model=settings.embed_model,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return list(resp.embeddings[0].values)


def structured_chat(
    *,
    system: str,
    history: list[dict[str, str]],
    user_message: str,
    schema: Type[T],
    temperature: float = 0.3,
) -> T:
    """Chat completion constrained to a pydantic schema (Structured Output Parser)."""
    client = gemini_client()
    contents: list[types.Content] = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=turn["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    resp = client.models.generate_content(
        model=settings.chat_model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    parsed = resp.parsed
    if isinstance(parsed, schema):
        return parsed
    # Fallback: parse raw JSON text if the SDK didn't hydrate .parsed
    return schema.model_validate_json(resp.text)


def vision_extract(image_bytes: bytes, mime_type: str, prompt: str, schema: Type[T]) -> T:
    """Gemini Vision OCR of a wine label into a structured schema (Flow 1)."""
    client = gemini_client()
    resp = client.models.generate_content(
        model=settings.vision_model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            types.Part(text=prompt),
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    parsed = resp.parsed
    if isinstance(parsed, schema):
        return parsed
    return schema.model_validate_json(resp.text)
