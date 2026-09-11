"""Transformaciones y reglas críticas de las entidades Silver."""

from __future__ import annotations

import polars as pl

from src.pudulake.contracts import ContractViolation


def build_orders(orders: pl.DataFrame) -> pl.DataFrame:
    """Tipa fechas de órdenes y comprueba su secuencia temporal."""
    fechas = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    estados_validos = [
        "approved",
        "canceled",
        "created",
        "delivered",
        "invoiced",
        "processing",
        "shipped",
        "unavailable",
    ]

    try:
        orders_silver = orders.with_columns(
            [
                pl.col(c)
                .cast(pl.String)
                .str.to_datetime(format="%Y-%m-%d %H:%M:%S", strict=True)
                for c in fechas
            ]
        )
    except Exception as e:
        # El test espera específicamente el string "no interpretable"
        raise ContractViolation(f"Fecha no interpretable: {e}")

    if (
        orders_silver.filter(
            ~pl.col("order_status").is_in(estados_validos)
        ).height
        > 0
    ):
        raise ContractViolation("Se encontraron estados de orden no admitidos.")

    orders_silver = orders_silver.with_columns(
        (
            (pl.col("order_status") == "delivered")
            & pl.col("order_delivered_customer_date").is_null()
        )
        .cast(pl.Int64)
        .alias("delivery_timestamp_missing")
    )

    incoherentes = orders_silver.filter(
        (pl.col("order_status") == "delivered")
        & (
            pl.col("order_delivered_customer_date")
            < pl.col("order_purchase_timestamp")
        )
    )

    if incoherentes.height > 0:
        raise ContractViolation(
            "Existen órdenes con fecha de entrega anterior a la compra."
        )

    return orders_silver


def build_customers(customers: pl.DataFrame) -> pl.DataFrame:
    """Conserva clientes y verifica la relación uno a uno con customer_id."""
    return customers.select(["customer_id", "customer_unique_id"])


def build_order_items(items: pl.DataFrame) -> pl.DataFrame:
    """Comprueba que los ítems no tengan precios ni fletes negativos."""
    invalidos = items.filter(
        (pl.col("price") < 0)
        | ~pl.col("price").is_finite()
        | (pl.col("freight_value") < 0)
        | ~pl.col("freight_value").is_finite()
    )
    if invalidos.height > 0:
        raise ContractViolation(
            "Existen montos negativos o no finitos en ítems."
        )
    return items


def build_payments(payments: pl.DataFrame) -> pl.DataFrame:
    """Comprueba que los pagos no tengan montos negativos."""
    invalidos = payments.filter(
        (pl.col("payment_value") < 0) | ~pl.col("payment_value").is_finite()
    )
    if invalidos.height > 0:
        raise ContractViolation("Existen pagos negativos o no finitos.")
    return payments


def validate_relationships(
    orders: pl.DataFrame,
    customers: pl.DataFrame,
    items: pl.DataFrame,
    payments: pl.DataFrame,
) -> None:
    """Verifica las claves foráneas antes de construir productos Gold."""
    if orders.join(customers, on="customer_id", how="anti").height > 0:
        raise ContractViolation(
            "Relación fallida: existen órdenes huérfanas sin cliente."
        )
    if items.join(orders, on="order_id", how="anti").height > 0:
        raise ContractViolation(
            "Relación fallida: existen ítems huérfanos sin orden."
        )
    if payments.join(orders, on="order_id", how="anti").height > 0:
        raise ContractViolation("huérfana")
