"""Funciones para declarar y validar el esquema CRU."""

from __future__ import annotations

import pandera.polars as pa
import polars as pl
from pandera.errors import SchemaErrors

from src.meteolab.constantes import ESQUEMA_CRU, PERIODOS_VALIDOS

ESQUEMA_TEMPERATURAS = pa.DataFrameSchema(
    {
        "year": pa.Column(
            int, pa.Check.in_range(min_value=1901, max_value=2025)
        ),
        "period": pa.Column(str, pa.Check.isin(PERIODOS_VALIDOS)),
        "parameter": pa.Column(str, pa.Check.isin(["Mean Temperature"])),
        "units": pa.Column(str, pa.Check.isin(["degrees Celsius"])),
    }
)


def comparar_esquema(temperaturas: pl.DataFrame) -> list[str]:
    """Devuelve diferencias entre el esquema real y el esperado."""
    esquema_real = temperaturas.schema
    diferencias: list[str] = []

    for columna, tipo_esperado in ESQUEMA_CRU.items():
        if columna not in esquema_real:
            diferencias.append(f"Falta la columna {columna}")
        elif esquema_real[columna] != tipo_esperado:
            diferencias.append(
                f"Columna {columna} tiene tipo {esquema_real[columna]} "
                f"pero se esperaba {tipo_esperado}"
            )
    return diferencias


def validar_esquema(temperaturas: pl.DataFrame) -> None:
    """Comprueba los nombres y tipos de las columnas."""
    diferencias = comparar_esquema(temperaturas)
    if diferencias:
        raise ValueError(
            "El esquema no coincide con el esperado:\n" + "\n".join(diferencias)
        )


def validar_datos(temperaturas: pl.DataFrame) -> pl.DataFrame:
    """Valida tipos, periodos, unidades y valores faltantes."""
    return ESQUEMA_TEMPERATURAS.validate(
        temperaturas, lazy=True
    )  # lazy=True permite que se acumulen los errores y se entreguen todos juntos


def casos_que_fallan(temperaturas: pl.DataFrame) -> pl.DataFrame:
    """Devuelve los incumplimientos sin ocultar sus columnas."""
    try:
        validar_datos(temperaturas)
    except SchemaErrors as errores:
        return errores.failure_cases
    return pl.DataFrame()  # para cumplir con la firma
