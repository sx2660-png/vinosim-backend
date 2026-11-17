"""App levels: exams, tasting sheets, label tasks, medals and bonus reading.

Level 1 medal = pass the Level 1 exam + 6 complete tasting sheets.
Level 2 medal = pass the Level 2 exam + 5 distinct label questions answered correctly.
Level 2 opens once the Level 1 medal is earned. Bonus medals are ungraded.
"""
from __future__ import annotations

import random
import re
from typing import Any

from fastapi import APIRouter, HTTPException

from . import db
from .schemas import BonusRead, ExamStart, ExamSubmit, SheetIn

router = APIRouter()

SHEETS_FOR_LEVEL1 = 6
LABELS_FOR_LEVEL2 = 5

# Questions per learning outcome in the WSET exams (spec section 4). Pools are drawn
# in the same proportions, scaled to the configured question_count.
WSET_WEIGHTS: dict[int, dict[str, int]] = {
    1: {"L1-LO1": 6, "L1-LO2": 18, "L1-LO3": 6},
    2: {"L2-LO1": 5, "L2-LO2": 4, "L2-LO3": 19, "L2-LO4": 12, "L2-LO5": 6, "L2-LO6": 4},
}

# Palate standard: a structure word plus the sensation it refers to.
STRUCTURE_WORDS: dict[str, str] = {
    r"acid": "acidity", r"\btart": "acidity", r"酸": "acidity",
    r"tannin": "tannin", r"单宁": "tannin",
    r"bod(y|ied)": "body", r"酒体": "body",
    r"sweet": "sweetness", r"甜": "sweetness",
    r"alcohol": "alcohol", r"酒精": "alcohol",
}
SENSATION_WORDS = re.compile(
    r"mouth.?water|water|saliva|tight|grip|gum|cheek|dry|drying|rough|astring|smooth|soft|"
    r"heavy|thin|weight|rich|round|sharp|tang|fresh|crisp|zest|warm|hot|burn|"
    r"sugary|sticky|syrup|honey|feel|"
    r"流口水|口水|紧|涩|干|厚|重|轻|薄|刺|热|烫|辣|黏|腻|顺|滑|柔|感觉",
    re.IGNORECASE,
)


def check_sheet(fields: dict[str, str]) -> tuple[bool, list[str], list[str]]:
    """Return (complete, structure_words found, what is still missing)."""
    missing = [line for line in ("appearance", "nose", "palate", "liking") if not fields.get(line, "").strip()]
    palate = fields.get("palate", "")
    words = sorted({name for pattern, name in STRUCTURE_WORDS.items() if re.search(pattern, palate, re.IGNORECASE)})
    if palate.strip():
        if not words:
            missing.append("palate_structure_word")
        elif not (SENSATION_WORDS.search(palate) or fields.get("palate_because", "").strip()):
            missing.append("palate_sensation")
    return not missing, words, missing


def sample_exam(level: int, count: int) -> list[int]:
    by_ref: dict[str, list[int]] = {}
    for qid, ref in db.exam_pool(level):
        by_ref.setdefault(ref, []).append(qid)
    weights = WSET_WEIGHTS[level]
    total_weight = sum(weights.values())
    chosen: list[int] = []
    for ref, weight in weights.items():
        want = round(count * weight / total_weight)
        pool = by_ref.get(ref, [])
        chosen += random.sample(pool, min(want, len(pool)))
    leftover = [qid for ids in by_ref.values() for qid in ids if qid not in chosen]
    random.shuffle(leftover)
    chosen = (chosen + leftover)[:count]
    random.shuffle(chosen)
    return chosen


