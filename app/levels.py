"""App levels: exams, tasting sheets, label tasks, medals and bonus reading.

Level 1 medal = pass the Level 1 exam + complete tasting sheets for 6 different wines
(re-tasting a wine keeps the new sheet but does not count it twice).
Level 2 medal = pass the Level 2 exam + 5 distinct label questions answered correctly.
Level 2 opens once the Level 1 medal is earned. Bonus medals are ungraded.
"""
from __future__ import annotations

import random
import re
from typing import Any

from fastapi import APIRouter, HTTPException

from . import db, llm
from .schemas import BonusRead, ExamStart, ExamSubmit, SheetFeedback, SheetFeedbackIn, SheetIn

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


# Completeness: six things a full sheet has. Shown as a score after every save.
COMPLETENESS_ITEMS = ("appearance", "nose", "palate", "structure_word", "sensation", "liking")


def completeness(missing: list[str]) -> dict[str, Any]:
    gaps = set(missing)
    if "palate" in gaps:
        gaps |= {"structure_word", "sensation"}
    if "palate_structure_word" in gaps:
        gaps |= {"structure_word", "sensation"}
    if "palate_sensation" in gaps:
        gaps.add("sensation")
    done = [item for item in COMPLETENESS_ITEMS if item not in gaps]
    return {"score": len(done), "total": len(COMPLETENESS_ITEMS), "done": done,
            "missing": [item for item in COMPLETENESS_ITEMS if item in gaps]}


def sheet_check(sheet: dict[str, Any]) -> dict[str, Any]:
    """What is still missing on a saved sheet, and its completeness score."""
    _, _, missing = check_sheet(sheet)
    return {"missing": missing, "completeness": completeness(missing)}


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
    study = db.study_articles_for(attempt["question_ids"])
    review, score = [], 0
    for qid in attempt["question_ids"]:
        given = body.answers.get(str(qid), "").strip().upper()
        right = key[qid]["correct_answer"].strip().upper()
        correct = given == right
        score += correct
        review.append({"id": qid, "given": given, "correct_answer": right, "correct": correct,
                       "explanation": key[qid]["explanation"], "study": study.get(qid)})
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
    sheets = db.list_sheets(user_id)
    for sheet in sheets:
        sheet["completeness"] = sheet_check(sheet)["completeness"]
    return {"sheets": sheets}


@router.post("/sheets")
def save_sheet(body: SheetIn):
    """Save (or edit, when id is given) a sheet. Progress updates here, right away;
    the tutor's note comes from POST /sheets/feedback afterwards so saving never waits on the model."""
    fields = body.model_dump(exclude={"user_id", "id"})
    complete, words, missing = check_sheet(fields)
    sheet = db.save_sheet(body.user_id, body.id, fields, words, complete)
    if sheet is None:
        raise HTTPException(404, "Unknown sheet.")
    state = progress(body.user_id)
    return {
        "sheet": sheet,
        "missing": missing,
        "completeness": completeness(missing),
        "previous": db.previous_tasting(body.user_id, sheet["id"]),
        "wines_counted": state["level1"]["sheets_complete"],
        "wines_needed": state["level1"]["sheets_needed"],
        "new_medals": state["new_medals"],
    }


