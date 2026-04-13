"""
Security utilities for access control and audit logging.
Canonical location: backend/core/security.py
"""
from datetime import datetime
from typing import Optional, List, Tuple


def normalize_order_id(order_id: str) -> str:
    """
    Normalize order ID to standard format (ORD + 5 digits).
    
    Examples:
        ORD000039 -> ORD00039
        ORD39 -> ORD00039
        ORD0039 -> ORD00039
    
    Args:
        order_id: Raw order ID from user input
    
    Returns:
        Normalized order ID in format ORDxxxxx
    """
    if not order_id:
        return order_id
    
    # Extract just the numeric part
    import re
    match = re.search(r'ORD(\d+)', order_id, re.IGNORECASE)
    if not match:
        return order_id
    
    numeric_part = match.group(1)
    
    # Pad to 5 digits
    normalized = f"ORD{int(numeric_part):05d}"
    
    return normalized


def find_similar_order_ids(invalid_id: str, customer_id: Optional[str] = None) -> List[str]:
    """
    Find similar order IDs when an invalid ID is provided.
    
    Args:
        invalid_id: The invalid order ID provided by user
        customer_id: Optional customer ID to scope search
    
    Returns:
        List of similar order IDs
    """
    try:
        from backend.tools.db_tools import get_conn, release_conn
        import psycopg2.extras
        
        # Try normalized version first
        normalized = normalize_order_id(invalid_id)
        
        conn = get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if customer_id:
                    # Search for similar IDs for this customer
                    cur.execute(
                        "SELECT order_id FROM orders WHERE customer_id = %s ORDER BY order_id DESC LIMIT 5",
                        (customer_id,)
                    )
                else:
                    # Try exact match with normalized ID
                    cur.execute(
                        "SELECT order_id FROM orders WHERE order_id = %s LIMIT 1",
                        (normalized,)
                    )
                
                results = [row["order_id"] for row in cur.fetchall()]
                return results
        finally:
            release_conn(conn)
    except Exception as e:
        print(f"[find_similar_order_ids] error: {e}")
        return []


def log_access_denied(
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: str,
    reason: str,
    session_id: Optional[str] = None
):
    """
    Log access denied events for security auditing.
    
    Args:
        user_id: Authenticated user/customer ID (None = unauthenticated)
        action: Action attempted (e.g., "view_order", "modify_order")
        resource_type: Type of resource (e.g., "order", "customer_profile")
        resource_id: ID of the resource (e.g., "ORD00001", "AH0001")
        reason: Reason for denial
        session_id: Session ID for correlation
    """
    timestamp = datetime.utcnow().isoformat()
    user_label = user_id or "UNAUTHENTICATED"
    session_label = session_id or "unknown"
    
    log_entry = (
        f"[SECURITY_AUDIT] {timestamp} | "
        f"user={user_label} | session={session_label} | "
        f"action={action} | resource={resource_type}:{resource_id} | "
        f"status=DENIED | reason={reason}"
    )
    
    print(log_entry)
    
    # TODO: In production, write to dedicated security audit log file or SIEM
    # with open("/var/log/pharmaassist/security_audit.log", "a") as f:
    #     f.write(log_entry + "\n")


def log_access_granted(
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: str,
    session_id: Optional[str] = None
):
    """
    Log successful access for security auditing.
    
    Args:
        user_id: Authenticated user/customer ID (None = admin)
        action: Action performed
        resource_type: Type of resource
        resource_id: ID of the resource
        session_id: Session ID for correlation
    """
    timestamp = datetime.utcnow().isoformat()
    user_label = user_id or "ADMIN"
    session_label = session_id or "unknown"
    
    log_entry = (
        f"[SECURITY_AUDIT] {timestamp} | "
        f"user={user_label} | session={session_label} | "
        f"action={action} | resource={resource_type}:{resource_id} | "
        f"status=GRANTED"
    )
    
    print(log_entry)


def is_admin(auth_customer_id: Optional[str]) -> bool:
    """
    Check if the authenticated user is an admin.
    
    Args:
        auth_customer_id: Customer ID from authentication (None = admin)
    
    Returns:
        True if admin, False if customer
    """
    return auth_customer_id is None


def validate_customer_access(
    auth_customer_id: Optional[str],
    target_customer_id: str,
    action: str,
    session_id: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate if a user can access a customer's data.
    
    Args:
        auth_customer_id: Authenticated customer ID (None = admin)
        target_customer_id: Customer ID being accessed
        action: Action being performed
        session_id: Session ID for audit logging
    
    Returns:
        Tuple of (is_allowed, error_message)
    """
    if is_admin(auth_customer_id):
        # Admins can access any customer
        log_access_granted(
            user_id=None,
            action=action,
            resource_type="customer",
            resource_id=target_customer_id,
            session_id=session_id
        )
        return True, None
    
    if auth_customer_id == target_customer_id:
        # Customers can access their own data
        log_access_granted(
            user_id=auth_customer_id,
            action=action,
            resource_type="customer",
            resource_id=target_customer_id,
            session_id=session_id
        )
        return True, None
    
    # Access denied
    log_access_denied(
        user_id=auth_customer_id,
        action=action,
        resource_type="customer",
        resource_id=target_customer_id,
        reason=f"Customer {auth_customer_id} attempted to access customer {target_customer_id}",
        session_id=session_id
    )
    return False, f"You can only access your own data. Attempted access to {target_customer_id} has been logged."


def validate_order_access(
    auth_customer_id: Optional[str],
    order_id: str,
    order_owner_id: str,
    action: str,
    session_id: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate if a user can access an order.
    
    Args:
        auth_customer_id: Authenticated customer ID (None = admin)
        order_id: Order ID being accessed
        order_owner_id: Customer ID who owns the order
        action: Action being performed
        session_id: Session ID for audit logging
    
    Returns:
        Tuple of (is_allowed, error_message)
    """
    if is_admin(auth_customer_id):
        # Admins can access any order
        log_access_granted(
            user_id=None,
            action=action,
            resource_type="order",
            resource_id=order_id,
            session_id=session_id
        )
        return True, None
    
    if auth_customer_id == order_owner_id:
        # Customers can access their own orders
        log_access_granted(
            user_id=auth_customer_id,
            action=action,
            resource_type="order",
            resource_id=order_id,
            session_id=session_id
        )
        return True, None
    
    # Access denied
    log_access_denied(
        user_id=auth_customer_id,
        action=action,
        resource_type="order",
        resource_id=order_id,
        reason=f"Customer {auth_customer_id} attempted to access order {order_id} owned by {order_owner_id}",
        session_id=session_id
    )
    return False, f"Order {order_id} does not belong to your account. This attempt has been logged."
