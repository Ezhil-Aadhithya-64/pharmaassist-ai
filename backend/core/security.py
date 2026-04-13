"""
Security utilities for access control and audit logging.
Canonical location: backend/core/security.py
"""
from datetime import datetime
from typing import Optional


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
