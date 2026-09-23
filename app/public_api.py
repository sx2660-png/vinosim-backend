"""Routes the online WinePal app already calls.

The Vite app posts to `/webhook/...` and expects the old n8n field names.
These handlers translate that contract onto the local quiz, article, and agent code.
"""
from __future__ import annotations

import json
import random
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from . import db, llm
from .graph.agent_graph import run_agent
from .schemas import WineLabel

router = APIRouter(prefix="/webhook")

LABEL_PROMPT = (
    "Read this wine label and extract the fields. Leave a field blank if it is not legible. "
    "Do not guess beyond what is printed."
)

# The label-decoder screen asks for a finished quiz plus an image URL.
# It does not upload a photo. These are the same public label photos the app already ships.
LABEL_QUIZZES: list[dict[str, Any]] = [
    {
        "id": "label_1",
        "image_url": "https://i.ibb.co/wZ7HmcrV/wine-label-1.jpg",
        "question": "Identify the region based on the label style:",
        "options": [
            "Bordeaux, France",
            "Napa Valley, USA",
            "Tuscany, Italy",
            "Rioja, Spain",
            "Mendoza, Argentina",
            "Barossa, Australia",
        ],
        "correct_answer": "Bordeaux, France",
        "explanation": "The classic chateau illustration and typography are hallmarks of traditional Bordeaux labels.",
    },
    {
        "id": "label_2",
        "image_url": "https://i.ibb.co/W4DhyV3p/wine-label-2.jpg",
        "question": "What is the most likely grape variety for this bottle?",
        "options": [
            "Pinot Noir",
            "Cabernet Sauvignon",
            "Riesling",
            "Chardonnay",
            "Syrah",
            "Sauvignon Blanc",
        ],
        "correct_answer": "Riesling",
        "explanation": "The tall, slender flute bottle shape combined with the Germanic styling often indicates Riesling.",
    },
    {
        "id": "label_3",
        "image_url": "https://i.ibb.co/p6Z4qjNz/wine-label-3.jpg",
        "question": "Which classification does this label likely represent?",
        "options": ["Grand Cru Classé", "DOCG", "Reserva", "Qba", "Grand Reserve", "Premier Cru"],
        "correct_answer": "DOCG",
        "explanation": "The pink seal on the neck indicates an Italian DOCG classification.",
    },
    {
        "id": "label_4",
        "image_url": "https://i.ibb.co/mrYBmdvz/wine-label-4.jpg",
        "question": "Identify the producer style:",
        "options": [
            "Old World Traditional",
            "New World Modern",
            "Natural / Low Intervention",
            "Bulk Commercial",
            "Fortified",
            "Sparkling",
        ],
        "correct_answer": "Natural / Low Intervention",
        "explanation": "Abstract label art without prominent traditional text is a common natural-wine aesthetic.",
    },
    {
        "id": "label_5",
        "image_url": "https://i.ibb.co/YFpLdfKP/wine-label-5.jpg",
        "question": "What information appears to be emphasized on this label?",
        "options": [
            "The Estate Name",
            "The Vintage Year",
            "The Grape Variety",
            "The Alcohol Content",
            "The Importer",
            "The Soil Type",
        ],
        "correct_answer": "The Estate Name",
        "explanation": "The label design prioritizes the producer name over the grape or region.",
    },
]


class WebhookChat(BaseModel):
    sessionId: str | None = None
    userId: str | None = None
    user_id: str | None = None
    mode: str
    message: str


class WebhookQuizSubmit(BaseModel):
    userId: str | None = None
    user_id: str | None = None
    questionId: str | int | None = None
    question_id: str | int | None = None
    answer: str


def _as_options(raw: Any) -> list[str]:
    if isinstance(raw, str):
        parsed = json.loads(raw)
        return [str(item) for item in parsed]
    return [str(item) for item in raw]


def _option_for_letter(options: list[str], letter: str) -> str:
    key = letter.strip().upper()
    for opt in options:
        text = opt.strip()
        if text.upper() == key or text.upper().startswith(key + "."):
            return opt
    return letter


