"""
action_node — LangGraph Tool Calling pattern for WRITE operations.
Canonical location: backend/pipeline/nodes/action/action_node.py
"""
import json
import os

import backend.core.config as _cfg  # noqa: F401 — ensures .env is loaded
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from backend.state.schema import AgentState
from backend.core.security import validate_order_access, is_admin, normalize_order_id, find_similar_order_ids
from backend.tools.db_tools import (
    process_refund,
    cancel_order,
    modify_order,
    escalate_to_human,
    send_customer_email,
    ACTION_TOOLS,
)

_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0,
)
_llm_with_tools = _llm.bind_tools(ACTION_TOOLS)

SYSTEM = """You are an action execution agent for a pharmacy ecommerce platform.
Your job is to execute the correct WRITE action based on the user's intent and entities.

Available tools:
- cancel_order(order_id): Cancel a pending or shipped order
- process_refund(order_id): Initiate refund for a delivered/returned order
- modify_order(order_id, updated_products): Update product quantities in an order
- escalate_to_human(customer_id, order_id, reason): Escalate to human agent
- send_customer_email(customer_id, subject, body): Send notification email to customer

Rules:
- Call EXACTLY ONE primary action tool matching the intent:
  * request_refund → process_refund ONLY (never cancel_order)
  * cancel_order   → cancel_order ONLY (never process_refund)
  * modify_order   → modify_order ONLY
  * escalate       → escalate_to_human ONLY
- After the primary action succeeds AND customer_id is available (non-empty string),
  also call send_customer_email to notify the customer
- If customer_id is missing or empty, skip send_customer_email entirely
- Never call both cancel_order and process_refund in the same turn
- Never fabricate IDs or data
- Execute immediately — do not ask for confirmation
"""

_TOOL_MAP = {
    "cancel_order":        cancel_order,
    "process_refund":      process_refund,
    "modify_order":        modify_order,
    "escalate_to_human":   escalate_to_human,
    "send_customer_email": send_customer_email,
}


