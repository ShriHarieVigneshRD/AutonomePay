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
