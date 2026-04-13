"""
Database tools — all PostgreSQL operations as LangChain @tool functions.
Canonical location: backend/tools/db_tools.py
"""
import psycopg2
import psycopg2.extras
from psycopg2 import pool
import os
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

import backend.core.config as _cfg  # noqa: F401 — ensures .env is loaded
from langchain_core.tools import tool
from backend.core.data_sanitizer import (
    sanitize_order_id,
    sanitize_customer_id,
    sanitize_status,
    sanitize_db_row,
    fuzzy_match_order,
)

DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     os.getenv("DB_PORT"),
    "dbname":   os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

# Connection pool - reuse connections for better performance
_connection_pool = None

def get_connection_pool():
    """Get or create connection pool."""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                **DB_CONFIG
            )
            print("[db_tools] Connection pool created (2-10 connections)")
        except Exception as e:
            print(f"[db_tools] Connection pool creation failed: {e}")
            raise
    return _connection_pool

def get_conn():
    """Get a connection from the pool."""
    try:
        pool_instance = get_connection_pool()
        return pool_instance.getconn()
    except Exception:
        # Fallback to direct connection if pool fails
        return psycopg2.connect(**DB_CONFIG)

def release_conn(conn):
    """Return connection to pool."""
    try:
        pool_instance = get_connection_pool()
        pool_instance.putconn(conn)
    except Exception:
        # If pool doesn't exist, just close the connection
        if conn:
            release_conn(conn)


def ok(data: dict) -> dict:
    return {"status": "success", "data": data}


def normalize_order_id(order_id: str) -> Optional[str]:
    """
    Normalize and validate order ID format, with fuzzy matching for common typos.
    
    Expected format: ORDxxxxx (where xxxxx is 5 digits)
    Common errors: ORD0000xx (extra zeros), ORDxxx (missing zeros)
    
    Returns normalized order_id or None if invalid format.
    """
    import re
    
    order_id = order_id.strip().upper()
    
    # Extract the numeric part
    match = re.match(r'^ORD(\d+)$', order_id, re.IGNORECASE)
    if not match:
        return None
    
    numeric_part = match.group(1)
    
    # Normalize to 5 digits
    if len(numeric_part) <= 5:
        # Pad with leading zeros if too short
        normalized = f"ORD{numeric_part.zfill(5)}"
    else:
        # Too many digits - try removing leading zeros
        # ORD000039 -> ORD00039
        numeric_part = numeric_part.lstrip('0') or '0'
        if len(numeric_part) <= 5:
            normalized = f"ORD{numeric_part.zfill(5)}"
        else:
            # Still too long, invalid
            return None
    
    return normalized


def find_order_fuzzy(order_id: str, conn) -> Optional[str]:
    """
    Try to find an order with fuzzy matching for common typos.
    
    Returns the actual order_id from database or None if not found.
    """
    # First try exact match
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT order_id FROM orders WHERE order_id = %s", (order_id,))
        row = cur.fetchone()
        if row:
            return row["order_id"]
    
    # Try normalized version
    normalized = normalize_order_id(order_id)
    if normalized and normalized != order_id:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT order_id FROM orders WHERE order_id = %s", (normalized,))
            row = cur.fetchone()
            if row:
                print(f"[find_order_fuzzy] normalized {order_id} -> {normalized}")
                return row["order_id"]
    
    return None


# ── RETRIEVAL TOOLS ────────────────────────────────────────────────────────────

@tool
def get_customer_profile(customer_id: str) -> dict:
    """Fetch customer profile from CRM using customer_id."""
    customer_id = str(customer_id).strip()[:50]  # Sanitize input
    conn = None
    try:
        conn = get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
            row = cur.fetchone()
            if not row:
                return {"status": "error", "data": {"message": f"Customer {customer_id} not found"}}
            return ok(dict(row))
    finally:
        if conn:
            release_conn(conn)


@tool
def get_order_details(order_id: str) -> dict:
    """Fetch full order details using order_id."""
    order_id = sanitize_order_id(order_id)
    if not order_id:
        return {"status": "error", "data": {"message": "Invalid order ID format"}}
    
    conn = None
    try:
        conn = get_conn()
        
        # Try fuzzy matching
        actual_order_id = fuzzy_match_order(order_id, conn)
        if not actual_order_id:
            return {"status": "error", "data": {"message": f"Order {order_id} not found"}}
        
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM orders WHERE UPPER(TRIM(order_id)) = %s", (actual_order_id.upper(),))
            row = cur.fetchone()
            if not row:
                return {"status": "error", "data": {"message": f"Order {order_id} not found"}}
            return ok(sanitize_db_row(dict(row)))
    finally:
        if conn:
            release_conn(conn)


