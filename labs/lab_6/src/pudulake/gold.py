"""Productos analíticos Gold de Pudubella."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import polars as pl


def build_rfm_exclusions(
    orders: pl.DataFrame, payments: pl.DataFrame
) -> pl.DataFrame:
    delivered = orders.filter(pl.col("order_status") == "delivered")
    payment_keys = payments.select("order_id").unique()
    return (
        delivered.join(payment_keys, on="order_id", how="anti")
        .select(["order_id", "customer_id", "order_purchase_timestamp"])
        .with_columns(pl.lit("delivered_order_without_payment").alias("reason"))
    )


def build_sales_daily(
    orders: pl.DataFrame, items: pl.DataFrame
) -> pl.DataFrame:
    """Construye ventas de ítems por fecha de compra y órdenes entregadas."""
    return (
        orders.filter(pl.col("order_status") == "delivered")
        .join(items, on="order_id", how="inner")
        .with_columns(
            pl.col("order_purchase_timestamp").dt.date().alias("sale_date")
        )
        .group_by("sale_date")
        .agg(
            pl.col("price").sum().alias("items_sold_value"),
            pl.col("order_id").n_unique().alias("delivered_orders"),
        )
        .sort("sale_date")
    )


def build_customer_rfm(
    orders: pl.DataFrame,
    customers: pl.DataFrame,
    payments: pl.DataFrame,
    segments: dict[str, Any],
) -> pl.DataFrame:
    """Calcula RFM de compras entregadas y aplica reglas congeladas."""
    rfm_exclusions = build_rfm_exclusions(orders, payments)

    delivered_orders = orders.filter(pl.col("order_status") == "delivered")
    eligible_orders = delivered_orders.join(
        rfm_exclusions.select("order_id"), on="order_id", how="anti"
    )

    payments_by_order = payments.group_by("order_id").agg(
        pl.col("payment_value").sum().alias("order_payment_value")
    )

    eligible_with_payment = eligible_orders.join(
        payments_by_order, on="order_id", how="inner"
    ).join(customers, on="customer_id", how="inner")

    reference_date = eligible_with_payment.select(
        pl.col("order_purchase_timestamp").max()
    ).item().date() + timedelta(days=1)

    thresholds = segments["segments"]

    customer_rfm = (
        eligible_with_payment.group_by("customer_unique_id")
        .agg(
            pl.col("order_purchase_timestamp").max().alias("last_purchase"),
            pl.col("order_id").n_unique().alias("frequency"),
            pl.col("order_payment_value").sum().alias("monetary"),
        )
        .with_columns(
            (pl.lit(reference_date) - pl.col("last_purchase").dt.date())
            .dt.total_days()
            .alias("recency_days")
        )
    )

    return customer_rfm.with_columns(
        pl.when(
            (
                pl.col("recency_days")
                <= thresholds["champions"]["max_recency_days"]
            )
            & (pl.col("frequency") >= thresholds["champions"]["min_frequency"])
            & (pl.col("monetary") >= thresholds["champions"]["min_monetary"])
        )
        .then(pl.lit("Champions"))
        .when(pl.col("frequency") >= thresholds["loyal"]["min_frequency"])
        .then(pl.lit("Loyal"))
        .when(pl.col("recency_days") <= thresholds["new"]["max_recency_days"])
        .then(pl.lit("New"))
        .when(pl.col("recency_days") >= thresholds["lost"]["min_recency_days"])
        .then(pl.lit("Lost"))
        .otherwise(pl.lit("Other"))
        .alias("segment")
    )
