"""
clarification_node — asks the user for missing required entities, or recovers them from memory.
Canonical location: backend/pipeline/nodes/clarification/clarification_node.py
"""
import re
from backend.state.schema import AgentState

_CUSTOMER_INTENTS = {"account_status", "order_history"}
_ORDER_INTENTS    = {"track_order", "cancel_order", "request_refund", "modify_order"}

_ORD_PATTERN = re.compile(r'\bORD\d+\b', re.IGNORECASE)
_CID_PATTERN = re.compile(r'\b[A-Z]{2}\d{4}\b')


def _scan_memory(memory: list, pattern: re.Pattern) -> str | None:
    """Scan both user and agent text in recent turns, newest first."""
    for turn in reversed(memory[-5:]):
        for text in (turn.get("agent", ""), turn.get("user", "")):
            m = pattern.search(text)
            if m:
                return m.group(0).upper()
    return None


def clarification_node(state: AgentState) -> AgentState:
    intent   = state.get("intent", "unknown")
    entities = dict(state.get("entities") or {})
    memory   = state.get("memory", [])
    label    = intent.replace("_", " ")

    # ── try to recover missing entities from memory ───────────────────────────
    recovered = False

    if intent in _ORDER_INTENTS and not entities.get("order_id"):
        found = _scan_memory(memory, _ORD_PATTERN)
        if found:
            entities["order_id"] = found
            state["entities"]    = entities
            state["is_valid"]    = True
            recovered            = True
            print(f"[clarification_node] recovered order_id={found} from memory")

    if intent in _CUSTOMER_INTENTS and not entities.get("customer_id"):
        found = _scan_memory(memory, _CID_PATTERN)
        if found:
            entities["customer_id"] = found
            state["entities"]       = entities
            state["is_valid"]       = True
            recovered               = True
            print(f"[clarification_node] recovered customer_id={found} from memory")

    if recovered:
        if intent in {"cancel_order", "request_refund", "modify_order"}:
            from backend.pipeline.nodes.action.action_node import action_node
            state = action_node(state)
        else:
            from backend.pipeline.nodes.system.tool_node import tool_node
            state = tool_node(state)
        from backend.pipeline.nodes.response.response_node import response_node
        state = response_node(state)
        return state

    # ── nothing recoverable — ask the user ────────────────────────────────────
    if intent in _CUSTOMER_INTENTS:
        msg = (
            f"To look up your {label}, I need your customer ID "
            "(e.g. QA0001, AH0001). Could you please provide it?"
        )
    elif intent in _ORDER_INTENTS:
        msg = (
            f"To process your {label} request, I need your order ID "
            "(e.g. ORD00001). Could you please provide it?"
        )
    else:
        msg = "Could you please provide more details so I can help you?"

    state["agent_response"] = msg
    state["tool_result"]    = {}
    print(f"[clarification_node] intent={intent} — asked for missing entity")
    return state