@tool
def get_order_history(customer_id: str) -> dict:
    """Fetch all orders placed by a customer using customer_id."""
    customer_id = str(customer_id).strip()[:50]  # Sanitize input
    conn = None
    try:
        conn = get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM orders WHERE customer_id = %s ORDER BY ordered_date DESC",
                (customer_id,)
            )
            rows = cur.fetchall()
            return ok({"customer_id": customer_id, "orders": [dict(r) for r in rows]})
    finally:
        if conn:
            release_conn(conn)


# ── ACTION TOOLS ───────────────────────────────────────────────────────────────

@tool
def process_refund(order_id: str) -> dict:
    """Initiate a refund for an order using order_id. Only allowed for cancelled, pending, returned or shipped orders."""
    order_id = sanitize_order_id(order_id)
    if not order_id:
        return {"status": "error", "data": {"message": "Invalid order ID format"}}
    
    REFUNDABLE = {"cancelled", "pending", "returned", "shipped"}
    conn = None
    try:
        conn = get_conn()
        
        # Try fuzzy matching
        actual_order_id = fuzzy_match_order(order_id, conn)
        if not actual_order_id:
            return {"status": "error", "data": {"message": f"Order {order_id} not found"}}
        
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM orders WHERE UPPER(TRIM(order_id)) = %s", (actual_order_id.upper(),))
            row = cur.fetchone()
            if not row:
                return {"status": "error", "data": {"message": f"Order {order_id} not found"}}
            status = sanitize_status(row["order_status"])
            if status not in REFUNDABLE:
                return {"status": "rejected", "data": {
                    "message": f"Refund not applicable. Order {order_id} has status '{status}'. "
                               f"Refunds are only available for cancelled, pending, returned or shipped orders."
                }}
            cur.execute(
                "UPDATE orders SET order_status = 'refund_initiated' WHERE UPPER(TRIM(order_id)) = %s", (actual_order_id.upper(),)
            )
            conn.commit()
            return ok({
                "order_id":   actual_order_id,
                "action":     "refund_initiated",
                "amount":     float(row["amount"]),
                "new_status": "refund_initiated"
            })
    finally:
        if conn:
            release_conn(conn)


@tool
def cancel_order(order_id: str) -> dict:
    """Cancel an order using order_id. Only allowed for pending or shipped orders."""
    order_id = sanitize_order_id(order_id)
    if not order_id:
        return {"status": "error", "data": {"message": "Invalid order ID format"}}
    
    CANCELLABLE = {"pending", "shipped"}
    conn = None
    try:
        conn = get_conn()
        
        # Try fuzzy matching
        actual_order_id = fuzzy_match_order(order_id, conn)
        if not actual_order_id:
            return {"status": "error", "data": {"message": f"Order {order_id} not found"}}
        
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM orders WHERE UPPER(TRIM(order_id)) = %s", (actual_order_id.upper(),))
            row = cur.fetchone()
            if not row:
                return {"status": "error", "data": {"message": f"Order {order_id} not found"}}
            status = sanitize_status(row["order_status"])
            if status not in CANCELLABLE:
                return {"status": "rejected", "data": {
                    "message": f"Cannot cancel order {order_id}. Current status is '{status}'. "
                               f"Only pending or shipped orders can be cancelled."
                }}
            cur.execute(
                "UPDATE orders SET order_status = 'cancelled' WHERE UPPER(TRIM(order_id)) = %s", (actual_order_id.upper(),)
            )
            conn.commit()
            return ok({
                "order_id":   actual_order_id,
                "action":     "order_cancelled",
                "new_status": "cancelled"
            })
    finally:
        if conn:
            release_conn(conn)


