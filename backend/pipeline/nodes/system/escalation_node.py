"""
escalation_node — graceful human handoff with full context package.
Canonical location: backend/pipeline/nodes/system/escalation_node.py
"""
from backend.state.schema import AgentState
from backend.tools.db_tools import (
    get_order_details,
    get_customer_profile,
    escalate_to_human,
)


def _call(fn, **kwargs) -> dict:
    try:
        result = fn.invoke(kwargs)
        if isinstance(result, dict) and "status" in result:
            return result
        if isinstance(result, dict) and "data" in result:
            return result
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "data": {"message": str(e)}}


def escalation_node(state: AgentState) -> AgentState:
    """
    Graceful human handoff — builds full context package even when
    customer_id or order_id is missing (partial context is better than none).
    """
    entities    = state.get("entities", {})
    order_id    = entities.get("order_id")
    customer_id = entities.get("customer_id")
    memory      = state.get("memory", [])

    print(f"[escalation_node] building handoff — customer={customer_id} order={order_id}")

    transcript = "\n".join(
        f"Customer: {t['user']}\nAgent: {t['agent']}" for t in memory
    )

    handoff = {
        "escalation_status": "queued_for_human",
        "reason": state.get("user_input", "Customer requested escalation"),
        "transcript": transcript,
        "customer": {},
        "order": {},
        "context_note": "",
    }

    if customer_id and order_id:
        result = _call(escalate_to_human,
                       customer_id=customer_id,
                       order_id=order_id,
                       reason=state.get("user_input", ""))
        if result.get("status") == "success":
            handoff.update(result["data"])
    elif customer_id:
        cr = _call(get_customer_profile, customer_id=customer_id)
        if cr.get("status") == "success":
            handoff["customer"] = cr["data"]
        handoff["context_note"] = "No order ID available — customer profile only."
    elif order_id:
        or_ = _call(get_order_details, order_id=order_id)
        if or_.get("status") == "success":
            handoff["order"] = or_["data"]
        handoff["context_note"] = "No customer ID available — order details only."
    else:
        handoff["context_note"] = (
            "No customer ID or order ID provided. "
            "Human agent should identify customer from transcript."
        )

    state["tool_result"]        = {"status": "escalated", "data": handoff}
    state["escalation_package"] = handoff
    state["action_taken"]       = "escalated"
    state["resolution_status"]  = "escalated"
    state["agent_response"] = (
        "I completely understand your frustration, and I'm sorry for the inconvenience. "
        "I'm connecting you with a human agent right now who will have full context of our conversation. "
        "You won't need to repeat yourself. Please hold on."
    )
    print(f"[escalation_node] handoff package ready — context_note={handoff['context_note']!r}")
    return state
