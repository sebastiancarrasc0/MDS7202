"""Etapa 2: la ingesta es idempotente y la consulta devuelve fragmentos con fuente."""

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from src.reposicion.config import Settings
from src.reposicion.rag import (
    ErrorEmbeddings,
    abrir_coleccion,
    borrar_coleccion,
    consultar_politicas,
    contar_fragmentos,
    ingestar_politicas,
)

from .conftest import POLITICAS

pytestmark = pytest.mark.etapa2


def _settings(**campos) -> Settings:
    return Settings(_env_file=None, **campos)  # pyright: ignore[reportCallIssue]


@pytest.fixture
def coleccion():
    return abrir_coleccion(_settings(), DeterministicFakeEmbedding(size=32))


def test_ingerir_dos_veces_no_duplica_fragmentos(coleccion):
    primera = ingestar_politicas(POLITICAS, coleccion)
    segunda = ingestar_politicas(POLITICAS, coleccion)
    assert primera.archivos == 10
    assert primera.fragmentos > 50
    assert primera.total_en_coleccion == segunda.total_en_coleccion
    assert contar_fragmentos(coleccion) == primera.fragmentos


def test_la_consulta_devuelve_fragmentos_con_archivo_y_seccion(coleccion):
    ingestar_politicas(POLITICAS, coleccion)
    resultados = consultar_politicas(
        coleccion, "merluza", k=3, distancia_maxima=2.0
    )
    assert len(resultados) == 3
    for fragmento in resultados:
        assert fragmento.archivo.endswith(".md")
        assert " > " in fragmento.ruta_seccion


def test_un_texto_identico_a_un_fragmento_lo_encuentra_primero(coleccion):
    ingestar_politicas(POLITICAS, coleccion)
    texto = coleccion.get()["documents"][7]
    mejor = consultar_politicas(coleccion, texto, k=1, distancia_maxima=0.01)
    assert [f.texto for f in mejor] == [texto]


def test_sin_fragmentos_bajo_la_distancia_maxima_la_lista_es_vacia(coleccion):
    ingestar_politicas(POLITICAS, coleccion)
    assert (
        consultar_politicas(
            coleccion, "tema que nadie trata", distancia_maxima=0.0
        )
        == []
    )


def test_otro_modelo_de_embeddings_se_niega_y_explica_que_hay_que_reingerir():
    abrir_coleccion(
        _settings(modelo_embeddings="modelo/a"),
        DeterministicFakeEmbedding(size=32),
    )
    with pytest.raises(ErrorEmbeddings, match="Vuelvan a ingerir"):
        abrir_coleccion(
            _settings(modelo_embeddings="modelo/b"),
            DeterministicFakeEmbedding(size=64),
        )


def test_borrar_la_base_permite_cambiar_de_modelo(coleccion):
    ingestar_politicas(POLITICAS, coleccion)
    settings = _settings(modelo_embeddings="modelo/b")
    borrar_coleccion(_settings())
    nueva = abrir_coleccion(settings, DeterministicFakeEmbedding(size=64))
    assert contar_fragmentos(nueva) == 0