def progress(user_id: str) -> dict[str, Any]:
    """Current progress; awards any medal the learner has just earned."""
    newly: list[str] = []
    exam1, exam2 = db.best_exam(user_id, 1), db.best_exam(user_id, 2)
    sheets = db.count_complete_sheets(user_id)
    labels = len(db.label_tasks_done(user_id))

    if exam1 and exam1["passed"] and sheets >= SHEETS_FOR_LEVEL1 and db.award_medal(user_id, "level1"):
        newly.append("level1")
    medals = db.list_medals(user_id)
    level2_open = "level1" in medals
    if level2_open and exam2 and exam2["passed"] and labels >= LABELS_FOR_LEVEL2 and db.award_medal(user_id, "level2"):
        newly.append("level2")

    bonus = db.bonus_articles(user_id)
    for article in bonus:
        if article["read"] and db.award_medal(user_id, f"bonus:{article['id']}"):
            newly.append(f"bonus:{article['id']}")
    medals = db.list_medals(user_id)

    return {
        "user_id": user_id,
        "level1": {
            "exam": exam1, "sheets_complete": sheets, "sheets_needed": SHEETS_FOR_LEVEL1,
            "medal": medals.get("level1"),
        },
        "level2": {
            "unlocked": level2_open, "exam": exam2, "labels_done": labels,
            "labels_needed": LABELS_FOR_LEVEL2, "medal": medals.get("level2"),
        },
        "bonus": {
            "status": "Still growing: more topics are on the way.",
            "articles": [{"id": a["id"], "title": a["title"], "read": a["read"],
                          "medal": medals.get(f"bonus:{a['id']}")} for a in bonus],
        },
        "course_complete": "level1" in medals and "level2" in medals,
        "new_medals": newly,
    }


@router.get("/progress")
def get_progress(user_id: str):
    return progress(user_id)


@router.post("/exam/start")
def exam_start(body: ExamStart):
    if body.level == 2 and "level1" not in db.list_medals(body.user_id):
        raise HTTPException(403, "Level 2 opens after the Level 1 medal.")
    config = db.level_exam_config(body.level)
    if not config:
        raise HTTPException(404, "No exam configured for this level.")
    ids = sample_exam(body.level, config["question_count"])
    attempt_id = db.create_exam_attempt(body.user_id, body.level, ids)
    return {
        "attempt_id": attempt_id, "level": body.level, "pass_pct": config["pass_pct"],
        "time_limit_min": config["time_limit_min"], "questions": db.questions_for_learner(ids),
    }


@router.post("/exam/submit")
def exam_submit(body: ExamSubmit):
    attempt = db.get_exam_attempt(body.attempt_id)
    if not attempt or attempt["user_id"] != body.user_id:
        raise HTTPException(404, "Unknown exam attempt.")
    if attempt["submitted"]:
        raise HTTPException(409, "This exam was already submitted.")
    key = db.answer_key(attempt["question_ids"])
    review, score = [], 0
    for qid in attempt["question_ids"]:
        given = body.answers.get(str(qid), "").strip().upper()
        right = key[qid]["correct_answer"].strip().upper()
        correct = given == right
        score += correct
        review.append({"id": qid, "given": given, "correct_answer": right, "correct": correct,
                       "explanation": key[qid]["explanation"]})
    config = db.level_exam_config(attempt["app_level"]) or {"pass_pct": 70}
    passed = score * 100 >= config["pass_pct"] * attempt["total"]
    db.finish_exam_attempt(body.attempt_id, {k: v.strip().upper() for k, v in body.answers.items()}, score, passed)
    return {
        "level": attempt["app_level"], "score": score, "total": attempt["total"],
        "pass_pct": config["pass_pct"], "passed": passed, "review": review,
        "new_medals": progress(body.user_id)["new_medals"],
    }


@router.get("/sheets")
def get_sheets(user_id: str):
    return {"sheets": db.list_sheets(user_id)}


@router.post("/sheets")
def save_sheet(body: SheetIn):
    fields = body.model_dump(exclude={"user_id", "id"})
    complete, words, missing = check_sheet(fields)
    sheet = db.save_sheet(body.user_id, body.id, fields, words, complete)
    if sheet is None:
        raise HTTPException(404, "Unknown sheet.")
    return {"sheet": sheet, "missing": missing, "new_medals": progress(body.user_id)["new_medals"]}


@router.get("/labels/tasks")
def label_tasks(user_id: str):
    done = db.label_tasks_done(user_id)
    tasks = [{**q, "done": f"q{q['id']}" in done} for q in db.label_questions()]
    return {"needed": LABELS_FOR_LEVEL2, "done": len(done), "tasks": tasks}


@router.get("/bonus")
def bonus(user_id: str):
    return {"status": "Still growing: more topics are on the way.", "articles": db.bonus_articles(user_id)}


@router.post("/bonus/read")
def bonus_read(body: BonusRead):
    if not db.mark_bonus_read(body.user_id, body.article_id):
        raise HTTPException(404, "Unknown bonus article.")
    return {"ok": True, "new_medals": progress(body.user_id)["new_medals"]}


@router.get("/prompts")
def prompts(line: str | None = None):
    return {"prompts": db.tasting_prompts(line)}
