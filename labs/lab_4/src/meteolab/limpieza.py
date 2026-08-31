"""Funciones para revisar nulos y claves temporales."""

from __future__ import annotations

import polars as pl

from src.meteolab.constantes import PERIODOS_MENSUALES, Tabla


def resumen_de_nulos(temperaturas: pl.DataFrame) -> pl.DataFrame:
    """Devuelve conteos y porcentajes de nulos por columna."""
    N = temperaturas.shape[0]
    return pl.DataFrame(
        {
            "columna": temperaturas.columns,
            "nulos": [
                temperaturas[col].null_count() for col in temperaturas.columns
            ],
            "porcentaje": [
                100 * temperaturas[col].null_count() / N
                for col in temperaturas.columns
            ],
        }
    )


def claves_repetidas(temperaturas: Tabla) -> Tabla:
    """Cuenta repeticiones de país, año y periodo."""
    q = (
        temperaturas.group_by(["country", "year", "period"])
        .agg(pl.len())
        .filter(pl.col("len") > 1)
    )
    return q


def limpiar_temperaturas(temperaturas: Tabla) -> Tabla:
    """Conserva el contrato de periodos y los nulos válidos."""
    return temperaturas.filter(
        pl.col("period").is_in(PERIODOS_MENSUALES)
        & pl.col("temperature_c").is_not_null()
    )
