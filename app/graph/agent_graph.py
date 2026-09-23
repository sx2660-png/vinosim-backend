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

CORRECTION_SYSTEM = (
    "You are VinoSim, a warm, precise sommelier tutor for beginners. "
    "Answer the user's (often vague) wine question using ONLY the provided knowledge snippets "
    "as your factual basis. If the snippets do not cover it, say so honestly and give general "
    "guidance without inventing specifics. Keep it approachable and jargon-light. "
    "List the titles of the snippets you actually used in `sources`."
)

ROLEPLAY_SYSTEM = (
    "You are role-playing as a charismatic sommelier at a cozy wine bar, chatting with a guest. "
    "Stay in character, be vivid and encouraging, and keep replies conversational."
)


def load_history(state: AgentState) -> AgentState:
    history = db.load_chat_history(state["user_id"], state["mode"], limit=10)
    return {"history": history}


def route_by_mode(state: AgentState) -> str:
    """The IF node: correction has a knowledge tool, roleplay does not."""
    return "correction" if state.get("mode") == "correction" else "roleplay"


def retrieve(state: AgentState) -> AgentState:
    """PGVector similarity search over wine_docs."""
    q_emb = llm.embed(state["message"], task_type="RETRIEVAL_QUERY")
    docs = db.similarity_search(q_emb, k=settings.rag_top_k)
    return {"retrieved": docs}


def correction_agent(state: AgentState) -> AgentState:
    docs = state.get("retrieved", [])
    context = "\n\n".join(f"[{d['title']}]\n{d['content']}" for d in docs) or "(no snippets found)"
    user_message = (
        f"Knowledge snippets:\n{context}\n\n"
        f"User question: {state['message']}"
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
        user_message=state["message"],
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


def run_agent(user_id: str, mode: str, message: str) -> dict:
    graph = build_graph()
    final = graph.invoke({"user_id": user_id, "mode": mode, "message": message})
    return final["response"]
