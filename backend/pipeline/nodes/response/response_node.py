"""
response_node — converts structured tool_result into natural language using Groq.
Canonical location: backend/pipeline/nodes/response/response_node.py
"""
import os

import backend.core.config as _cfg  # noqa: F401 — ensures .env is loaded
from groq import Groq
from backend.state.schema import AgentState

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

RESPONSE_MODEL = "llama-3.1-8b-instant"
RAG_MODEL      = "llama-3.3-70b-versatile"

SYSTEM_GROUNDED = (
    "You are a concise pharmacy ecommerce assistant. "
    "Rephrase the structured data below into a clear, friendly response. "
    "Do NOT add, invent, or assume any information not present in the data. "
    "If the data contains an error or not_found message, relay it politely."
)

SYSTEM_GENERAL = (
    "You are a helpful pharmacy ecommerce assistant. "
    "Answer the user's question conversationally. "
    "You can help with order tracking, cancellations, refunds, and pharmacy policy questions. "
    "IMPORTANT: Do NOT invent, assume, or recall order details, product names, quantities, or amounts "
    "from previous conversation turns. Only state facts that are explicitly provided in the current data."
)


def response_node(state: AgentState) -> AgentState:
    user_input  = state.get("user_input", "")
    tool_result = state.get("tool_result", {})
    memory      = state.get("memory", [])
    intent      = state.get("intent", "")

    tool_intents = {"track_order", "cancel_order", "request_refund", "account_status",
                    "modify_order", "order_history"}

    # ── place_order: not supported ───────────────────────────────────────────
    if intent == "place_order":
        state["agent_response"] = (
            "Placing new orders isn't something I can do — I'm a customer service assistant. "
            "I can help you track, cancel, modify, or get a refund on existing orders, "
            "and search for drug availability and pricing. "
            "To place a new order, please visit our website or app."
        )
        print("[response_node] place_order — not supported")
        return state

    # ── low-confidence escalation trigger ────────────────────────────────────
    confidence = state.get("confidence", 1.0)
    if confidence < 0.4 and intent not in ("general_query", "escalate", "check_policy"):
        state["agent_response"] = (
            "I'm not entirely sure I understood your request correctly. "
            "Could you rephrase it, or would you like me to connect you with a human agent?"
        )
        print(f"[response_node] low confidence ({confidence:.2f}) — asking for clarification")
        return state

    # ── handle non-success statuses directly ─────────────────────────────────
    if tool_result:
        status = tool_result.get("status", "")
        data   = tool_result.get("data", {})
        msg    = data.get("message", "") if isinstance(data, dict) else ""

        if status == "not_found":
            state["agent_response"] = msg or "I couldn't find a record for that ID. Please verify and try again."
            return state
        if status == "missing_entity":
            state["agent_response"] = msg or "I need more information to process your request."
            return state
        if status == "rejected":
            state["agent_response"] = msg or "This action cannot be completed for that order."
            return state
        if status == "access_denied":
            state["agent_response"] = msg or "You don't have permission to access that information."
            return state
        if status == "error":
            state["agent_response"] = msg or "Something went wrong while fetching your data. Please try again."
            return state

    # ── tool was expected but returned nothing ────────────────────────────────
    if intent in tool_intents and not tool_result:
        state["agent_response"] = (
            "I wasn't able to retrieve that information from our system. "
            "Please verify the ID and try again."
        )
        print("[response_node] tool intent with no result — blocked LLM")
        return state

    # ── modify_order guard ────────────────────────────────────────────────────
    if intent == "modify_order":
        action = (tool_result.get("data", {}) or {}).get("action")
        if action == "_action_needed":
            order_data = tool_result.get("data", {})
            prompt_msg = order_data.pop("_action_needed", "Please tell me what changes you'd like.")
            state["agent_response"] = (
                f"I found your order. {prompt_msg}\n\n"
                f"Current order details:\n{order_data}"
            )
            return state
        elif action != "order_modified":
            state["agent_response"] = "I wasn't able to modify the order. Please try again with the product name and quantity."
            return state

    # ── safety net: block hallucination for misclassified modify attempts ─────
    if intent == "general_query" and not tool_result:
        lower = user_input.lower()
        modify_signals = ["modify", "change", "update", "increase", "decrease", "set quantity",
                          "products of order", "items in order", "must be increased", "must be decreased"]
        if any(s in lower for s in modify_signals):
            state["agent_response"] = (
                "I want to make sure I process your request correctly. "
                "Could you rephrase it as: \"Modify order ORD00001 — set [product name] to [quantity] units\"?"
            )
            return state

        place_signals = ["place an order", "place order", "order one", "order a ", "buy ", "purchase ",
                         "add to cart", "i want to order", "can you order", "can i order"]
        if any(s in lower for s in place_signals):
            state["agent_response"] = (
                "Placing new orders isn't something I can do — I'm a customer service assistant. "
                "I can help you track, cancel, modify, or get a refund on existing orders, "
                "and search for drug availability and pricing. "
                "To place a new order, please visit our website or app."
            )
            return state

    # ── build LLM messages ────────────────────────────────────────────────────
    rag_context = state.get("rag_context", "")

    if rag_context:
        system = (
            "You are a pharmacy ecommerce assistant. "
            "Answer the user's question strictly based on the provided policy context. "
            "Do not add information not present in the context."
        )
    elif tool_result:
        system = SYSTEM_GROUNDED
    else:
        system = SYSTEM_GENERAL

    messages = [{"role": "system", "content": system}]

    for turn in memory[-10:]:
        messages.append({"role": "user",      "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["agent"]})

    if rag_context:
        user_prompt = (
            f"Policy Context:\n{rag_context}\n\n"
            f"User Question: {user_input}\n\nAnswer:"
        )
    elif tool_result:
        data_section = tool_result.get("data", tool_result)
        user_prompt = (
            f"User Query: {user_input}\n\n"
            f"Data from system:\n{data_section}\n\n"
            "Rephrase this data into a clear, friendly response. "
            "Do NOT add any information not present above."
        )
    else:
        user_prompt = user_input

    messages.append({"role": "user", "content": user_prompt})

    try:
        response = client.chat.completions.create(
            model=RAG_MODEL if rag_context else RESPONSE_MODEL,
            messages=messages,
            temperature=0.3,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[response_node] LLM error: {e}")
        answer = "I'm sorry, I couldn't process your request right now. Please try again."

    state["agent_response"] = answer
    print(f"[response_node] {answer[:100]}")
    return state