def action_node(state: AgentState) -> AgentState:
    intent          = state.get("intent", "")
    entities        = state.get("entities", {}) or {}
    order_id        = entities.get("order_id", "")
    customer_id     = entities.get("customer_id", "")
    product_updates = entities.get("product_updates") or []
    user_input      = state.get("user_input", "")
    session_id      = state.get("session_id", "unknown")

    auth_customer_id = state.get("customer_id")

    # Normalize order ID format (ORD000039 -> ORD00039)
    if order_id:
        normalized_order_id = normalize_order_id(order_id)
        if normalized_order_id != order_id:
            print(f"[action_node] normalized order_id: {order_id} -> {normalized_order_id}")
            order_id = normalized_order_id
            entities["order_id"] = order_id

    print(f"[action_node] intent={intent} order_id={order_id} customer_id={customer_id} is_admin={is_admin(auth_customer_id)}")

    # Ownership check for write actions on orders
    # CRITICAL: Customers can only modify their own orders, admins can modify any
    if not is_admin(auth_customer_id) and order_id:
        try:
            from backend.tools.db_tools import get_conn
            import psycopg2.extras
            with get_conn() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT customer_id FROM orders WHERE order_id = %s", (order_id,))
                    row = cur.fetchone()
                    if row:
                        allowed, error_msg = validate_order_access(
                            auth_customer_id=auth_customer_id,
                            order_id=order_id,
                            order_owner_id=row["customer_id"],
                            action=f"modify_order_{intent}",
                            session_id=session_id
                        )
                        if not allowed:
                            state["tool_result"]       = {"status": "access_denied", "data": {"message": error_msg}}
                            state["action_taken"]      = "none"
                            state["resolution_status"] = "pending"
                            return state
        except Exception as e:
            print(f"[action_node] ownership check error: {e}")

    action_request = (
        f"Intent: {intent}\n"
        f"Order ID: {order_id or 'not provided'}\n"
        f"Customer ID: {customer_id or 'not provided'}\n"
        f"Product updates: {json.dumps(product_updates) if product_updates else 'none'}\n"
        f"Session ID: {state.get('session_id', '')}\n"
        f"User message: {user_input}\n\n"
        "Call the appropriate tool now."
    )

    messages = [
        SystemMessage(content=SYSTEM),
        HumanMessage(content=action_request),
    ]

    try:
        response = _llm_with_tools.invoke(messages)
    except Exception as e:
        print(f"[action_node] LLM error: {e}")
        state["tool_result"]       = {"status": "error", "data": {"message": str(e)}}
        state["action_taken"]      = "error"
        state["resolution_status"] = "pending"
        return state

    tool_calls = getattr(response, "tool_calls", []) or []
    state["tool_calls"] = tool_calls

    if not tool_calls:
        print(f"[action_node] no tool call returned — content: {response.content[:100]}")
        state["tool_result"]       = {"status": "error", "data": {"message": "Action could not be determined. Please rephrase your request."}}
        state["action_taken"]      = "none"
        state["resolution_status"] = "pending"
        return state

    last_result    = {}
    primary_result = {}
    primary_tool   = ""

    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]

        print(f"[action_node] executing tool={tool_name} args={tool_args}")

        if tool_name == "send_customer_email":
            cid = tool_args.get("customer_id", "")
            if not cid or cid.strip() == "":
                print("[action_node] skipping send_customer_email — no customer_id")
                continue

        tool_fn = _TOOL_MAP.get(tool_name)
        if not tool_fn:
            print(f"[action_node] unknown tool: {tool_name}")
            continue

        try:
            result = tool_fn.invoke(tool_args)
            print(f"[action_node] {tool_name} result={str(result)[:200]}")
        except Exception as e:
            print(f"[action_node] {tool_name} execution error: {e}")
            result = {"status": "error", "data": {"message": str(e)}}

        if not isinstance(result, dict):
            result = {"status": "success", "data": result}
        if "status" not in result:
            result = {"status": "success", "data": result}

        last_result = result

        if tool_name != "send_customer_email":
            primary_result = result
            primary_tool   = tool_name

        data = result.get("data", {})
        if isinstance(data, dict) and data.get("escalation_status") == "queued_for_human":
            state["escalation_package"] = data
            state["resolution_status"]  = "escalated"
            state["action_taken"]       = "escalated"

    final_result = primary_result if primary_result else last_result
    final_tool   = primary_tool   if primary_tool   else (tool_calls[-1]["name"] if tool_calls else "")

    state["tool_result"] = final_result

    # Handle order not found with helpful suggestions
    if final_result.get("status") == "error":
        error_msg = final_result.get("data", {}).get("message", "")
        if "not found" in error_msg.lower() and order_id:
            # Try to find similar order IDs
            similar_ids = find_similar_order_ids(order_id, auth_customer_id)
            if similar_ids:
                suggestion = f"Order {order_id} not found. "
                if len(similar_ids) == 1 and similar_ids[0] != order_id:
                    suggestion += f"Did you mean {similar_ids[0]}?"
                else:
                    suggestion += f"Your recent orders: {', '.join(similar_ids[:3])}"
                state["tool_result"] = {
                    "status": "error",
                    "data": {"message": suggestion}
                }
                print(f"[action_node] order not found, suggested: {similar_ids}")

    if not state.get("action_taken"):
        data         = final_result.get("data", {})
        action_taken = ""
        if isinstance(data, dict):
            action_taken = data.get("action", "") or final_tool

        if final_result.get("status") == "success":
            state["resolution_status"] = "resolved"
        else:
            state["resolution_status"] = "pending"

        state["action_taken"] = action_taken or final_tool

    # Auto-send email if primary action succeeded and no email was sent
    if (
        final_result.get("status") == "success"
        and primary_tool in {"cancel_order", "process_refund", "modify_order"}
        and not any(tc["name"] == "send_customer_email" for tc in tool_calls)
    ):
        derived_customer_id = customer_id
        if not derived_customer_id and order_id:
            try:
                from backend.tools.db_tools import get_conn
                import psycopg2.extras
                with get_conn() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                        cur.execute("SELECT customer_id FROM orders WHERE order_id = %s", (order_id,))
                        row = cur.fetchone()
                        if row:
                            derived_customer_id = row["customer_id"]
            except Exception as e:
                print(f"[action_node] customer_id lookup error: {e}")

        if derived_customer_id:
            data = final_result.get("data", {})
            action_label = data.get("action", primary_tool).replace("_", " ")
            subject = f"Order Update: {action_label.title()} — {order_id}"
            body = (
                f"Dear Customer,\n\n"
                f"Your order {order_id} has been updated.\n"
                f"Action: {action_label}\n"
                f"New Status: {data.get('new_status', 'updated')}\n"
            )
            if data.get("amount"):
                body += f"Amount: ₹{data['amount']}\n"
            if data.get("updates"):
                body += f"Updates: {data['updates']}\n"
            body += "\nThank you for choosing PharmaAssist.\nPharmaAssist AI Team"
            try:
                email_result = send_customer_email.invoke({
                    "customer_id": derived_customer_id,
                    "subject": subject,
                    "body": body,
                })
                print(f"[action_node] auto-email result={str(email_result)[:120]}")
            except Exception as e:
                print(f"[action_node] auto-email error: {e}")

    print(f"[action_node] action_taken={state['action_taken']} resolution={state['resolution_status']}")
    return state
