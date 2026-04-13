"""
LLM-based intent classification using Groq.
Canonical location: backend/pipeline/nodes/intent/intent_classifier.py
"""
import json
import os
import re as _re

import backend.core.config as _cfg  # noqa: F401 — ensures .env is loaded
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CLASSIFIER_MODEL = "llama-3.3-70b-versatile"

VALID_INTENTS = {
    "track_order",
    "cancel_order",
    "request_refund",
    "modify_order",
    "order_history",
    "check_policy",
    "general_query",
    "escalate",
    "account_status",
    "drug_search",
    "place_order",
}

ORDER_REQUIRED    = {"cancel_order", "request_refund", "track_order", "modify_order"}
CUSTOMER_REQUIRED = {"account_status", "order_history"}

SYSTEM_PROMPT = """You are an intent classification engine for a pharmacy ecommerce assistant.

Classify the user query into exactly one of these intents:

- track_order    : user wants to track or check the status of a specific order
                   Examples: "where is my order ORD00001", "status of ORD00002"

- cancel_order   : user wants to cancel a specific order
                   Examples: "cancel order ORD00001", "I want to cancel ORD00002"

- request_refund : user wants a refund for a specific order
                   Examples: "refund for ORD00001", "I want my money back for ORD00002"

- modify_order   : user wants to change, update, or modify the products/items/quantities in a specific order.
                   This includes ANY phrasing that involves changing what is in an order.
                   Examples:
                     "change my order ORD00001"
                     "modify ORD00002"
                     "update items in ORD00003"
                     "increase Otomize Ear Spray to 2 units in ORD00001"
                     "modify the products of order id ORD00001 where otomize ear spray must be increased to 2 units"
                     "in order ORD00001 set paracetamol quantity to 3"
                     "remove vitamin d from ORD00002"
                     "add montelukast 10mg to order ORD00003"
                     "change quantity of aspirin in ORD00001 to 5"

- order_history  : user wants to see all their past orders
                   Examples: "show my order history", "what orders has customer QA0001 placed",
                             "all orders for customer AH0001"

- account_status : user asks about a customer profile, name, account details, or customer information
                   Examples: "what is the name of customer AH0001", "account details for QA0001",
                             "who is customer AH0001", "look up customer QA0002"

- check_policy   : user asks about return, refund, shipping, or pharmacy policies
                   Examples: "what is your return policy", "how long does shipping take"

- drug_search    : user asks about drug availability, price, or searches for a medication
                   Examples: "how much does Paracetamol cost", "is Ciprofloxacin available",
                             "what is the price of Metformin", "do you have Amoxicillin",
                             "search for vitamin D supplements"

- escalate       : user is frustrated, angry, or explicitly demands a human agent
                   Examples: "I want to speak to a human", "get me a manager", "this is unacceptable"

- place_order    : user wants to place, create, or buy a new order
                   Examples: "place an order", "I want to order", "can you order one", "buy paracetamol",
                             "add to cart", "purchase this", "order paracetamol 500mg"

- general_query  : anything else not covered above

IMPORTANT: If the user mentions an order ID AND mentions changing/updating/modifying/increasing/decreasing
any product or quantity, it is ALWAYS "modify_order" — never "general_query".

Extract entities:
- order_id:        any order identifier (e.g. ORD00001). Return null if not present.
- customer_id:     any customer/account identifier (e.g. AH0001, QA0002). Return null if not present.
- drug_name:       for drug_search ONLY — the drug or medication name the user is asking about (e.g. "Paracetamol 500mg", "Metformin"). Return null for other intents.
- product_updates: for modify_order ONLY — extract ALL products the user wants to change.
                   Each item MUST have "product_name" (exact name as mentioned) and "quantity" (integer).
                   Return null if intent is not modify_order or no product changes are mentioned.
                   Examples:
                     "increase Otomize Ear Spray to 2 units" → [{"product_name": "Otomize Ear Spray", "quantity": 2}]
                     "otomize ear spray must be increased to 2 units" → [{"product_name": "Otomize Ear Spray", "quantity": 2}]
                     "set paracetamol to 3 and add montelukast 10mg 1 unit" → [{"product_name": "Paracetamol", "quantity": 3}, {"product_name": "Montelukast 10mg", "quantity": 1}]

CRITICAL RULES:
1. Customer ID queries (name/details/account) → MUST be "account_status"
2. Order history for a customer → MUST be "order_history"
3. Any order modification/change/update → MUST be "modify_order"
4. Extract IDs exactly as typed
5. For modify_order: ALWAYS extract product_updates when product name + quantity/change is mentioned
6. Return ONLY valid JSON, no extra text

{
  "intent": "<intent>",
  "confidence": <float 0-1>,
  "entities": {
    "order_id": "<value or null>",
    "customer_id": "<value or null>",
    "drug_name": "<value or null>",
    "product_updates": [{"product_name": "<name>", "quantity": <int>}] or null
  }
}"""


