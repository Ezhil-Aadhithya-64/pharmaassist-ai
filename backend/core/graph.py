"""
LangGraph pipeline with MemorySaver checkpointing.
Canonical location: backend/core/graph.py

Flow:
  session_manager → intent_node → decision_node
                                      ├─ action_node   (cancel/refund/modify — tool calling)
                                      ├─ tool_node     (track/account/history — read-only)
                                      ├─ rag_node      (policy questions)
                                      ├─ response_node (general queries)
                                      ├─ clarification_node
                                      └─ escalation_node
  all branches → memory_updater → END
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.state.schema import AgentState
from backend.pipeline.nodes.system.session_manager import session_manager
from backend.pipeline.nodes.system.tool_node import tool_node
from backend.pipeline.nodes.system.escalation_node import escalation_node
from backend.pipeline.nodes.system.memory_updater import memory_updater
from backend.pipeline.nodes.action.action_node import action_node
from backend.pipeline.nodes.intent.intent_node import intent_node
from backend.pipeline.nodes.decision.decision_node import decision_node
from backend.pipeline.nodes.response.response_node import response_node
from backend.pipeline.nodes.clarification.clarification_node import clarification_node
from backend.pipeline.nodes.rag.rag_node import rag_node


def build_graph():
    graph = StateGraph(AgentState)

    # ── register nodes ────────────────────────────────────────────────────────
    graph.add_node("session_manager",    session_manager)
    graph.add_node("intent_node",        intent_node)
    graph.add_node("action_node",        action_node)
    graph.add_node("tool_node",          tool_node)
    graph.add_node("rag_node",           rag_node)
    graph.add_node("response_node",      response_node)
    graph.add_node("clarification_node", clarification_node)
    graph.add_node("escalation_node",    escalation_node)
    graph.add_node("memory_updater",     memory_updater)

    # ── edges ─────────────────────────────────────────────────────────────────
    graph.set_entry_point("session_manager")
    graph.add_edge("session_manager", "intent_node")

    graph.add_conditional_edges(
        "intent_node",
        decision_node,
        {
            "action_node":        "action_node",
            "tool_node":          "tool_node",
            "rag_node":           "rag_node",
            "response_node":      "response_node",
            "clarification_node": "clarification_node",
            "escalation_node":    "escalation_node",
        },
    )

    graph.add_edge("action_node",        "response_node")
    graph.add_edge("tool_node",          "response_node")
    graph.add_edge("rag_node",           "response_node")
    graph.add_edge("response_node",      "memory_updater")
    graph.add_edge("clarification_node", "memory_updater")
    graph.add_edge("escalation_node",    "memory_updater")
    graph.add_edge("memory_updater",     END)

    return graph.compile(checkpointer=MemorySaver())
