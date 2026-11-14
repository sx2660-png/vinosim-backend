"""FastAPI app: the 6 n8n webhook flows re-implemented as local HTTP endpoints.

n8n webhook                     -> endpoint
--------------------------------------------------------
Flow 1  Webhook Scan            -> POST /scan            (Gemini Vision OCR)
Flow 2  Webhook2 (AI agent)     -> POST /agent           (LangGraph: correction/roleplay)
Flow 3  Webhook Get Quiz        -> GET  /quiz
Flow 4  Webhook Submit          -> POST /quiz/submit
Flow 5  Webhook Get Quiz1       -> POST /label/decode    (Gemini quiz from an image)
Flow 6  Webhook Study           -> GET  /articles
"""
from __future__ import annotations

import base64
from pathlib import Path

from fastapi import BackgroundTasks, Body, FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, llm
from .config import settings
from .graph.agent_graph import run_agent
from .profile import distill_turn
from .public_api import router as public_router
from .schemas import AgentRequest, QuizSubmit, WineLabel

app = FastAPI(title="VinoSim (local)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(public_router)

LABEL_PROMPT = (
    "Read this wine label and extract the fields. Leave a field blank if it is not legible. "
    "Do not guess beyond what is printed."
)


def _model_failure(exc: Exception) -> HTTPException:
    text = str(exc)
    if "API key not valid" in text or "API_KEY_INVALID" in text:
        return HTTPException(502, "Gemini rejected the API key configured on this server.")
    return HTTPException(502, "The model request failed.")


@app.get("/health")
def health():
    return {"ok": True, "chat_model": settings.chat_model}


# --- Flow 1: OCR ---
@app.post("/scan")
async def scan(file: UploadFile | None = None, image_base64: str | None = Body(default=None, embed=True)):
    if file is not None:
        data = await file.read()
        mime = file.content_type or "image/jpeg"
    elif image_base64:
        data = base64.b64decode(image_base64)
        mime = "image/jpeg"
    else:
        raise HTTPException(400, "Provide a multipart `file` or a base64 `image_base64`.")
    try:
        label = llm.vision_extract(data, mime, LABEL_PROMPT, WineLabel)
    except Exception as exc:
        raise _model_failure(exc) from exc
    return label.model_dump()


# --- Flow 2: AI agent (LangGraph) ---
@app.post("/agent")
def agent(req: AgentRequest, background: BackgroundTasks):
    if req.mode not in ("correction", "roleplay"):
        raise HTTPException(400, "mode must be 'correction' or 'roleplay'")
    try:
        result = run_agent(req.user_id, req.mode, req.message)
    except Exception as exc:
        raise _model_failure(exc) from exc
    background.add_task(
        distill_turn,
        req.user_id,
        req.mode,
        req.message,
        result.get("answer") or result.get("reply") or "",
        result.get("retrieved_titles") or result.get("sources") or [],
    )
    return result


@app.get("/agent/history")
def agent_history(user_id: str, mode: str = "correction"):
    if mode not in ("correction", "roleplay"):
        raise HTTPException(400, "mode must be 'correction' or 'roleplay'")
    return {"messages": db.load_chat_history(user_id, mode, limit=20)}


# --- Flow 3: get a random quiz question ---
@app.get("/quiz")
def quiz():
    q = db.random_question()
    if not q:
        raise HTTPException(404, "No questions seeded.")
    return q


# --- Flow 4: submit answer, score it, store history ---
@app.post("/quiz/submit")
def quiz_submit(sub: QuizSubmit):
    q = db.get_question(sub.question_id)
    if not q:
        raise HTTPException(404, "Unknown question_id.")
    is_correct = sub.answer.strip().upper() == q["correct_answer"].strip().upper()
    db.save_quiz_attempt(sub.user_id, sub.question_id, sub.answer, is_correct)
    score = db.user_score(sub.user_id)
    return {
        "correct": is_correct,
        "correct_answer": q["correct_answer"],
        "explanation": q["explanation"],
        "score": score,
    }


# --- Flow 5: label decoder — generate a quiz question from an image ---
class LabelQuiz(BaseModel):
    question: str
    options: list[str] = Field(min_length=2)
    correct_answer: str
    explanation: str


@app.post("/label/decode")
async def label_decode(file: UploadFile | None = None, image_base64: str | None = Body(default=None, embed=True)):
    if file is not None:
        data = await file.read()
        mime = file.content_type or "image/jpeg"
    elif image_base64:
        data = base64.b64decode(image_base64)
        mime = "image/jpeg"
    else:
        raise HTTPException(400, "Provide a multipart `file` or a base64 `image_base64`.")
    prompt = (
        "Look at this wine label and write ONE multiple-choice question (4 options) that tests "
        "whether a learner understood something visible on the label. Give the correct option "
        "and a one-sentence explanation."
    )
    try:
        quiz = llm.vision_extract(data, mime, prompt, LabelQuiz)
    except Exception as exc:
        raise _model_failure(exc) from exc
    return quiz.model_dump()


# --- Flow 6: study articles ---
@app.get("/articles")
def articles(category: str | None = None, user_id: str | None = None):
    return {"articles": db.list_articles(category, user_id)}


@app.get("/learner/profile")
def learner_profile(user_id: str):
    profile = db.get_learner_profile(user_id)
    if profile:
        return profile
    return {"user_id": user_id, "weak_topics": {}, "mentioned_topics": {}, "summaries": []}


# The web client lives in web/. Study and quiz images are root-relative `/media/...`
# paths, and the production build is served from this same process so one host is the app.
_WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
_MEDIA_DIR = _WEB_ROOT / "public" / "media"
_DIST_DIR = _WEB_ROOT / "dist"

if _MEDIA_DIR.is_dir():
    app.mount("/media", StaticFiles(directory=str(_MEDIA_DIR)), name="media")

_ASSETS_DIR = _DIST_DIR / "assets"
if _ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="web-assets")

_INDEX = _DIST_DIR / "index.html"
if _INDEX.is_file():

    @app.get("/", include_in_schema=False)
    def web_app():
        return FileResponse(_INDEX)
