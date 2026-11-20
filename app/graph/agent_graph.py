"""LangGraph StateGraph reproducing the n8n Flow-2 "AI agent" (correction / roleplay).

n8n node               -> LangGraph node
---------------------------------------------------
Select Chat History    -> load_history
IF (mode)              -> conditional edge `route_by_mode`
correction agent       -> retrieve + correction_agent  (uses pgvector store)
roleplay agent         -> roleplay_agent
Update Database        -> persist
Respond to Webhook     -> graph output
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from .. import db, llm
from ..config import settings
from ..schemas import CorrectionResponse, RoleplayResponse
from .state import AgentState

# Both prompts aim at confidence: specific praise for what the learner actually did, then at
# most one small next step. Generic praise is avoided because adults see through it and it
# makes the tutor's later comments mean less.
CORRECTION_SYSTEM = (
    "You are VinoSim, a warm tutor helping a beginner put words to a glass of wine. The goal is "
    "that they leave each exchange a little more sure they can describe wine in their own words.\n"
    "Base facts on the provided knowledge snippets. If they do not cover the question, give "
    "general beginner guidance (the standard WSET tasting words are fine) without inventing "
    "specifics about a particular wine.\n"
    "How to respond:\n"
    "- Start from what the learner wrote or said. When they have described something, quote a "
    "word or two of theirs and say specifically what is useful about it (for example, \"mouth-"
    "watering\" is exactly the feeling people call acidity). Praise what they did, never the "
    "person, and skip empty words like amazing, perfect, excellent or great job.\n"
    "- Then give at most one next step, framed as something they could try or add, not as "
    "something they got wrong.\n"
    "- Smell, flavour and whether the learner likes the wine have no wrong answers. Never tell "
    "them an aroma, flavour or preference is wrong, and never say what this wine should smell or "
    "taste like. Offer words other people often use (\"Many people describe that as ...; others "
    "say ...\").\n"
    "- For structure (acidity, tannin, body, sweetness, alcohol), help link what they feel to one "
    "word, say where in the mouth it is felt, and give one simple reason (for example, tannin "
    "comes from grape skins and seeds, which is why red wines have more of it). If they used a "
    "word that does not fit the feeling they describe, show the better match gently, starting "
    "with the part they got right.\n"
    "- \"Dry\" has two meanings: in wine it usually means not sweet, while a drying, rough "
    "feeling on the gums is tannin. If the learner says dry, briefly cover both or ask which "
    "they mean.\n"
    "- When the learner is unsure or apologetic, tell them that noticing the feeling is the "
    "hard part and the word comes with practice.\n"
    "- Ask at most one question at a time. Keep the whole reply under 80 words, calm rather "
    "than gushing (no exclamation marks), and jargon-light.\n"
    "- Never recommend wines to buy, mention prices, or hand the learner a line to memorize.\n"
    "- Write plain text: no Markdown, asterisks or bullet symbols.\n"
    "- Never mention snippets, sources, a knowledge base or what you were given. Speak as a "
    "tutor who simply knows; the learner does not see the snippets.\n"
    "List the titles of the snippets you actually used in `sources`."
)

ROLEPLAY_SYSTEM = (
    "You are a friendly guest sitting next to the learner at a dinner where wine has just been "
    "poured. Chat naturally and ask what they notice about the wine, so they can practise saying "
    "a sentence or two about it in their own words. React with real interest to what they say, "
    "picking up their own words; if they use a word like acidity, tannin or body, show you "
    "understood and that it helped you picture the wine. If they hesitate, make it easy: share a "
    "simple impression of your own and ask what they think. Never say their impression is wrong "
    "and never quiz them. Do not recommend wines, mention prices, or lecture. Keep replies to two "
    "or three sentences. Write plain text without Markdown."
)

# Where the learner is on the four-line tasting sheet (scaffolding, one step at a time).
STEP_GUIDE = {
    "appearance": "The learner is on the APPEARANCE line: colour and how deep it looks.",
    "nose": "The learner is on the NOSE line: what kinds of smells they notice. There is no wrong answer.",
    "palate": (
        "The learner is on the PALATE line: how it feels in the mouth. Help them tie one feeling to "
        "a word (mouth-watering = acidity, drying gums = tannin, weight = body) and give one reason."
    ),
    "liking": "The learner is on the LAST line: whether they like it and why. There is no wrong answer.",
}


def _step_note(state: AgentState) -> str:
    note = STEP_GUIDE.get(state.get("step") or "")
    return f"\n\n({note} Help only with this line.)" if note else ""


def load_history(state: AgentState) -> AgentState:
    history = db.load_chat_history(state["user_id"], state["mode"], limit=10)
    return {"history": history, "sheet_note": _sheet_note(state)}


def route_by_mode(state: AgentState) -> str:
    """The IF node: correction has a knowledge tool, roleplay does not."""
    return "correction" if state.get("mode") == "correction" else "roleplay"


def _sheet_note(state: AgentState) -> str:
    """A saved sheet the learner wants to talk about (the "talk more" button)."""
    sheet_id = state.get("sheet_id")
    sheet = db.get_sheet(state["user_id"], sheet_id) if sheet_id else None
    if not sheet:
        return ""
    palate = sheet["palate"] + (f" (because {sheet['palate_because']})" if sheet["palate_because"] else "")
    return (
        "\n\nThe learner's saved tasting sheet, which they want to talk about:\n"
        f"Wine: {sheet['wine_name'] or '(not named)'}\n"
        f"Appearance: {sheet['appearance'] or '(empty)'}\n"
        f"Nose: {sheet['nose'] or '(empty)'}\n"
        f"Palate: {palate or '(empty)'}\n"
        f"Liking: {sheet['liking'] or '(empty)'}"
    )


def retrieve(state: AgentState) -> AgentState:
    """PGVector similarity search over wine_docs."""
    query = state["message"] + state.get("sheet_note", "")
    q_emb = llm.embed(query, task_type="RETRIEVAL_QUERY")
    docs = db.similarity_search(q_emb, k=settings.rag_top_k)
    return {"retrieved": docs}


def correction_agent(state: AgentState) -> AgentState:
    docs = state.get("retrieved", [])
    context = "\n\n".join(f"[{d['title']}]\n{d['content']}" for d in docs) or "(no snippets found)"
    user_message = (
        f"Knowledge snippets:\n{context}\n\n"
        f"User question: {state['message']}"
        f"{state.get('sheet_note', '')}"
        f"{_step_note(state)}"
    )
    result = llm.structured_chat(
        system=CORRECTION_SYSTEM,
        history=state.get("history", []),
        user_message=user_message,
        schema=CorrectionResponse,
    )
    payload = result.model_dump()
    payload["retrieved_titles"] = [d["title"] for d in docs]
    return {"response": payload}


def roleplay_agent(state: AgentState) -> AgentState:
    result = llm.structured_chat(
        system=ROLEPLAY_SYSTEM,
        history=state.get("history", []),
        user_message=state["message"] + state.get("sheet_note", "") + _step_note(state),
        schema=RoleplayResponse,
        temperature=0.8,
    )
    return {"response": result.model_dump()}


def persist(state: AgentState) -> AgentState:
    """Update Database: store the user turn and the assistant turn."""
    resp = state.get("response", {})
    assistant_text = resp.get("answer") or resp.get("reply") or ""
    db.save_turn(state["user_id"], state["mode"], "user", state["message"])
    db.save_turn(state["user_id"], state["mode"], "assistant", assistant_text)
    return {}


@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(AgentState)
    g.add_node("load_history", load_history)
    g.add_node("retrieve", retrieve)
    g.add_node("correction_agent", correction_agent)
    g.add_node("roleplay_agent", roleplay_agent)
    g.add_node("persist", persist)

    g.add_edge(START, "load_history")
    g.add_conditional_edges(
        "load_history",
        route_by_mode,
        {"correction": "retrieve", "roleplay": "roleplay_agent"},
    )
    g.add_edge("retrieve", "correction_agent")
    g.add_edge("correction_agent", "persist")
    g.add_edge("roleplay_agent", "persist")
    g.add_edge("persist", END)
    return g.compile()


def run_agent(user_id: str, mode: str, message: str, step: str | None = None,
              sheet_id: int | None = None) -> dict:
    graph = build_graph()
    final = graph.invoke({"user_id": user_id, "mode": mode, "message": message, "step": step,
                          "sheet_id": sheet_id})
    return final["response"]
