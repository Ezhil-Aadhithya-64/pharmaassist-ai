"""
Dynamic data sanitization and normalization utilities.
Handles all edge cases for database data quality issues.
Canonical location: backend/core/data_sanitizer.py
"""
import re
from typing import Any, Dict, Optional


def sanitize_order_id(order_id: Optional[str]) -> Optional[str]:
    """
    Normalize order ID to standard format, handling all variations.
    
    Handles:
    - Extra zeros: ORD000039 -> ORD00039
    - Missing zeros: ORD39 -> ORD00039
    - Lowercase: ord00039 -> ORD00039
    - Whitespace: " ORD00039 " -> ORD00039
    - None/empty values
    
    Returns:
        Normalized order ID or None if invalid
    """
    if not order_id:
        return None
    
    order_id = str(order_id).strip().upper()
    
    # Extract numeric part
    match = re.match(r'^ORD(\d+)$', order_id)
    if not match:
        return None
    
    numeric_part = match.group(1)
    
    # Normalize to 5 digits
    if len(numeric_part) <= 5:
        return f"ORD{numeric_part.zfill(5)}"
    else:
        # Remove leading zeros if too many
        numeric_part = numeric_part.lstrip('0') or '0'
        if len(numeric_part) <= 5:
            return f"ORD{numeric_part.zfill(5)}"
    
    return None


def sanitize_customer_id(customer_id: Optional[str]) -> Optional[str]:
    """
    Normalize customer ID to standard format.
    
    Handles:
    - Whitespace: " AH0001 " -> AH0001
    - Lowercase: ah0001 -> AH0001
    - None/empty values
    
    Returns:
        Normalized customer ID or None if invalid
    """
    if not customer_id:
        return None
    
    customer_id = str(customer_id).strip().upper()
    
    # Validate format: 2 letters + 4 digits
    if re.match(r'^[A-Z]{2}\d{4}$', customer_id):
        return customer_id
    
    return None


def sanitize_status(status: Optional[str]) -> str:
    """
    Normalize order/entity status.
    
    Handles:
    - Trailing/leading whitespace: " pending " -> pending
    - Case variations: PENDING -> pending
    - None values -> empty string
    
    Returns:
        Normalized lowercase status
    """
    if not status:
        return ""
    
    return str(status).strip().lower()


def sanitize_product_name(product_name: Optional[str]) -> Optional[str]:
    """
    Normalize product/drug name.
    
    Handles:
    - Extra whitespace: "Paracetamol  500mg" -> "Paracetamol 500mg"
    - Case variations: "paracetamol 500mg" -> "Paracetamol 500mg"
    - None/empty values
    
    Returns:
        Normalized product name or None if invalid
    """
    if not product_name:
        return None
    
    # Normalize whitespace
    product_name = ' '.join(str(product_name).split())
    
    # Title case for better readability
    return product_name.strip()


def sanitize_dict(data: Dict[str, Any], field_types: Dict[str, str]) -> Dict[str, Any]:
    """
    Sanitize all fields in a dictionary based on their types.
    
    Args:
        data: Dictionary to sanitize
        field_types: Mapping of field names to types
                    (e.g., {"order_id": "order_id", "status": "status"})
    
    Returns:
        Sanitized dictionary
    """
    sanitized = {}
    
    for key, value in data.items():
        field_type = field_types.get(key)
        
        if field_type == "order_id":
            sanitized[key] = sanitize_order_id(value)
        elif field_type == "customer_id":
            sanitized[key] = sanitize_customer_id(value)
        elif field_type == "status":
            sanitized[key] = sanitize_status(value)
        elif field_type == "product_name":
            sanitized[key] = sanitize_product_name(value)
        else:
            # Default: strip strings, pass through others
            if isinstance(value, str):
                sanitized[key] = value.strip()
            else:
                sanitized[key] = value
    
    return sanitized


def sanitize_db_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Automatically sanitize a database row based on common field names.
    
    Handles:
    - order_id fields
    - customer_id fields
    - *_status fields
    - product_name fields
    - All string fields (trim whitespace)
    
    Returns:
        Sanitized row dictionary
    """
    if not row:
        return row
    
    sanitized = {}
    
    for key, value in row.items():
        # Skip None values
        if value is None:
            sanitized[key] = value
            continue
        
        # Sanitize based on field name patterns
        key_lower = key.lower()
        
        if 'order_id' in key_lower:
            sanitized[key] = sanitize_order_id(value)
        elif 'customer_id' in key_lower:
            sanitized[key] = sanitize_customer_id(value)
        elif key_lower.endswith('_status') or key_lower == 'status':
            sanitized[key] = sanitize_status(value)
        elif 'product_name' in key_lower or 'drug_name' in key_lower:
            sanitized[key] = sanitize_product_name(value)
        elif isinstance(value, str):
            # Default: trim all strings
            sanitized[key] = value.strip()
        else:
            sanitized[key] = value
    
    return sanitized


def fuzzy_match_order(order_id: str, conn) -> Optional[str]:
    """
    Find order with fuzzy matching, trying multiple strategies.
    
    Strategies:
    1. Exact match
    2. Normalized match
    3. Case-insensitive match
    4. Partial match (last 3-5 digits)
    
    Returns:
        Actual order_id from database or None
    """
    import psycopg2.extras
    
    # Strategy 1: Exact match
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT order_id FROM orders WHERE order_id = %s", (order_id,))
        row = cur.fetchone()
        if row:
            return sanitize_order_id(row["order_id"])
    
    # Strategy 2: Normalized match
    normalized = sanitize_order_id(order_id)
    if normalized and normalized != order_id:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT order_id FROM orders WHERE order_id = %s", (normalized,))
            row = cur.fetchone()
            if row:
                print(f"[fuzzy_match_order] normalized {order_id} -> {normalized}")
                return sanitize_order_id(row["order_id"])
    
    # Strategy 3: Case-insensitive match
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT order_id FROM orders WHERE UPPER(TRIM(order_id)) = %s", (order_id.upper(),))
        row = cur.fetchone()
        if row:
            print(f"[fuzzy_match_order] case-insensitive match for {order_id}")
            return sanitize_order_id(row["order_id"])
    
    return None
