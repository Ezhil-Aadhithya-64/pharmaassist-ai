"""
decision_node — routing function for LangGraph conditional edges.
Canonical location: backend/pipeline/nodes/decision/decision_node.py
"""
from backend.state.schema import AgentState

ACTION_INTENTS   = {"cancel_order", "request_refund", "modify_order"}
LOOKUP_INTENTS   = {"track_order", "account_status", "order_history", "drug_search"}
POLICY_INTENTS   = {"check_policy"}
ESCALATE_INTENTS = {"escalate"}


def decision_node(state: AgentState) -> str:
    intent   = state.get("intent", "general_query")
    is_valid = state.get("is_valid", True)

    if not is_valid:
        return "clarification_node"

    if intent in ACTION_INTENTS:
        return "action_node"

    if intent in LOOKUP_INTENTS:
        return "tool_node"

    if intent == "place_order":
        return "response_node"

    if intent in POLICY_INTENTS:
        return "rag_node"

    if intent in ESCALATE_INTENTS:
        return "escalation_node"

    return "response_node"
