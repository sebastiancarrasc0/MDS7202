"""Cachés de respuestas del modelo y de embeddings (material provisto).

Una consulta idéntica no vuelve a pedirse: se responde desde un archivo SQLite
en `.cache/`. Así repetir un ejercicio no gasta solicitudes de la cuota diaria.
"""

import hashlib
import json
import sqlite3
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from langchain_core.caches import RETURN_VAL_TYPE, BaseCache
from langchain_core.embeddings import Embeddings
from langchain_core.load import dumps, loads


class CacheSQLite(BaseCache):
    """Caché de respuestas del modelo de chat sobre un archivo SQLite."""

    def __init__(self, ruta: Path) -> None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(ruta, check_same_thread=False)
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS respuestas ("
            "prompt TEXT, modelo TEXT, valor TEXT, PRIMARY KEY (prompt, modelo))"
        )
        self.aciertos = 0
        self.fallos = 0

    def lookup(self, prompt: str, llm_string: str) -> RETURN_VAL_TYPE | None:
        fila = self._con.execute(
            "SELECT valor FROM respuestas WHERE prompt = ? AND modelo = ?",
            (prompt, llm_string),
        ).fetchone()
        if fila is None:
            self.fallos += 1
            return None
        self.aciertos += 1
        with warnings.catch_warnings():
            # `loads` avisa que su API es beta: el aviso no le sirve a quien aprende.
            warnings.simplefilter("ignore")
            return loads(fila[0], allowed_objects="core")

    def update(
        self, prompt: str, llm_string: str, return_val: RETURN_VAL_TYPE
    ) -> None:
        self._con.execute(
            "INSERT OR REPLACE INTO respuestas VALUES (?, ?, ?)",
            (prompt, llm_string, dumps(return_val)),
        )
        self._con.commit()

    def clear(self, **kwargs: Any) -> None:
        self._con.execute("DELETE FROM respuestas")
        self._con.commit()


class EmbeddingsConCache(Embeddings):
    """Envuelve unos embeddings y guarda cada vector que ya calculó.

    Pide los textos nuevos en lotes pequeños y guarda cada lote apenas llega: si
    el servicio falla a la mitad (un 504 por demora, por ejemplo), lo ya calculado
    queda guardado y al reintentar solo se piden los lotes que faltan.
    """

    def __init__(
        self,
        base: Embeddings,
        ruta: Path,
        modelo: str,
        tamano_lote: int = 16,
    ) -> None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self._base = base
        self._modelo = modelo
        self._tamano_lote = tamano_lote
        self._con = sqlite3.connect(ruta, check_same_thread=False)
        self._con.execute(
            "CREATE TABLE IF NOT EXISTS vectores ("
            "clave TEXT PRIMARY KEY, vector TEXT)"
        )
        self.llamadas_al_modelo = 0

    def _clave(self, texto: str) -> str:
        digest = hashlib.sha256(texto.encode()).hexdigest()
        return f"{self._modelo}:{digest}"

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        textos = list(texts)
        vectores: dict[int, list[float]] = {}
        pendientes: list[int] = []
        for i, texto in enumerate(textos):
            fila = self._con.execute(
                "SELECT vector FROM vectores WHERE clave = ?",
                (self._clave(texto),),
            ).fetchone()
            if fila is None:
                pendientes.append(i)
            else:
                vectores[i] = json.loads(fila[0])
        for inicio in range(0, len(pendientes), self._tamano_lote):
            lote = pendientes[inicio : inicio + self._tamano_lote]
            self.llamadas_al_modelo += 1
            nuevos = self._base.embed_documents([textos[i] for i in lote])
            for i, vector in zip(lote, nuevos, strict=True):
                vectores[i] = vector
                self._con.execute(
                    "INSERT OR REPLACE INTO vectores VALUES (?, ?)",
                    (self._clave(textos[i]), json.dumps(vector)),
                )
            self._con.commit()
        return [vectores[i] for i in range(len(textos))]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