SHEET_FEEDBACK_SYSTEM = (
    "You are VinoSim, a warm wine tutor. A beginner has just saved a tasting sheet with four lines: "
    "appearance, nose, palate and whether they like the wine. Your note should leave them feeling "
    "more able to describe wine, because it shows them what they already did well.\n"
    "Write 2 or 3 short sentences, under 60 words in total:\n"
    "1. Quote a few of the learner's own words in quotation marks and say exactly what was good "
    "about them (for example: linked a feeling to a structure word, said how deep the colour was, "
    "gave a reason, was honest about what they liked). Praise what they did, not the person.\n"
    "2. If the sheet is missing something, invite them to add the single most useful missing "
    "piece now (they can edit the sheet straight away), in a light \"you could add...\" tone, and "
    "say that it would complete the sheet. If nothing is missing, the sheet is complete: never "
    "imply otherwise. You may suggest one optional thing to notice next time, or none at all.\n"
    "If an earlier tasting of the same wine is given, name one concrete thing that grew since then "
    "(a more specific word, a reason added, a line filled in). Only mention growth that is really "
    "there; if little changed, say what they noticed both times.\n"
    "Rules:\n"
    "- Smell, flavour and liking have no wrong answers. Never correct them or say what this wine "
    "should smell or taste like; you have not tasted it.\n"
    "- No grades or scores, and never the words correct, wrong, mistake or should.\n"
    "- No empty or inflated praise. Never use amazing, perfect, excellent, great, wonderful, "
    "fantastic, well done, or in Chinese 很棒, 太棒了, 非常好, 优秀. Say what the words do instead "
    "(\"'deep ruby' tells me both the colour and how deep it is\").\n"
    "- Any next step stays within beginner tasting: colour and depth, smells, and the five "
    "structure words (acidity, tannin, body, sweetness, alcohol). Do not bring in finish, length, "
    "complexity or other advanced terms.\n"
    "- Do not end with a question. Plain text only, no Markdown.\n"
    "- Reply in the language the learner wrote in."
)

# Missing items in the order a learner should fill them, with a plain description for the model.
_GAP_TEXT = {
    "appearance": "the appearance line is empty",
    "nose": "the nose line is empty",
    "palate": "the palate line is empty",
    "palate_structure_word": "the palate line has no structure word (acidity, tannin, body, sweetness, alcohol)",
    "palate_sensation": "the palate line names a structure word but not the feeling behind it",
    "liking": "the liking line is empty",
}


def _sheet_text(sheet: dict[str, Any]) -> str:
    palate = sheet["palate"] + (f" (because {sheet['palate_because']})" if sheet["palate_because"] else "")
    return (
        f"Wine: {sheet['wine_name'] or '(not named)'}\n"
        f"Appearance: {sheet['appearance'] or '(empty)'}\n"
        f"Nose: {sheet['nose'] or '(empty)'}\n"
        f"Palate: {palate or '(empty)'}\n"
        f"Liking: {sheet['liking'] or '(empty)'}"
    )


def sheet_feedback_text(user_id: str, sheet_id: int) -> str:
    sheet = db.get_sheet(user_id, sheet_id)
    if sheet is None:
        raise HTTPException(404, "Unknown sheet.")
    missing = sheet_check(sheet)["missing"]
    parts = [f"The sheet just saved:\n{_sheet_text(sheet)}"]
    parts.append(
        "Still missing: " + "; ".join(_GAP_TEXT[m] for m in missing) if missing
        else "Nothing is missing: the sheet is complete."
    )
    previous = db.previous_tasting(user_id, sheet_id)
    if previous:
        parts.append(f"Earlier tasting of the same wine ({previous['created_at'][:10]}):\n{_sheet_text(previous)}")
    message = "\n\n".join(parts)
    text = _feedback_call(message)
    # The model still slips into stock praise now and then; one rewrite is enough to clear it.
    found = sorted({m.group(0) for m in EMPTY_PRAISE.finditer(text)})
    if found:
        text = _feedback_call(
            f"{message}\n\nYour draft was:\n{text}\n\nRewrite it without these words: "
            f"{', '.join(found)}. Keep the quotes and the specific reasons."
        )
    return text


EMPTY_PRAISE = re.compile(
    r"\b(amazing|perfect(ly)?|excellent|great|wonderful|fantastic|brilliant|awesome|well done)\b"
    r"|很棒|太棒|非常好|优秀|真棒",
    re.IGNORECASE,
)


def _feedback_call(message: str) -> str:
    result = llm.structured_chat(
        system=SHEET_FEEDBACK_SYSTEM, history=[], user_message=message,
        schema=SheetFeedback, temperature=0.3,
    )
    return result.feedback.strip()


@router.post("/sheets/feedback")
def sheet_feedback(body: SheetFeedbackIn):
    """A short tutor note on a saved sheet. Called by the app after the save has finished."""
    from .main import _model_failure  # same error mapping as /agent

    try:
        return {"feedback": sheet_feedback_text(body.user_id, body.sheet_id)}
    except HTTPException:
        raise
    except Exception as exc:
        raise _model_failure(exc) from exc


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
