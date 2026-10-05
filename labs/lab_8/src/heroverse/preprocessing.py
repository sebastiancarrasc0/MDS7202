"""Preprocesador tabular reutilizable para el catálogo y los personajes nuevos."""

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    FunctionTransformer,
    OneHotEncoder,
    RobustScaler,
    StandardScaler,
)


def construir_preprocesador(
    puntajes: list[str],
    medidas: list[str],
    categoricas: list[str],
    binarias: list[str],
    min_frequency: int = 10,
) -> Pipeline:
    """Arma el preprocesador por familia de columnas, sin ajustarlo.

    - `puntajes`: imputación por mediana y estandarización.
    - `medidas`: imputación por mediana, `log1p` y escalamiento robusto, para
      variables sesgadas con colas largas como el peso.
    - `categoricas`: nulo como categoría `"desconocido"` y one-hot; las
      categorías con menos de `min_frequency` apariciones comparten una
      columna de infrecuentes. Las nuevas usan esa columna si existe;
      si no, el bloque de esa variable queda en ceros.
    - `binarias`: columnas `poder_*` generadas con el encoder ajustado
      al catálogo; pasan sin cambios.

    El resultado es un `Pipeline` con un único paso, `"columnas"`, que es un
    `ColumnTransformer` con `verbose_feature_names_out=False`. Su salida es un
    DataFrame de Polars: las columnas numéricas y binarias conservan su
    nombre, y las one-hot se llaman `<columna>_<categoría>`, con
    `<columna>_infrequent_sklearn` para las infrecuentes.
    """
    pipeline_puntajes = Pipeline(
        [
            ("imputar", SimpleImputer(strategy="median")),
            ("escalar", StandardScaler()),
        ]
    )
    pipeline_medidas = Pipeline(
        [
            ("imputar", SimpleImputer(strategy="median")),
            (
                "log",
                FunctionTransformer(np.log1p, feature_names_out="one-to-one"),
            ),
            ("escalar", RobustScaler()),
        ]
    )
    pipeline_categorico = Pipeline(
        [
            (
                "imputar",
                SimpleImputer(
                    missing_values=None,
                    strategy="constant",
                    fill_value="desconocido",
                ),
            ),
            (
                "codificar",
                OneHotEncoder(
                    min_frequency=min_frequency,
                    handle_unknown="infrequent_if_exist",
                    sparse_output=False,
                ),
            ),
        ]
    )
    columnas = ColumnTransformer(
        [
            ("puntajes", pipeline_puntajes, puntajes),
            ("medidas", pipeline_medidas, medidas),
            ("categoricas", pipeline_categorico, categoricas),
            ("binarias", "passthrough", binarias),
        ],
        verbose_feature_names_out=False,
    )
    return Pipeline([("columnas", columnas)]).set_output(transform="polars")
