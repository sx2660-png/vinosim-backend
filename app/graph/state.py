"""Shared state passed between LangGraph nodes for the Flow-2 agent."""
from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # inputs
    user_id: str
    mode: str          # 'correction' | 'roleplay'
    message: str
    # working memory
    history: list[dict[str, str]]
    retrieved: list[dict[str, Any]]
    # output
    response: dict[str, Any]
