"""
intent_node — classifies user intent and writes results to AgentState.
Canonical location: backend/pipeline/nodes/intent/intent_node.py
"""
from backend.state.schema import AgentState
from backend.pipeline.nodes.intent.intent_classifier import classify_intent


def intent_node(state: AgentState) -> AgentState:
    auth_cid = state.get("customer_id")  # None = admin, string = authenticated customer
    is_admin = auth_cid is None
    
    result = classify_intent(
        user_input=state["user_input"],
        memory=state.get("memory", []),
        auth_customer_id=auth_cid,
    )

    intent   = result["intent"]
    entities = result["entities"]

    # If a customer is authenticated and the intent needs their ID,
    # inject it automatically — never ask them for it, and never allow
    # them to query a different customer's data.
    if auth_cid and intent in {"order_history", "account_status"}:
        entities["customer_id"] = auth_cid
        result["is_valid"] = True
    
    # SECURITY: Prevent customers from attempting to query other customers
    # If a customer tries to specify a different customer_id, override it
    if not is_admin and entities.get("customer_id") and entities["customer_id"] != auth_cid:
        print(f"[intent_node] SECURITY: customer {auth_cid} attempted to query customer {entities['customer_id']} - overriding")
        entities["customer_id"] = auth_cid

    state["intent"]     = intent
    state["confidence"] = result["confidence"]
    state["entities"]   = entities
    state["is_valid"]   = result["is_valid"]

    print(f"[intent_node] {result}")
    return state
