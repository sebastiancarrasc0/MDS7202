"""Etapa 0: repetir una consulta idéntica no gasta una solicitud nueva."""

from pathlib import Path

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from src.reposicion.cache import CacheSQLite, EmbeddingsConCache

from .conftest import ModeloFalso, final

pytestmark = pytest.mark.etapa0


def test_la_segunda_consulta_identica_sale_del_cache(tmp_path: Path):
    cache = CacheSQLite(tmp_path / "llm.sqlite")
    modelo = ModeloFalso(guion=[final(respuesta="uno")], cache=cache)
    primera = modelo.invoke("¿cuánta merluza queda?")
    segunda = modelo.invoke("¿cuánta merluza queda?")
    assert modelo.paso == 1
    assert (cache.aciertos, cache.fallos) == (1, 1)
    assert primera.content == segunda.content


def test_una_consulta_distinta_si_llama_al_modelo(tmp_path: Path):
    modelo = ModeloFalso(
        guion=[final(respuesta="uno")], cache=CacheSQLite(tmp_path / "c.sqlite")
    )
    modelo.invoke("una")
    modelo.invoke("otra")
    assert modelo.paso == 2


def test_el_cache_sobrevive_al_reinicio_y_se_puede_borrar(tmp_path: Path):
    ruta = tmp_path / "llm.sqlite"
    CacheSQLite(ruta).update("p", "m", [])
    reabierto = CacheSQLite(ruta)
    assert reabierto.lookup("p", "m") == []
    reabierto.clear()
    assert reabierto.lookup("p", "m") is None


class _EmbeddingsContados(DeterministicFakeEmbedding):
    llamadas: int = 0

    def embed_documents(self, texts):
        self.llamadas += 1
        return super().embed_documents(texts)


def test_los_embeddings_repetidos_salen_del_cache(tmp_path: Path):
    base = _EmbeddingsContados(size=8)
    cache = EmbeddingsConCache(base, tmp_path / "e.sqlite", "modelo-x")
    primero = cache.embed_documents(["merluza", "tomate"])
    segundo = cache.embed_documents(["merluza", "tomate"])
    assert primero == segundo
    assert base.llamadas == 1
    assert cache.llamadas_al_modelo == 1


def test_solo_se_piden_los_textos_nuevos(tmp_path: Path):
    base = _EmbeddingsContados(size=8)
    cache = EmbeddingsConCache(base, tmp_path / "e.sqlite", "modelo-x")
    cache.embed_documents(["merluza"])
    cache.embed_documents(["merluza", "palta"])
    assert base.llamadas == 2


def test_los_textos_nuevos_se_piden_en_lotes_pequenos(tmp_path: Path):
    base = _EmbeddingsContados(size=8)
    cache = EmbeddingsConCache(
        base, tmp_path / "e.sqlite", "modelo-x", tamano_lote=4
    )
    cache.embed_documents([f"texto {n}" for n in range(10)])
    assert base.llamadas == 3  # 4 + 4 + 2


def test_si_un_lote_falla_lo_ya_calculado_queda_guardado(tmp_path: Path):
    class _FallaAlSegundoLote(_EmbeddingsContados):
        def embed_documents(self, texts):
            if self.llamadas == 1:
                self.llamadas += 1
                raise TimeoutError("504")
            return super().embed_documents(texts)

    ruta = tmp_path / "e.sqlite"
    textos = [f"texto {n}" for n in range(8)]
    base = _FallaAlSegundoLote(size=8)
    cache = EmbeddingsConCache(base, ruta, "modelo-x", tamano_lote=4)
    with pytest.raises(TimeoutError):
        cache.embed_documents(textos)

    reintento = _EmbeddingsContados(size=8)
    cache = EmbeddingsConCache(reintento, ruta, "modelo-x", tamano_lote=4)
    cache.embed_documents(textos)
    assert reintento.llamadas == 1  # solo el lote que faltaba
