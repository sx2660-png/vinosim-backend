"""Async preference distill: one tutor turn -> weak topics and mentioned topics.

The chat response does not wait on this. Article ranking reads the stored profile later.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from . import db, llm

log = logging.getLogger(__name__)

# Closed vocabulary shared with articles.topics and the new tasting notes.
ALLOWED_TOPICS = frozenset({
    "tasting", "appearance", "nose", "palate", "finish",
    "acidity", "tannin", "body", "alcohol", "sweetness", "balance", "quality",
    "aroma", "bordeaux", "burgundy", "pinot", "cabernet", "merlot",
    "sangiovese", "tuscany", "riesling", "champagne", "sparkling",
    "orange", "natural", "pairing", "service", "label",
})

# Titles already in the correction corpus, plus the tasting-method notes.
DOC_TOPICS: dict[str, list[str]] = {
    "Tannin": ["tannin", "palate"],
    "Acidity": ["acidity", "palate"],
    "Body": ["body", "palate", "alcohol"],
    "Bordeaux Left Bank vs Right Bank": ["bordeaux", "cabernet", "merlot"],
    "Burgundy and Pinot Noir": ["burgundy", "pinot"],
    "Sangiovese and Tuscany": ["sangiovese", "tuscany", "acidity", "tannin"],
    "Riesling": ["riesling", "acidity", "sweetness"],
    "Orange (skin-contact) wine": ["orange", "tannin"],
    "Food pairing basics": ["pairing", "acidity", "tannin", "sweetness"],
    "Champagne and traditional method": ["champagne", "sparkling"],
    "Decanting and serving temperature": ["service"],
    "Reading a wine label": ["label"],
    "Tasting sequence": ["tasting", "appearance", "nose", "palate", "finish"],
    "What to look for in the glass": ["appearance", "tasting"],
    "Aroma families": ["aroma", "nose", "cabernet"],
    "Order of checks on the palate": ["palate", "sweetness", "acidity", "tannin", "alcohol", "body", "finish"],
    "Finish and length": ["finish", "quality", "palate"],
    "Judging quality without a score": ["quality", "balance", "finish", "tasting"],
    "How a bottle review is organized": ["tasting", "appearance", "nose", "palate"],
}


class TurnDistill(BaseModel):
    summary: str = Field(description="One sentence on what this turn showed about the learner.")
    weak_topics: list[str] = Field(
        default_factory=list,
        description="Allowed topic ids the learner is unsure about or asked to have explained.",
    )
    mentioned_topics: list[str] = Field(
        default_factory=list,
        description="Allowed topic ids that came up and are worth a later reading.",
    )


def _keep(topics: list[str]) -> list[str]:
    chosen: list[str] = []
    for topic in topics:
        key = topic.strip().lower()
        if key in ALLOWED_TOPICS and key not in chosen:
            chosen.append(key)
    return chosen


def _from_docs(titles: list[str]) -> list[str]:
    found: list[str] = []
    for title in titles:
        for topic in DOC_TOPICS.get(title, []):
            if topic not in found:
                found.append(topic)
    return found


def _bump(counts: dict, topics: list[str]) -> dict:
    merged = {key: int(value) for key, value in counts.items() if key in ALLOWED_TOPICS}
    for topic in topics:
        merged[topic] = merged.get(topic, 0) + 1
    return merged


def distill_turn(
    user_id: str,
    mode: str,
    user_message: str,
    assistant_message: str,
    doc_titles: list[str] | None = None,
) -> None:
    """Summarize one finished turn and merge it into the learner profile. Never raises."""
    try:
        titles = [title for title in (doc_titles or []) if isinstance(title, str)]
        mentioned = _from_docs(titles)
        summary = ""
        weak: list[str] = []
        if user_message.strip():
            allowed = ", ".join(sorted(ALLOWED_TOPICS))
            system = (
                "You distill one wine-tutor turn into a learner profile. "
                f"Use only these topic ids: {allowed}. "
                "weak_topics are things the learner does not yet have words for, or asked to have explained. "
                "mentioned_topics are knowledge points that appeared, including ones already in the answer. "
                "Do not invent a weakness that the message does not show. Keep summary to one sentence."
            )
            user = (
                f"Mode: {mode}\n"
                f"Learner: {user_message.strip()}\n"
                f"Tutor: {assistant_message.strip()}\n"
                f"Notes used: {', '.join(titles) if titles else '(none)'}"
            )
            distilled = llm.structured_chat(
                system=system,
                history=[],
                user_message=user,
                schema=TurnDistill,
                temperature=0.1,
            )
            summary = distilled.summary.strip()
            weak = _keep(distilled.weak_topics)
            mentioned = _keep(mentioned + distilled.mentioned_topics)
        if not summary and not weak and not mentioned:
            return
        db.merge_learner_profile(
            user_id,
            weak_topics=_bump({}, weak),
            mentioned_topics=_bump({}, mentioned),
            summary=summary,
            mode=mode,
            at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception:
        log.exception("learner profile distill failed for %s", user_id)
