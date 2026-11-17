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

def random_question(level: int | None = None, item_type: str | None = None) -> dict[str, Any] | None:
    where, params = [], []
    if level is not None:
        where.append("app_level = %s")
        params.append(level)
    if item_type:
        where.append("item_type = %s")
        params.append(item_type)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with cursor() as cur:
        cur.execute(
            f"""SELECT id, question, options, category, image, app_level, item_type, sheet_line
                FROM quiz_questions {clause} ORDER BY random() LIMIT 1""",
            params,
        )
        r = cur.fetchone()
    if not r:
        return None
    return {
        "id": r[0], "question": r[1], "options": r[2], "category": r[3], "image": r[4] or "",
        "app_level": r[5], "item_type": r[6], "sheet_line": r[7],
    }


def get_question(question_id: int) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute(
            "SELECT id, correct_answer, explanation, item_type FROM quiz_questions WHERE id = %s",
            (question_id,),
        )
        r = cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "correct_answer": r[1], "explanation": r[2], "item_type": r[3]}


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


# --- Level exams (sql/005, 006, 007) ---

def level_exam_config(level: int) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute(
            "SELECT question_count, pass_pct, time_limit_min FROM level_exams WHERE app_level = %s",
            (level,),
        )
        r = cur.fetchone()
    if not r:
        return None
    return {"question_count": r[0], "pass_pct": r[1], "time_limit_min": r[2]}


def exam_pool(level: int) -> list[tuple[int, str]]:
    """(id, wset_ref) of every question that may appear in this level's exam."""
    with cursor() as cur:
        cur.execute(
            "SELECT id, wset_ref FROM quiz_questions WHERE app_level = %s AND exam_eligible",
            (level,),
        )
        return [(r[0], r[1] or "") for r in cur.fetchall()]


def questions_for_learner(ids: list[int]) -> list[dict[str, Any]]:
    """Questions without answers, in the order given."""
    with cursor() as cur:
        cur.execute(
            "SELECT id, question, options, image FROM quiz_questions WHERE id = ANY(%s)",
            (ids,),
        )
        found = {r[0]: {"id": r[0], "question": r[1], "options": r[2], "image": r[3] or ""}
                 for r in cur.fetchall()}
    return [found[i] for i in ids if i in found]


def answer_key(ids: list[int]) -> dict[int, dict[str, str]]:
    with cursor() as cur:
        cur.execute(
            "SELECT id, correct_answer, explanation FROM quiz_questions WHERE id = ANY(%s)",
            (ids,),
        )
        return {r[0]: {"correct_answer": r[1], "explanation": r[2]} for r in cur.fetchall()}


