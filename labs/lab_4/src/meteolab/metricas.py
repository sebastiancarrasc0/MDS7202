"""Agregaciones sobre las temperaturas medias mensuales."""

from __future__ import annotations

import polars as pl


def resumen_mensual(
    mensuales: pl.DataFrame | pl.LazyFrame,
    paises: list[str] | tuple[str, ...] | None = None,
) -> pl.DataFrame | pl.LazyFrame:
    """Calcula la climatología mensual por país."""
    if paises is not None:
        mensuales = mensuales.filter(pl.col("iso_alpha3").is_in(paises))
    q = mensuales.group_by(["iso_alpha3", "country", "month"]).agg(
        pl.len().alias("observaciones"),
        pl.col("temperature_c").mean().round(2).alias("temperature_mean"),
    )
    return q.sort(["country", "month"])


def resumen_anual_desde_mensuales(
    mensuales: pl.DataFrame | pl.LazyFrame,
    paises: list[str] | tuple[str, ...] | None = None,
) -> pl.DataFrame | pl.LazyFrame:
    """Calcula medias anuales usando únicamente filas mensuales."""
    if paises is not None:
        mensuales = mensuales.filter(pl.col("iso_alpha3").is_in(paises))
    q = mensuales.group_by(["iso_alpha3", "country", "year"]).agg(
        pl.len().alias("meses_disponibles"),
        pl.col("temperature_c").mean().round(2).alias("temperature_mean"),
    )
    return q.sort(["country", "year"])


def anomalias_mensuales(
    mensuales: pl.DataFrame | pl.LazyFrame,
    umbral: float = 2.0,
) -> pl.DataFrame | pl.LazyFrame:
    """Marca anomalías usando una ventana por país y mes."""
    q = (
        mensuales.with_columns(
            temperature_mean_month=pl.col("temperature_c")
            .mean()
            .over(["iso_alpha3", "month"])
        )
        .with_columns(
            standardized_anomaly=(
                (pl.col("temperature_c") - pl.col("temperature_mean_month"))
                / pl.col("temperature_c").std().over(["iso_alpha3", "month"])
            )
        )
        .with_columns(
            is_anomaly=(
                pl.col("standardized_anomaly").abs() > umbral
            ).fill_null(False)
        )
    )
    return q.sort(["country", "year", "month"])