def _answer_matches(answer: str, letter: str, options: list[str]) -> bool:
    given = answer.strip()
    key = letter.strip().upper()
    if given.upper() == key or given.upper().startswith(key + "."):
        return True
    return given == _option_for_letter(options, letter)


def _full_question(question_id: int) -> dict[str, Any] | None:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, question, options, correct_answer, explanation, category
            FROM quiz_questions WHERE id = %s
            """,
            (question_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "question": row[1],
        "options": _as_options(row[2]),
        "correct_answer": row[3],
        "explanation": row[4],
        "category": row[5],
    }


@router.post("/wine/scan")
async def wine_scan(data: UploadFile | None = File(default=None)):
    if data is None:
        raise HTTPException(400, "Provide a multipart file field named data.")
    image = await data.read()
    mime = data.content_type or "image/jpeg"
    label: WineLabel = llm.vision_extract(image, mime, LABEL_PROMPT, WineLabel)
    return {
        "name": label.wine_name or label.producer,
        "grape": ", ".join(label.grape_varieties),
        "region": label.region,
        "year": label.vintage,
    }


@router.post("/chat2")
def chat2(body: WebhookChat):
    mode = body.mode
    if mode not in ("correction", "roleplay"):
        raise HTTPException(400, "mode must be 'correction' or 'roleplay'")
    user_id = body.userId or body.user_id or "anon"
    result = run_agent(user_id, mode, body.message)
    reply = result.get("reply") or result.get("answer") or ""
    raw_character = result.get("character")
    if isinstance(raw_character, str) and raw_character:
        character = {"name": raw_character, "role": "Sommelier", "avatarSeed": "host"}
    else:
        character = {"name": "Host", "role": "Sommelier", "avatarSeed": "host"}
    return {
        "reply": reply,
        "sessionId": body.sessionId,
        "character": character,
    }


@router.get("/wine/quiz/get")
def quiz_get():
    picked = db.random_question()
    if not picked:
        raise HTTPException(404, "No questions seeded.")
    full = _full_question(int(picked["id"]))
    if not full:
        raise HTTPException(404, "No questions seeded.")
    options = full["options"]
    return {
        "id": str(full["id"]),
        "type": "text",
        "question": full["question"],
        "options": options,
        "correct_answer": _option_for_letter(options, full["correct_answer"]),
        "explanation": full["explanation"],
        "category": full["category"],
    }


@router.get("/get-label-quiz")
def label_quiz():
    quiz = random.choice(LABEL_QUIZZES)
    return {
        "id": quiz["id"],
        "image_url": quiz["image_url"],
        "question": quiz["question"],
        "options": quiz["options"],
        "correct_answer": quiz["correct_answer"],
        "explanation": quiz["explanation"],
    }


@router.post("/wine/quiz/submit")
def quiz_submit(body: WebhookQuizSubmit):
    raw_id = body.questionId if body.questionId is not None else body.question_id
    user_id = body.userId or body.user_id or "anon"
    if raw_id is None:
        raise HTTPException(400, "questionId is required.")
    try:
        question_id = int(raw_id)
    except (TypeError, ValueError):
        return {"result": "Submitted", "correct_answer": "", "explanation": ""}

    question = _full_question(question_id)
    if not question:
        raise HTTPException(404, "Unknown question_id.")
    correct = _answer_matches(body.answer, question["correct_answer"], question["options"])
    db.save_quiz_attempt(user_id, question_id, body.answer, correct)
    return {
        "result": "Correct!" if correct else "Wrong!",
        "correct_answer": _option_for_letter(question["options"], question["correct_answer"]),
        "explanation": question["explanation"],
    }


@router.get("/study/list")
def study_list(category: str | None = None):
    if category in (None, "", "Comprehensive"):
        category = None
    rows = db.list_articles(category)
    return [
        {
            "id": str(row["id"]),
            "title": row["title"],
            "category": row["category"],
            "content": row["content"],
            "image": row["image"] or "",
        }
        for row in rows
    ]