def create_exam_attempt(user_id: str, level: int, question_ids: list[int]) -> int:
    with cursor() as cur:
        cur.execute(
            """INSERT INTO exam_attempts (user_id, app_level, question_ids, total)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (user_id, level, question_ids, len(question_ids)),
        )
        return cur.fetchone()[0]


def get_exam_attempt(attempt_id: int) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute(
            """SELECT id, user_id, app_level, question_ids, total, submitted_at
               FROM exam_attempts WHERE id = %s""",
            (attempt_id,),
        )
        r = cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "user_id": r[1], "app_level": r[2], "question_ids": list(r[3]),
            "total": r[4], "submitted": r[5] is not None}


def finish_exam_attempt(attempt_id: int, answers: dict[str, str], score: int, passed: bool) -> None:
    import json

    with cursor() as cur:
        cur.execute(
            """UPDATE exam_attempts
               SET answers = %s::jsonb, score = %s, passed = %s, submitted_at = now()
               WHERE id = %s""",
            (json.dumps(answers), score, passed, attempt_id),
        )


def best_exam(user_id: str, level: int) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute(
            """SELECT score, total, passed, submitted_at FROM exam_attempts
               WHERE user_id = %s AND app_level = %s AND submitted_at IS NOT NULL
               ORDER BY passed DESC, score DESC, submitted_at DESC LIMIT 1""",
            (user_id, level),
        )
        r = cur.fetchone()
    if not r:
        return None
    return {"score": r[0], "total": r[1], "passed": bool(r[2]), "at": r[3].isoformat()}


# --- Tasting sheets ---

_SHEET_COLS = ("wine_name", "appearance", "nose", "palate", "palate_because", "liking")


def _sheet_row(r) -> dict[str, Any]:
    return {
        "id": r[0], "wine_name": r[1], "appearance": r[2], "nose": r[3], "palate": r[4],
        "palate_because": r[5], "liking": r[6], "structure_words": list(r[7] or []),
        "complete": bool(r[8]), "created_at": r[9].isoformat(), "updated_at": r[10].isoformat(),
    }


_SHEET_SELECT = """SELECT id, wine_name, appearance, nose, palate, palate_because, liking,
                          structure_words, complete, created_at, updated_at FROM tasting_sheets"""


def save_sheet(user_id: str, sheet_id: int | None, fields: dict[str, str],
               structure_words: list[str], complete: bool) -> dict[str, Any] | None:
    values = [fields.get(c, "") for c in _SHEET_COLS]
    with cursor() as cur:
        if sheet_id is None:
            cur.execute(
                f"""INSERT INTO tasting_sheets (user_id, {', '.join(_SHEET_COLS)}, structure_words, complete)
                    VALUES (%s, {', '.join(['%s'] * len(_SHEET_COLS))}, %s, %s) RETURNING id""",
                (user_id, *values, structure_words, complete),
            )
            sheet_id = cur.fetchone()[0]
        else:
            cur.execute(
                f"""UPDATE tasting_sheets SET {', '.join(f'{c} = %s' for c in _SHEET_COLS)},
                        structure_words = %s, complete = %s, updated_at = now()
                    WHERE id = %s AND user_id = %s RETURNING id""",
                (*values, structure_words, complete, sheet_id, user_id),
            )
            if cur.fetchone() is None:
                return None
        cur.execute(f"{_SHEET_SELECT} WHERE id = %s", (sheet_id,))
        return _sheet_row(cur.fetchone())


def list_sheets(user_id: str) -> list[dict[str, Any]]:
    with cursor() as cur:
        cur.execute(f"{_SHEET_SELECT} WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
        return [_sheet_row(r) for r in cur.fetchall()]


def count_complete_sheets(user_id: str) -> int:
    with cursor() as cur:
        cur.execute("SELECT count(*) FROM tasting_sheets WHERE user_id = %s AND complete", (user_id,))
        return cur.fetchone()[0]


# --- Label tasks (Level 2 medal) ---

def record_label_task(user_id: str, task_id: str, correct: bool) -> None:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO label_task_attempts (user_id, task_id, correct) VALUES (%s, %s, %s)",
            (user_id, task_id, correct),
        )


def label_tasks_done(user_id: str) -> set[str]:
    with cursor() as cur:
        cur.execute(
            "SELECT DISTINCT task_id FROM label_task_attempts WHERE user_id = %s AND correct",
            (user_id,),
        )
        return {r[0] for r in cur.fetchall()}


def label_questions() -> list[dict[str, Any]]:
    with cursor() as cur:
        cur.execute(
            """SELECT id, question, options, image FROM quiz_questions
               WHERE item_type = 'label' ORDER BY (image = '') , id"""
        )
        return [{"id": r[0], "question": r[1], "options": r[2], "image": r[3] or ""}
                for r in cur.fetchall()]


# --- Medals ---

def award_medal(user_id: str, medal_id: str) -> bool:
    """True if this call awarded it (first time)."""
    with cursor() as cur:
        cur.execute(
            """INSERT INTO medals (user_id, medal_id) VALUES (%s, %s)
               ON CONFLICT DO NOTHING RETURNING medal_id""",
            (user_id, medal_id),
        )
        return cur.fetchone() is not None


def list_medals(user_id: str) -> dict[str, str]:
    with cursor() as cur:
        cur.execute("SELECT medal_id, awarded_at FROM medals WHERE user_id = %s", (user_id,))
        return {r[0]: r[1].isoformat() for r in cur.fetchall()}


# --- Bonus reading (ungraded) ---

def bonus_articles(user_id: str) -> list[dict[str, Any]]:
    with cursor() as cur:
        cur.execute(
            """SELECT a.id, a.title, a.content, a.image, (b.user_id IS NOT NULL) AS read
               FROM articles a
               LEFT JOIN bonus_reads b ON b.article_id = a.id AND b.user_id = %s
               WHERE a.category = 'Bonus' ORDER BY a.id""",
            (user_id,),
        )
        return [{"id": r[0], "title": r[1], "content": r[2], "image": r[3] or "", "read": r[4]}
                for r in cur.fetchall()]


def mark_bonus_read(user_id: str, article_id: int) -> bool:
    with cursor() as cur:
        cur.execute("SELECT 1 FROM articles WHERE id = %s AND category = 'Bonus'", (article_id,))
        if cur.fetchone() is None:
            return False
        cur.execute(
            "INSERT INTO bonus_reads (user_id, article_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (user_id, article_id),
        )
        return True


# --- Open, ungraded tasting prompts ---

def tasting_prompts(sheet_line: str | None = None) -> list[dict[str, Any]]:
    with cursor() as cur:
        if sheet_line:
            cur.execute(
                """SELECT id, sheet_line, prompt, example_answers, guidance FROM tasting_prompts
                   WHERE sheet_line = %s ORDER BY id""",
                (sheet_line,),
            )
        else:
            cur.execute(
                "SELECT id, sheet_line, prompt, example_answers, guidance FROM tasting_prompts ORDER BY id"
            )
        return [{"id": r[0], "sheet_line": r[1], "prompt": r[2], "examples": r[3] or [],
                 "guidance": r[4] or ""} for r in cur.fetchall()]
