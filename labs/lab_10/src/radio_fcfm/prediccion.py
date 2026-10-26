"""Predicción del ánimo de canciones nuevas."""

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

from src.radio_fcfm.data import limpiar_letra
from src.radio_fcfm.evaluation import a_franja


def predecir_animo(modelo: Pipeline, letras: Sequence[str]) -> pd.DataFrame:
    """Predice el ánimo, la franja y la confianza de cada letra.

    `modelo` es un `Pipeline` ya ajustado que entrega `predict_proba`. Cada
    letra se limpia con `limpiar_letra`, igual que las del entrenamiento. El
    resultado tiene una fila por letra, en el mismo orden, con tres columnas:
    `animo` (la clase de mayor probabilidad), `franja` (la franja de
    programación de ese ánimo, según `a_franja`) y `confianza` (la
    probabilidad de la clase elegida, entre 0 y 1). La confianza no está
    calibrada: no es la probabilidad real de acertar.
    """
    if not letras:
        return pd.DataFrame(columns=["animo", "franja", "confianza"])
    limpias = [limpiar_letra(letra) for letra in letras]
    probabilidades = modelo.predict_proba(limpias)
    mejores = probabilidades.argmax(axis=1)
    clases = np.asarray(modelo.classes_)
    animos = [str(clases[i]) for i in mejores]
    return pd.DataFrame(
        {
            "animo": animos,
            "franja": [a_franja(animo) for animo in animos],
            "confianza": probabilidades[np.arange(len(mejores)), mejores],
        }
    )
