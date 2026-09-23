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
            "SELECT id, question, options, category FROM quiz_questions ORDER BY random() LIMIT 1"
        )
        r = cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "question": r[1], "options": r[2], "category": r[3]}


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


# --- Articles (Flow 6) ---

def list_articles(category: str | None = None) -> list[dict[str, Any]]:
    with cursor() as cur:
        if category:
            cur.execute(
                "SELECT id, title, category, content, image FROM articles WHERE category = %s ORDER BY id",
                (category,),
            )
        else:
            cur.execute("SELECT id, title, category, content, image FROM articles ORDER BY id")
        rows = cur.fetchall()
    return [
        {"id": r[0], "title": r[1], "category": r[2], "content": r[3], "image": r[4]}
        for r in rows
    ]