@tool
def modify_order(order_id: str, updated_products: List[dict]) -> dict:
    """
    Modify an order by merging product updates into the existing product list.
    'updated_products' is a list of {product_name, quantity}.
    Only specified products are updated; all other existing products remain unchanged.
    Example: [{"product_name": "Paracetamol 500mg", "quantity": 2}]
    """
    order_id = sanitize_order_id(order_id)
    if not order_id:
        return {"status": "error", "data": {"message": "Invalid order ID format"}}
    
    conn = None
    try:
        conn = get_conn()
        
        # Try fuzzy matching
        actual_order_id = fuzzy_match_order(order_id, conn)
        if not actual_order_id:
            return {"status": "error", "data": {"message": f"Order {order_id} not found"}}
        
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM orders WHERE UPPER(TRIM(order_id)) = %s", (actual_order_id.upper(),))
            order = cur.fetchone()
            if not order:
                return {"status": "error", "data": {"message": f"Order {order_id} not found"}}

            existing = order["product_details"]
            if isinstance(existing, str):
                existing = json.loads(existing)
            existing_map = {item["product_name"].lower(): dict(item) for item in existing}

            for item in updated_products:
                p_name = item.get("product_name", "").strip()
                qty    = item.get("quantity", 1)
                matched_key = next((k for k in existing_map if k == p_name.lower()), None)
                if matched_key:
                    if qty == 0:
                        # Remove product from order
                        del existing_map[matched_key]
                        print(f"[modify_order] removed {p_name} from order")
                    else:
                        existing_map[matched_key]["quantity"] = qty
                else:
                    # Only add new products if quantity > 0
                    if qty > 0:
                        # Try to find the drug with fuzzy matching (partial name match)
                        cur.execute(
                            "SELECT drug_name FROM drugs WHERE drug_name ILIKE %s LIMIT 1", (f"%{p_name}%",)
                        )
                        drug_row = cur.fetchone()
                        if drug_row:
                            canonical = drug_row["drug_name"]
                            existing_map[canonical.lower()] = {"product_name": canonical, "quantity": qty}
                        else:
                            return {"status": "error", "data": {"message": f"Drug matching '{p_name}' not found in catalog"}}

            merged = list(existing_map.values())

            new_total = 0.0
            for item in merged:
                cur.execute(
                    "SELECT unit_price_inr FROM drugs WHERE drug_name ILIKE %s LIMIT 1",
                    (item["product_name"],)
                )
                drug = cur.fetchone()
                if not drug:
                    return {"status": "error", "data": {"message": f"Drug '{item['product_name']}' not found"}}
                new_total += float(drug["unit_price_inr"]) * item["quantity"]

            cur.execute(
                "UPDATE orders SET product_details = %s, amount = %s WHERE UPPER(TRIM(order_id)) = %s",
                (json.dumps(merged), round(new_total, 2), actual_order_id.upper())
            )
            conn.commit()
            print(f"[modify_order] updated order={actual_order_id} total={new_total}")
            return ok({
                "order_id": actual_order_id,
                "action":   "order_modified",
                "updates":  {"products": merged, "new_total_amount": round(new_total, 2)}
            })
    finally:
        if conn:
            release_conn(conn)


@tool
def search_drugs(query: str) -> dict:
    """Search for drugs by ID, name, or generic name to find prices and availability."""
    query = str(query).strip()[:200]  # Sanitize and limit length
    conn = None
    try:
        conn = get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM drugs WHERE drug_id ILIKE %s OR drug_name ILIKE %s OR generic_name ILIKE %s",
                (f"%{query}%", f"%{query}%", f"%{query}%")
            )
            rows = cur.fetchall()
            return ok([dict(r) for r in rows])
    finally:
        if conn:
            release_conn(conn)


# ── ESCALATION TOOL ────────────────────────────────────────────────────────────

@tool
def escalate_to_human(customer_id: str, order_id: str, reason: str) -> dict:
    """Escalate the case to a human agent with customer and order context."""
    customer_id = str(customer_id).strip()[:50]  # Sanitize input
    order_id = str(order_id).strip()[:50]
    reason = str(reason).strip()[:500]
    conn = None
    try:
        conn = get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
            customer = cur.fetchone()
            cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
            order = cur.fetchone()
        return ok({
            "escalation_status": "queued_for_human",
            "customer":          dict(customer) if customer else {},
            "order":             dict(order) if order else {},
            "reason":            reason
        })
    finally:
        if conn:
            release_conn(conn)


# ── NOTIFICATION TOOL ──────────────────────────────────────────────────────────

