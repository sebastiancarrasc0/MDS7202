"""Carga del modelo desde su artefacto."""

from pathlib import Path
from typing import Any

import joblib
import sklearn
from sklearn.pipeline import Pipeline

from .artifacts import ErrorArtefacto, leer_metadata
from .constants import FEATURES


def cargar_modelo(directorio: Path) -> tuple[Pipeline, dict[str, Any]]:
    """Carga el artefacto de `directorio` y devuelve (modelo, metadata).

    Antes de cargar el modelo comprueba que las variables de la metadata sean
    exactamente `FEATURES`, en ese orden, y que `sklearn_version` coincida con
    la versión de scikit-learn instalada. Si algo no calza lanza
    `ErrorArtefacto` con un mensaje que nombra la diferencia.
    """
    metadata = leer_metadata(directorio)

    if list(metadata["features"]) != list(FEATURES):
        raise ErrorArtefacto(
            "Las variables del artefacto no calzan con el contrato: "
            f"el artefacto trae {list(metadata['features'])} y el contrato "
            f"espera {list(FEATURES)}."
        )

    if metadata["sklearn_version"] != sklearn.__version__:
        raise ErrorArtefacto(
            "La versión de scikit-learn no coincide: el artefacto se entrenó con "
            f"{metadata['sklearn_version']} y el servicio usa {sklearn.__version__}."
        )

    modelo = joblib.load(directorio / "model.joblib")
    return modelo, metadata
