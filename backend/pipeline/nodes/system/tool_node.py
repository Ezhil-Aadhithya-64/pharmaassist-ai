"""
tool_node — READ-ONLY DB lookups: track_order, account_status, order_history, drug_search.
Canonical location: backend/pipeline/nodes/system/tool_node.py
"""
import re
from backend.state.schema import AgentState
from backend.core.security import validate_customer_access, validate_order_access, is_admin
from backend.tools.db_tools import (
    get_order_details,
    get_customer_profile,
    get_order_history,
    search_drugs,
)


def _call(fn, **kwargs) -> dict:
    """Invoke a LangChain @tool and normalise to {status, data}."""
    try:
        result = fn.invoke(kwargs)
        print(f"[_call] {fn.name} raw result type={type(result).__name__} value={str(result)[:200]}")
        if isinstance(result, dict) and "status" in result:
            return result
        if isinstance(result, dict) and "data" in result:
            return result
        return {"status": "success", "data": result}
    except Exception as e:
        print(f"[_call] {fn.name} EXCEPTION: {e}")
        return {"status": "error", "data": {"message": str(e)}}


def tool_node(state: AgentState) -> AgentState:
    """READ-ONLY lookups: track_order, account_status, order_history, drug_search."""
    intent      = state.get("intent", "general_query")
    entities    = state.get("entities", {})
    order_id    = entities.get("order_id")
    customer_id = entities.get("customer_id")
    session_id  = state.get("session_id", "unknown")

    # The authenticated customer from login — None means admin (full access)
    auth_customer_id = state.get("customer_id")
    
    print(f"[tool_node] intent={intent} order_id={order_id} customer_id={customer_id} is_admin={is_admin(auth_customer_id)}")

    if intent == "track_order" and not order_id:
        state["tool_result"] = {"status": "missing_entity", "data": {"message": "Please provide your order ID."}}
        return state

    # For customer-specific intents, enforce proper customer_id
    if intent in {"account_status", "order_history"} and not customer_id:
        if is_admin(auth_customer_id):
            # Admin must explicitly specify which customer to query
            state["tool_result"] = {"status": "missing_entity", "data": {"message": "Please provide a customer ID."}}
            return state
        else:
            # Customer users: auto-inject their own customer_id
            customer_id = auth_customer_id
            print(f"[tool_node] auto-injected customer_id={customer_id} for authenticated customer")

    if intent == "track_order":
        result = _call(get_order_details, order_id=order_id)
        # Access control: customers can only view their own orders
        if not is_admin(auth_customer_id) and result.get("status") == "success":
            order_owner = result["data"].get("customer_id")
            allowed, error_msg = validate_order_access(
                auth_customer_id=auth_customer_id,
                order_id=order_id,
                order_owner_id=order_owner,
                action="view_order",
                session_id=session_id
            )
            if not allowed:
                state["tool_result"] = {
                    "status": "access_denied",
                    "data": {"message": error_msg}
                }
                return state

    elif intent == "order_history":
        # Access control: customers can only view their own history
        allowed, error_msg = validate_customer_access(
            auth_customer_id=auth_customer_id,
            target_customer_id=customer_id,
            action="view_order_history",
            session_id=session_id
        )
        if not allowed:
            state["tool_result"] = {
                "status": "access_denied",
                "data": {"message": error_msg}
            }
            return state
        result = _call(get_order_history, customer_id=customer_id)

    elif intent == "account_status":
        # Access control: customers can only view their own account
        allowed, error_msg = validate_customer_access(
            auth_customer_id=auth_customer_id,
            target_customer_id=customer_id,
            action="view_customer_profile",
            session_id=session_id
        )
        if not allowed:
            state["tool_result"] = {
                "status": "access_denied",
                "data": {"message": error_msg}
            }
            return state
        result = _call(get_customer_profile, customer_id=customer_id)

    elif intent == "drug_search":
        entities_drug = entities.get("drug_name") or entities.get("query")
        if entities_drug:
            query = entities_drug
        else:
            raw = state.get("user_input", "")
            query = re.sub(
                r"(?i)^(search\s+(for\s+)?|find\s+|look\s+up\s+|do\s+you\s+have\s+|"
                r"is\s+.+\s+available\??|what\s+is\s+the\s+price\s+of\s+|"
                r"how\s+much\s+(does\s+)?|show\s+me\s+|get\s+me\s+|"
                r"search\s+for\s+.+\s+in\s+drug[s]?\s*)",
                "", raw
            ).strip().rstrip("?")
        result = _call(search_drugs, query=query)
        print(f"[tool_node] drug_search query={query!r}")

    else:
        result = {"status": "no_tool", "data": {}}

    state["tool_result"] = result
    print(f"[tool_node] status={result.get('status')} data={str(result.get('data',''))[:120]}")
    return state
