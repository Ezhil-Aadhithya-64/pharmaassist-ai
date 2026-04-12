"""
Shared state schema passed through the LangGraph pipeline.
Canonical location: backend/state/schema.py

Uses Annotated reducers so LangGraph MemorySaver merges list fields
correctly across turns instead of overwriting them.
"""
from typing import Any, Optional, Annotated
from typing_extensions import TypedDict
import operator


class AgentState(TypedDict, total=False):
    # ── core ──────────────────────────────────────────────────────────────────
    session_id:     str
    customer_id:    Optional[str]   # authenticated customer (None = admin/unauthenticated)
    user_input:     str
    tool_result:    dict[str, Any]
    agent_response: str
    # memory uses operator.add so each turn's entry is APPENDED, never lost
    memory:         Annotated[list[dict[str, str]], operator.add]
    summary:        str
    # ── intent classification ─────────────────────────────────────────────────
    intent:         Optional[str]
    confidence:     float
    entities:       dict[str, Any]
    is_valid:       bool
    rag_context:    str
    escalation_package: dict[str, Any]
    # ── action tracking ───────────────────────────────────────────────────────
    action_taken:       str          # e.g. "order_cancelled", "refund_initiated"
    resolution_status:  str          # "resolved", "escalated", "pending"
    tool_calls:         list[dict]   # raw tool call records from action_node
    session_logged:     bool         # True once this session has been written to DB
