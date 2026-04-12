"""
Integration tests for db_tools.
Canonical location: tests/test_db_tools.py
"""
import json
from decimal import Decimal
from datetime import date, datetime

try:
    from backend.tools.db_tools import (
        get_customer_profile,
        get_order_details,
        get_order_history,
        process_refund,
        cancel_order,
        modify_order,
        search_drugs,
        escalate_to_human,
    )
except ModuleNotFoundError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from backend.tools.db_tools import (
        get_customer_profile,
        get_order_details,
        get_order_history,
        process_refund,
        cancel_order,
        modify_order,
        search_drugs,
        escalate_to_human,
    )


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


def print_result(name, result):
    print(f"\n--- Testing: {name} ---")
    print(json.dumps(result, indent=2, cls=EnhancedJSONEncoder))


def run_tests():
    TEST_CUSTOMER_ID = "XL0029"
    TEST_ORDER_ID    = "ORD00050"
    TEST_DRUG_QUERY  = "Paracetamol"

    print("Starting Tool Integration Tests...")

    print_result("get_customer_profile", get_customer_profile.invoke({"customer_id": TEST_CUSTOMER_ID}))
    print_result("get_order_history",    get_order_history.invoke({"customer_id": TEST_CUSTOMER_ID}))
    print_result("get_order_details",    get_order_details.invoke({"order_id": TEST_ORDER_ID}))
    print_result("search_drugs",         search_drugs.invoke({"query": TEST_DRUG_QUERY}))

    new_products = [{"product_name": "Paracetamol 500mg", "quantity": 2}]
    print_result("modify_order",  modify_order.invoke({"order_id": TEST_ORDER_ID, "updated_products": new_products}))
    print_result("process_refund", process_refund.invoke({"order_id": TEST_ORDER_ID}))
    print_result("cancel_order",   cancel_order.invoke({"order_id": TEST_ORDER_ID}))
    print_result("escalate_to_human", escalate_to_human.invoke({
        "customer_id": TEST_CUSTOMER_ID,
        "order_id":    TEST_ORDER_ID,
        "reason":      "Customer is unhappy with the repeated modifications.",
    }))


if __name__ == "__main__":
    try:
        run_tests()
        print("\n✅ All tool tests completed.")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
