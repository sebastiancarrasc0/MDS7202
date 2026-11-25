"""Etapa 0: el modelo y los embeddings se crean según el modo y la configuración."""

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.globals import get_llm_cache, set_llm_cache
from langchain_openai import ChatOpenAI

from src.reposicion.cache import CacheSQLite, EmbeddingsConCache
from src.reposicion.config import ErrorConfiguracion, Settings
from src.reposicion.modelo_simulado import ModeloSimulado
from src.reposicion.modelos_llm import (
    activar_cache_llm,
    crear_embeddings,
    crear_modelo_chat,
)

pytestmark = pytest.mark.etapa0


def _settings(**campos) -> Settings:
    return Settings(_env_file=None, **campos)  # pyright: ignore[reportCallIssue]


def test_el_modelo_real_apunta_a_openrouter_con_el_modelo_configurado():
    modelo = crear_modelo_chat(
        _settings(openrouter_api_key="sk-or-x", modelo_chat="a/b:free")
    )
    assert isinstance(modelo, ChatOpenAI)
    assert modelo.model_name == "a/b:free"
    assert "openrouter.ai" in str(modelo.openai_api_base)


def test_sin_llave_el_modo_real_explica_que_falta():
    with pytest.raises(ErrorConfiguracion, match="OPENROUTER_API_KEY"):
        crear_modelo_chat(_settings())


def test_el_modo_simulado_no_necesita_llaves():
    settings = _settings(REPOSICION_MODO="simulado")
    assert isinstance(crear_modelo_chat(settings), ModeloSimulado)
    assert isinstance(crear_embeddings(settings), DeterministicFakeEmbedding)


def test_los_embeddings_reales_llevan_cache_si_esta_activado():
    settings = _settings(openrouter_api_key="sk-or-x")
    assert isinstance(crear_embeddings(settings), EmbeddingsConCache)


def test_el_cache_se_puede_desactivar():
    settings = _settings(openrouter_api_key="sk-or-x", usar_cache=False)
    assert not isinstance(crear_embeddings(settings), EmbeddingsConCache)
    assert activar_cache_llm(settings) is None
    assert get_llm_cache() is None


def test_activar_el_cache_lo_deja_como_cache_global():
    try:
        cache = activar_cache_llm(_settings())
        assert isinstance(cache, CacheSQLite)
        assert get_llm_cache() is cache
    finally:
        set_llm_cache(None)
