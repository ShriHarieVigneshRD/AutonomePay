"""Additive schema upgrades for databases created by older versions.

`create_all` makes missing tables but never alters existing ones, so columns added
after the first release are added here. Only ever add nullable/defaulted columns.
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# table -> {column: DDL type and default}
ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "merchants": {
        "max_discount_inr": "NUMERIC(12, 2) DEFAULT 20.00",
        "split_schedule_pct": "JSON",
        "split_min_invoice_inr": "NUMERIC(12, 2)",
        "partial_settlement_pct": "NUMERIC(5, 2)",
    },
    "evaluation_runs": {
        "batch_id": "VARCHAR(64)",
        "invoice_amount": "NUMERIC(12, 2)",
        "link_amount": "NUMERIC(12, 2)",
        "latency_ms": "NUMERIC(10, 2)",
        "tokens_used": "INTEGER",
        "final_action": "VARCHAR(40)",
        "expected_action": "VARCHAR(255)",
        "passed": "BOOLEAN",
    },
}

# table -> {column: VARCHAR length}. Columns created too narrow by an earlier version; widening is safe.
WIDENED_COLUMNS: dict[str, dict[str, int]] = {
    "evaluation_runs": {"expected_action": 255},
}


def add_missing_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, columns in ADDED_COLUMNS.items():
            if table not in tables:
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for column, ddl in columns.items():
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
                    logger.info("Added column %s.%s", table, column)

        if engine.dialect.name != "postgresql":  # SQLite doesn't enforce VARCHAR lengths
            return
        for table, columns in WIDENED_COLUMNS.items():
            if table not in tables:
                continue
            for col in inspector.get_columns(table):
                length = columns.get(col["name"])
                if length and (getattr(col["type"], "length", None) or 0) < length:
                    conn.execute(
                        text(f"ALTER TABLE {table} ALTER COLUMN {col['name']} TYPE VARCHAR({length})")
                    )
                    logger.info("Widened column %s.%s to VARCHAR(%d)", table, col["name"], length)
