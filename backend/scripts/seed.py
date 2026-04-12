"""
Database seeder — creates schema and upserts CSV data.
Canonical location: backend/scripts/seed.py

Run from project root:
    python -m backend.scripts.seed
  OR:
    python backend/scripts/seed.py
"""
import os
import json
import pandas as pd
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

# Support running from any working directory
_env_candidates = [
    os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
    ".env",
]
for _p in _env_candidates:
    if os.path.exists(_p):
        load_dotenv(_p)
        break
else:
    load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     os.getenv("DB_PORT"),
    "dbname":   os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id    VARCHAR(6)   PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    email          VARCHAR(150) UNIQUE NOT NULL,
    phone          VARCHAR(15),
    account_status VARCHAR(20)  DEFAULT 'active',
    address        TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id           VARCHAR(10) PRIMARY KEY,
    customer_id        VARCHAR(6) REFERENCES customers(customer_id),
    product_details    JSONB NOT NULL,
    amount             NUMERIC(12,2),
    order_status       VARCHAR(30) DEFAULT 'pending',
    ordered_date       DATE,
    tracking_id        VARCHAR(20),
    expected_delivery  DATE,
    actual_delivery    DATE
);

CREATE TABLE IF NOT EXISTS drugs (
    drug_id         VARCHAR(10) PRIMARY KEY,
    drug_name       VARCHAR(150) NOT NULL,
    generic_name    VARCHAR(150),
    category        VARCHAR(100),
    manufacturer    VARCHAR(100),
    unit_price_inr  NUMERIC(10,2),
    stock_qty       INTEGER
);

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

# Resolve data directory relative to project root
_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")


def seed():
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    cur.execute(CREATE_SCHEMA)
    conn.commit()
    print("Tables created or verified")

    customers = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"))
    customers = customers.where(customers.notna(), None)

    orders = pd.read_csv(os.path.join(DATA_DIR, "orders.csv"))
    orders = orders.where(orders.notna(), None)

    drugs = pd.read_csv(os.path.join(DATA_DIR, "drugs.csv"))
    drugs = drugs.where(drugs.notna(), None)

    for _, r in customers.iterrows():
        cur.execute("""
            INSERT INTO customers (customer_id, name, email, phone, account_status, address)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (customer_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                email = EXCLUDED.email,
                phone = EXCLUDED.phone,
                account_status = EXCLUDED.account_status,
                address = EXCLUDED.address
        """, (
            r['customer_id'], r['name'], r['email'],
            str(r['phone']) if r['phone'] is not None else None,
            r['account_status'], r['address']
        ))

    for _, r in orders.iterrows():
        product_details = r.product_details
        if isinstance(product_details, str):
            product_details = json.loads(product_details)
        cur.execute("""
            INSERT INTO orders (
                order_id, customer_id, product_details, amount, order_status,
                ordered_date, tracking_id, expected_delivery, actual_delivery
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (order_id)
            DO UPDATE SET
                customer_id = EXCLUDED.customer_id,
                product_details = EXCLUDED.product_details,
                amount = EXCLUDED.amount,
                order_status = EXCLUDED.order_status,
                ordered_date = EXCLUDED.ordered_date,
                tracking_id = EXCLUDED.tracking_id,
                expected_delivery = EXCLUDED.expected_delivery,
                actual_delivery = EXCLUDED.actual_delivery
        """, (
            r.order_id, r.customer_id, Json(product_details),
            float(r.amount), r.order_status, r.ordered_date,
            r.tracking_id, r.expected_delivery, r.actual_delivery
        ))

    for _, r in drugs.iterrows():
        cur.execute("""
            INSERT INTO drugs (
                drug_id, drug_name, generic_name, category,
                manufacturer, unit_price_inr, stock_qty
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (drug_id)
            DO UPDATE SET
                drug_name = EXCLUDED.drug_name,
                generic_name = EXCLUDED.generic_name,
                category = EXCLUDED.category,
                manufacturer = EXCLUDED.manufacturer,
                unit_price_inr = EXCLUDED.unit_price_inr,
                stock_qty = EXCLUDED.stock_qty
        """, (
            r.drug_id, r.drug_name, r.generic_name, r.category,
            r.manufacturer, float(r.unit_price_inr), int(r.stock_qty)
        ))

    conn.commit()
    cur.close()
    conn.close()

    print(f"Upserted {len(customers)} customers")
    print(f"Upserted {len(orders)} orders")
    print(f"Upserted {len(drugs)} drugs")


if __name__ == "__main__":
    seed()