def classify_intent(user_input: str, memory: list = None, auth_customer_id: str = None) -> dict:
    """
    Classify intent from user_input.
    memory: list of {user, agent} dicts from AgentState — last 3 turns are
            injected into the prompt so the classifier can resolve references
            like "what is the tracking ID" after "track order ORD00008".
    auth_customer_id: authenticated customer ID from session (None = admin/unauthenticated)
    """
    fallback = {
        "intent": "general_query",
        "confidence": 0.0,
        "entities": {"order_id": None, "customer_id": None, "product_updates": None},
        "is_valid": True,
    }

    context_block = ""
    if memory:
        recent = memory[-3:]
        lines = []
        for turn in recent:
            lines.append(f"Customer: {turn['user']}")
            lines.append(f"Agent: {turn['agent']}")
        context_block = (
            "\n\nCONVERSATION SO FAR (use this to resolve references and carry over entities):\n"
            + "\n".join(lines)
            + "\n\nNow classify the LATEST customer message below."
        )

    raw = ""
    try:
        response = client.chat.completions.create(
            model=CLASSIFIER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + context_block},
                {"role": "user",   "content": user_input},
            ],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)

    except json.JSONDecodeError:
        print(f"[intent_classifier] JSON parse error. Raw: {raw!r}")
        return fallback
    except Exception as e:
        print(f"[intent_classifier] Error: {e}")
        return fallback

    intent = result.get("intent", "general_query")
    if intent not in VALID_INTENTS:
        intent = "general_query"

    confidence = float(result.get("confidence", 0.0))

    entities = result.get("entities", {})
    if not isinstance(entities, dict):
        entities = {}

    order_id        = entities.get("order_id")        or None
    customer_id     = entities.get("customer_id")     or None
    drug_name       = entities.get("drug_name")       or None
    product_updates = entities.get("product_updates") or None

    if order_id:
        order_id = order_id.strip()
    if customer_id:
        customer_id = customer_id.strip()
    if drug_name:
        drug_name = drug_name.strip()

    if product_updates is not None:
        if not isinstance(product_updates, list) or len(product_updates) == 0:
            product_updates = None
        else:
            cleaned = []
            for item in product_updates:
                if isinstance(item, dict) and "product_name" in item and "quantity" in item:
                    try:
                        cleaned.append({
                            "product_name": str(item["product_name"]).strip(),
                            "quantity":     int(item["quantity"]),
                        })
                    except (ValueError, TypeError):
                        pass
            product_updates = cleaned if cleaned else None

    # ── Admin customer_id override ────────────────────────────────────────────
    # CRITICAL: For admin users (auth_customer_id=None), only allow customer_id
    # if it's explicitly mentioned in the CURRENT user input, not from memory/context.
    # This prevents customer IDs from "sticking" across admin queries.
    if auth_customer_id is None and customer_id is not None:
        # Check if customer_id is explicitly in the current user input
        if not _re.search(r'\b' + _re.escape(customer_id) + r'\b', user_input):
            print(f"[intent_classifier] admin override: clearing customer_id={customer_id} (not in current input)")
            customer_id = None

    # ── entity carryover from memory ──────────────────────────────────────────
    # CRITICAL: Only carry over customer_id for authenticated customers, NOT for admins.
    # Admins (auth_customer_id=None) should be able to query any customer without
    # having previous customer IDs "stick" to their session.
    if memory and (order_id is None or customer_id is None):
        for turn in reversed(memory[-5:]):
            for text in (turn.get("user", ""), turn.get("agent", "")):
                if order_id is None:
                    m = _re.search(r'\bORD\d+\b', text, _re.IGNORECASE)
                    if m:
                        order_id = m.group(0).upper()
                        print(f"[intent_classifier] carried over order_id={order_id} from memory")
                # Only carry over customer_id if user is NOT an admin
                if customer_id is None and auth_customer_id is not None:
                    m = _re.search(r'\b[A-Z]{2}\d{4}\b', text)
                    if m:
                        customer_id = m.group(0)
                        print(f"[intent_classifier] carried over customer_id={customer_id} from memory")
            if order_id and customer_id:
                break

    # ── post-classification override ──────────────────────────────────────────
    MODIFY_KEYWORDS = {
        "modify", "change", "update", "increase", "decrease", "reduce",
        "add", "remove", "set quantity", "must be", "products of order",
        "items in order", "alter", "adjust"
    }
    if intent == "general_query" and order_id:
        lower_input = user_input.lower()
        if any(kw in lower_input for kw in MODIFY_KEYWORDS):
            print(f"[intent_classifier] override: general_query → modify_order (keywords matched, order_id={order_id})")
            intent = "modify_order"
            is_valid = True
            if product_updates is None:
                import re
                matches = re.findall(
                    r'([A-Za-z0-9 \-]+?)\s+(?:must be |to |set to )?(?:increased?|decreased?|set)?\s*(?:to\s+)?(\d+)\s*units?',
                    user_input, re.IGNORECASE
                )
                if matches:
                    product_updates = [
                        {"product_name": m[0].strip(), "quantity": int(m[1])}
                        for m in matches
                    ]
                    print(f"[intent_classifier] regex extracted product_updates={product_updates}")

    if intent in ORDER_REQUIRED:
        is_valid = order_id is not None
    elif intent in CUSTOMER_REQUIRED:
        is_valid = customer_id is not None
    else:
        is_valid = True

    return {
        "intent":     intent,
        "confidence": round(confidence, 3),
        "entities":   {
            "order_id":        order_id,
            "customer_id":     customer_id,
            "drug_name":       drug_name,
            "product_updates": product_updates,
        },
        "is_valid":   is_valid,
    }
