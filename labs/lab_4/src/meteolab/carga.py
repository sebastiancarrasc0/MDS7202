"""Funciones de lectura del CSV que deben completar ustedes."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from src.meteolab.constantes import RUTA_CSV


def leer_temperaturas(ruta: Path = RUTA_CSV) -> pl.DataFrame:
    """Lee el CSV CRU con sus tipos y valores faltantes."""
    lectura = pl.read_csv(
        ruta, schema_overrides={"year": pl.Int64, "temperature_c": pl.Float64}
    )
    return lectura


def escanear_temperaturas(ruta: Path = RUTA_CSV) -> pl.LazyFrame:
    """Construye una consulta lazy sobre el CSV."""
    consulta = pl.scan_csv(
        ruta, schema_overrides={"year": pl.Int64, "temperature_c": pl.Float64}
    )
    return consulta
