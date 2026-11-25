"""RAG sobre las políticas: fragmentar, ingestar y consultar (lo escribe el equipo).

`abrir_coleccion`, `contar_fragmentos` y `borrar_coleccion` vienen dados.
"""

import contextlib
from pathlib import Path
from typing import Any

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.reposicion.config import Settings
from src.reposicion.contratos import (
    COLECCION,
    FragmentoPolitica,
    ResumenIngesta,
)


class ErrorEmbeddings(RuntimeError):
    """La base se creó con otro modelo de embeddings."""


def _cliente(settings: Settings) -> Any:
    # Ruta absoluta: Chroma comparte el estado de cada ruta dentro del proceso.
    return chromadb.PersistentClient(
        path=str(settings.directorio_chroma.resolve())
    )


def abrir_coleccion(settings: Settings, embeddings: Embeddings) -> Chroma:
    """Abre (o crea) la base de políticas, que recuerda su modelo de embeddings.

    Si la base se creó con un modelo distinto del actual, se niega con un mensaje
    claro: mezclar modelos produce vectores de otra dimensión y Chroma falla con
    un error confuso.
    """
    cliente = _cliente(settings)
    coleccion = cliente.get_or_create_collection(
        COLECCION,
        metadata={
            "modelo_embeddings": settings.modelo_embeddings,
            "hnsw:space": "cosine",
        },
    )
    guardado = (coleccion.metadata or {}).get("modelo_embeddings")
    if guardado != settings.modelo_embeddings:
        raise ErrorEmbeddings(
            f"La base se creó con el modelo «{guardado}» y ahora se usa "
            f"«{settings.modelo_embeddings}»: los vectores no son compatibles. "
            f"Vuelvan a ingerir los documentos (borren `{settings.directorio_chroma}`)."
        )
    return Chroma(
        client=cliente, collection_name=COLECCION, embedding_function=embeddings
    )


def contar_fragmentos(coleccion: Chroma) -> int:
    """Cuántos fragmentos hay en la base."""
    return len(coleccion.get()["ids"])


def borrar_coleccion(settings: Settings) -> None:
    """Borra la colección de políticas, para volver a ingerir desde cero."""
    with contextlib.suppress(ValueError):  # todavía no existía
        _cliente(settings).delete_collection(COLECCION)


def fragmentar_politica(texto: str, archivo: str) -> list[Document]:
    """Parte un documento Markdown en fragmentos, uno por regla.

    Cada fragmento lleva como metadatos el `archivo`, la `ruta_seccion` (los
    encabezados separados por ` > `) y su `indice` dentro del documento, y
    antepone la ruta a su texto para que la regla no pierda su contexto. Una
    sección muy larga se parte por tamaño sin mezclarse con otra.
    """
    raise NotImplementedError(
        "Completen fragmentar_politica antes de ejecutar esta celda."
    )


def ingestar_politicas(carpeta: Path, coleccion: Any) -> ResumenIngesta:
    """Lee los `.md` de `carpeta`, los fragmenta y los guarda en la base.

    Es idempotente: el identificador de cada fragmento sale del archivo y de su
    índice, así que ingerir dos veces los mismos documentos no duplica nada.
    """
    archivos = sorted(carpeta.glob("*.md"))
    documentos: list[Document] = []
    for ruta in archivos:
        documentos += fragmentar_politica(
            ruta.read_text(encoding="utf-8"), ruta.name
        )
    ids = [
        f"{d.metadata['archivo']}::{d.metadata['indice']}" for d in documentos
    ]
    coleccion.add_documents(documentos, ids=ids)
    return ResumenIngesta(
        archivos=len(archivos),
        fragmentos=len(documentos),
        total_en_coleccion=contar_fragmentos(coleccion),
    )


def consultar_politicas(
    coleccion: Any,
    consulta: str,
    k: int = 3,
    distancia_maxima: float = 0.75,
) -> list[FragmentoPolitica]:
    """Los `k` fragmentos más parecidos a la consulta que sean relevantes.

    Un fragmento es relevante si su distancia a la consulta no supera
    `distancia_maxima`; si ninguno lo es, devuelve una lista vacía.
    """
    resultados = coleccion.similarity_search_with_score(consulta, k=k)
    return [
        FragmentoPolitica(
            archivo=documento.metadata["archivo"],
            ruta_seccion=documento.metadata["ruta_seccion"],
            texto=documento.page_content,
            distancia=distancia,
        )
        for documento, distancia in resultados
        if distancia <= distancia_maxima
    ]