@tool
def send_customer_email(customer_id: str, subject: str, body: str) -> dict:
    """
    Send a notification email to a customer using their customer_id.
    The recipient email is fetched from the CRM database.
    """
    customer_id = str(customer_id).strip()[:50]  # Sanitize input
    subject = str(subject).strip()[:200]
    body = str(body).strip()[:5000]
    
    conn = None
    try:
        conn = get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT name, email FROM customers WHERE customer_id = %s", (customer_id,))
            customer = cur.fetchone()
            if not customer:
                return {"status": "error", "data": {"message": f"Customer {customer_id} not found"}}
    finally:
        if conn:
            release_conn(conn)

    recipient_email = customer["email"]
    recipient_name  = customer["name"]
    print(f"[send_customer_email] Sending to {recipient_name} <{recipient_email}> — '{subject}'")

    sender_email = os.getenv("MAIL_SENDER")
    app_password = os.getenv("MAIL_APP_PASSWORD")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender_email
    msg["To"]      = recipient_email
    msg.attach(MIMEText(body, "plain"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        return ok({"action": "email_sent", "customer_id": customer_id,
                   "recipient": recipient_email, "subject": subject})
    except Exception as e:
        return {"status": "error", "data": {"message": str(e)}}


# ── INTERACTION LOGGING ────────────────────────────────────────────────────────

def ensure_interactions_table():
    """Create interactions table if it doesn't exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS interactions (
        id                SERIAL PRIMARY KEY,
        session_id        VARCHAR(64),
        intent            VARCHAR(50),
        entities          JSONB,
        action_taken      VARCHAR(100),
        resolution_status VARCHAR(30),
        transcript        TEXT,
        created_at        TIMESTAMP DEFAULT NOW()
    );
    """
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    except Exception as e:
        print(f"[ensure_interactions_table] {e}")
    finally:
        if conn:
            release_conn(conn)


@tool
def log_interaction(
    session_id: str,
    intent: str,
    entities: str,
    action_taken: str,
    resolution_status: str,
    transcript: str,
) -> dict:
    """Log a completed interaction to the interactions table. entities must be a JSON string."""
    # Input sanitization
    session_id = str(session_id).strip()[:64]
    intent = str(intent).strip()[:50]
    action_taken = str(action_taken).strip()[:100]
    resolution_status = str(resolution_status).strip()[:30]
    transcript = str(transcript).strip()[:50000]
    
    ensure_interactions_table()
    try:
        entities_json = json.loads(entities) if isinstance(entities, str) else entities
    except Exception:
        entities_json = {}
    
    conn = None
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO interactions
                   (session_id, intent, entities, action_taken, resolution_status, transcript)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (session_id, intent, psycopg2.extras.Json(entities_json),
                 action_taken, resolution_status, transcript)
            )
        conn.commit()
        return ok({"logged": True, "session_id": session_id})
    except Exception as e:
        print(f"[log_interaction] error: {e}")
        return {"status": "error", "data": {"message": str(e)}}
    finally:
        if conn:
            release_conn(conn)


def get_interaction_metrics(customer_id: str = None) -> dict:
    """Fetch supervisor dashboard metrics from interactions table. Optionally scoped to a customer."""
    if customer_id:
        customer_id = str(customer_id).strip()[:50]
    
    ensure_interactions_table()
    conn = None
    try:
        scope_filter = "WHERE session_id LIKE %s" if customer_id else ""
        res_filter   = f"{scope_filter} {'AND' if customer_id else 'WHERE'} resolution_status = %s"
        scope_params = (f"{customer_id}_%",) if customer_id else ()

        conn = get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT COUNT(DISTINCT session_id) AS total_sessions FROM interactions {scope_filter}", scope_params)
            total = cur.fetchone()["total_sessions"] or 0

            cur.execute(f"SELECT COUNT(DISTINCT session_id) AS cnt FROM interactions {res_filter}",
                        scope_params + ("resolved",))
            resolved = cur.fetchone()["cnt"] or 0

            cur.execute(f"SELECT COUNT(DISTINCT session_id) AS cnt FROM interactions {res_filter}",
                        scope_params + ("escalated",))
            escalated = cur.fetchone()["cnt"] or 0

            cur.execute(f"""
                SELECT AVG(turn_count) AS aht FROM (
                    SELECT session_id, COUNT(*) AS turn_count
                    FROM interactions {scope_filter}
                    GROUP BY session_id
                ) t
            """, scope_params)
            aht_row = cur.fetchone()
            aht = round(float(aht_row["aht"]), 1) if aht_row["aht"] else 0.0

            cur.execute(f"""
                SELECT intent, COUNT(*) AS cnt
                FROM interactions {scope_filter}
                GROUP BY intent ORDER BY cnt DESC LIMIT 5
            """, scope_params)
            top_intents = [dict(r) for r in cur.fetchall()]

        return {
            "total_sessions":  total,
            "resolved":        resolved,
            "escalated":       escalated,
            "resolution_rate": round(resolved / total * 100, 1) if total else 0.0,
            "escalation_rate": round(escalated / total * 100, 1) if total else 0.0,
            "avg_turns":       aht,
            "top_intents":     top_intents,
        }
    except Exception as e:
        print(f"[get_interaction_metrics] {e}")
        return {}
    finally:
        if conn:
            release_conn(conn)


# ── TOOL REGISTRIES ────────────────────────────────────────────────────────────

TOOLS = [
    get_customer_profile,
    get_order_details,
    get_order_history,
    process_refund,
    cancel_order,
    modify_order,
    search_drugs,
    escalate_to_human,
    send_customer_email,
]

ACTION_TOOLS = [
    cancel_order,
    process_refund,
    modify_order,
    escalate_to_human,
    send_customer_email,
]

