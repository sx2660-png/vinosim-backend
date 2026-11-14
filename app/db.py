"""Postgres access with a small connection pool and pgvector registered."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from .config import settings


def _configure(conn: psycopg.Connection) -> None:
    register_vector(conn)


_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=5,
            configure=_configure,
            kwargs={"autocommit": True},
            open=True,
        )
    return _pool


@contextmanager
def cursor():
    with pool().connection() as conn:
        with conn.cursor() as cur:
            yield cur


# --- Chat history (Flow 2: Select Chat History / Update Database) ---

def load_chat_history(user_id: str, mode: str, limit: int = 10) -> list[dict[str, str]]:
    with cursor() as cur:
        cur.execute(
            """
            SELECT role, content FROM chat_history
            WHERE user_id = %s AND mode = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (user_id, mode, limit),
        )
        rows = cur.fetchall()
    rows.reverse()  # chronological
    return [{"role": r[0], "content": r[1]} for r in rows]


def save_turn(user_id: str, mode: str, role: str, content: str) -> None:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO chat_history (user_id, mode, role, content) VALUES (%s, %s, %s, %s)",
            (user_id, mode, role, content),
        )


# --- RAG retrieval (Flow 2 correction branch: Postgres PGVector Store) ---

def similarity_search(query_embedding: list[float], k: int) -> list[dict[str, Any]]:
    with cursor() as cur:
        cur.execute(
            """
            SELECT id, title, content, metadata,
                   1 - (embedding <=> %s::vector) AS score
            FROM wine_docs
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_embedding, query_embedding, k),
        )
        rows = cur.fetchall()
    return [
        {"id": r[0], "title": r[1], "content": r[2], "metadata": r[3], "score": float(r[4])}
        for r in rows
    ]


# --- Quiz (Flow 3 & 4) ---

def random_question() -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute(
            "SELECT id, question, options, category, image FROM quiz_questions ORDER BY random() LIMIT 1"
        )
        r = cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "question": r[1], "options": r[2], "category": r[3], "image": r[4] or ""}


def get_question(question_id: int) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute(
            "SELECT id, correct_answer, explanation FROM quiz_questions WHERE id = %s",
            (question_id,),
        )
        r = cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "correct_answer": r[1], "explanation": r[2]}


def save_quiz_attempt(user_id: str, question_id: int, user_answer: str, is_correct: bool) -> None:
    with cursor() as cur:
        cur.execute(
            """INSERT INTO quiz_history (user_id, question_id, user_answer, is_correct)
               VALUES (%s, %s, %s, %s)""",
            (user_id, question_id, user_answer, is_correct),
        )


def user_score(user_id: str) -> dict[str, int]:
    with cursor() as cur:
        cur.execute(
            """SELECT count(*) FILTER (WHERE is_correct), count(*)
               FROM quiz_history WHERE user_id = %s""",
            (user_id,),
        )
        r = cur.fetchone()
    return {"correct": r[0] or 0, "total": r[1] or 0}


# --- Learner profile (distilled after each tutor turn) ---

def get_learner_profile(user_id: str) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute(
            """
            SELECT weak_topics, mentioned_topics, summaries, updated_at
            FROM learner_profiles WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    updated = row[3]
    return {
        "user_id": user_id,
        "weak_topics": row[0] or {},
        "mentioned_topics": row[1] or {},
        "summaries": row[2] or [],
        "updated_at": updated.isoformat() if updated else "",
    }


def merge_learner_profile(
    user_id: str,
    *,
    weak_topics: dict[str, int],
    mentioned_topics: dict[str, int],
    summary: str,
    mode: str,
    at: str,
) -> None:
    """Add this turn's topic counts to the stored profile. One transaction."""
    import json

    with pool().connection() as conn:
        previous = conn.autocommit
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO learner_profiles (user_id) VALUES (%s)
                    ON CONFLICT (user_id) DO NOTHING
                    """,
                    (user_id,),
                )
                cur.execute(
                    """
                    SELECT weak_topics, mentioned_topics, summaries
                    FROM learner_profiles WHERE user_id = %s FOR UPDATE
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                weak = {key: int(value) for key, value in dict(row[0] or {}).items()}
                mentioned = {key: int(value) for key, value in dict(row[1] or {}).items()}
                summaries = list(row[2] or [])
                for key, inc in weak_topics.items():
                    weak[key] = weak.get(key, 0) + int(inc)
                for key, inc in mentioned_topics.items():
                    mentioned[key] = mentioned.get(key, 0) + int(inc)
                if summary:
                    summaries.append({"at": at, "mode": mode, "summary": summary})
                    summaries = summaries[-12:]
                cur.execute(
                    """
                    UPDATE learner_profiles
                    SET weak_topics = %s::jsonb,
                        mentioned_topics = %s::jsonb,
                        summaries = %s::jsonb,
                        updated_at = now()
                    WHERE user_id = %s
                    """,
                    (json.dumps(weak), json.dumps(mentioned), json.dumps(summaries), user_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.autocommit = previous


def _article_rank(topics: list[str], weak: dict, mentioned: dict) -> tuple[int, list[str]]:
    score = 0
    matched: list[str] = []
    for topic in topics:
        weak_count = int(weak.get(topic, 0) or 0)
        mentioned_count = int(mentioned.get(topic, 0) or 0)
        if weak_count or mentioned_count:
            matched.append(topic)
        score += 2 * weak_count + mentioned_count
    matched.sort(key=lambda topic: (0 if int(weak.get(topic, 0) or 0) else 1, topic))
    return score, matched


# --- Articles (Flow 6) ---

def list_articles(category: str | None = None, user_id: str | None = None) -> list[dict[str, Any]]:
    profile = get_learner_profile(user_id) if user_id else None
    weak = (profile or {}).get("weak_topics") or {}
    mentioned = (profile or {}).get("mentioned_topics") or {}
    with cursor() as cur:
        if category:
            cur.execute(
                """
                SELECT id, title, category, content, image, topics
                FROM articles WHERE category = %s ORDER BY id
                """,
                (category,),
            )
        else:
            cur.execute(
                "SELECT id, title, category, content, image, topics FROM articles ORDER BY id"
            )
        rows = cur.fetchall()
    articles = []
    for row in rows:
        topics = list(row[5] or [])
        score, matched = _article_rank(topics, weak, mentioned)
        articles.append({
            "id": row[0],
            "title": row[1],
            "category": row[2],
            "content": row[3],
            "image": row[4],
            "topics": topics,
            "match": matched,
            "score": score,
        })
    articles.sort(key=lambda article: (-article["score"], article["id"]))
    return articles
