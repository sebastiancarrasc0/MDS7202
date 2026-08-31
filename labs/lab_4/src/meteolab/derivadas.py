"""Funciones para construir fechas mensuales."""

from __future__ import annotations

import polars as pl

from src.meteolab.constantes import MESES, Tabla


def agregar_fecha_mensual(mensuales: Tabla) -> Tabla:
    """Agrega month y una fecha nativa de Polars."""
    q = (
        mensuales.with_columns(
            pl.col("period")
            .replace_strict(MESES, default=255)
            .cast(pl.Int8)
            .alias("month")
        )
        .filter(pl.col("month") != 255)
        .with_columns(
            pl.date(
                year=pl.col("year"),
                month=pl.col("month"),
                day=pl.lit(1),
            ).alias("fecha")
        )
    )
    return q
