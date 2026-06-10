"""Load the logistics CSV into SQLite.

Run once at startup (or manually): python -m app.seed

Correctness rules baked in here (documented in README "Assumptions"):
- delivery_days = delivery_date - order_date, NULL when delivery_date is blank
  (30 rows: all in_transit/canceled — excluded from delivery-time metrics).
- CSV is parsed as quoted CSV: city fields contain commas.
- All 400 rows are loaded, including canceled/exception; metric definitions
  decide which subsets count, not the loader.
"""

import csv
import sqlite3
from datetime import date
from pathlib import Path

DATA_CSV = Path(__file__).resolve().parent.parent / "data" / "mock_logistics_data.csv"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "logistics.db"

SCHEMA = """
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    client_id          TEXT NOT NULL,
    order_id           TEXT PRIMARY KEY,
    order_date         TEXT NOT NULL,            -- ISO yyyy-mm-dd
    delivery_date      TEXT,                     -- NULL when not delivered yet / canceled
    carrier            TEXT NOT NULL,
    origin_city        TEXT NOT NULL,
    destination_city   TEXT NOT NULL,
    status             TEXT NOT NULL,            -- delivered|delayed|in_transit|exception|canceled
    sku                TEXT NOT NULL,
    product_category   TEXT NOT NULL,
    quantity           INTEGER NOT NULL,
    unit_price_usd     REAL NOT NULL,
    order_value_usd    REAL NOT NULL,
    is_promo           INTEGER NOT NULL,         -- 0/1
    promo_discount_pct REAL NOT NULL,
    region             TEXT NOT NULL,
    warehouse          TEXT NOT NULL,
    delivery_days      INTEGER                   -- derived; NULL when delivery_date is NULL
);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);
"""


def seed(db_path: Path = DB_PATH, csv_path: Path = DATA_CSV) -> int:
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        for r in rows:
            delivery = r["delivery_date"].strip() or None
            days = None
            if delivery:
                days = (date.fromisoformat(delivery) - date.fromisoformat(r["order_date"])).days
            conn.execute(
                "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r["client_id"], r["order_id"], r["order_date"], delivery,
                    r["carrier"], r["origin_city"], r["destination_city"], r["status"],
                    r["sku"], r["product_category"], int(r["quantity"]),
                    float(r["unit_price_usd"]), float(r["order_value_usd"]),
                    int(r["is_promo"]), float(r["promo_discount_pct"]),
                    r["region"], r["warehouse"], days,
                ),
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


if __name__ == "__main__":
    n = seed()
    print(f"Seeded {n} rows into {DB_PATH}")
