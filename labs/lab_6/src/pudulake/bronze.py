"""Ingesta reproducible de las fuentes Parquet hacia Bronze."""

from __future__ import annotations

from pathlib import Path

import polars as pl


def read_sources(raw_dir: Path) -> dict[str, pl.DataFrame]:
    """Lee las cuatro fuentes crudas y conserva exactamente su esquema."""

    def not_found_error(name: str):
        raise FileNotFoundError(f"{name}")

    orders_dir = raw_dir / "orders.parquet"
    customers_dir = raw_dir / "customers.parquet"
    order_items_dir = raw_dir / "order_items.parquet"
    payments_dir = raw_dir / "payments.parquet"

    return {
        "orders": pl.read_parquet(orders_dir)
        if orders_dir.exists()
        else not_found_error("orders"),
        "customers": pl.read_parquet(customers_dir)
        if customers_dir.exists()
        else not_found_error("customers"),
        "order_items": pl.read_parquet(order_items_dir)
        if order_items_dir.exists()
        else not_found_error("order_items"),
        "payments": pl.read_parquet(payments_dir)
        if payments_dir.exists()
        else not_found_error("payments"),
    }
