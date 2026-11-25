"""Modelos de chat y de embeddings sobre OpenRouter (material provisto).

OpenRouter habla el mismo protocolo que OpenAI, así que `ChatOpenAI` y
`OpenAIEmbeddings` de LangChain funcionan apuntando a su dirección. Con
`REPOSICION_MODO=simulado` no se usa red ni llaves: responde un modelo de
reglas, útil para ensayar el código sin gastar la cuota.
"""

from langchain_core.caches import BaseCache
from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings
from langchain_core.globals import set_llm_cache
from langchain_core.language_models.chat_models import BaseChatModel

from src.reposicion.cache import CacheSQLite, EmbeddingsConCache
from src.reposicion.config import ErrorConfiguracion, Settings, get_settings


def _llave(settings: Settings) -> str:
    if settings.openrouter_api_key is None:
        raise ErrorConfiguracion(
            "Falta OPENROUTER_API_KEY. Defínanla en su archivo .env."
        )
    return settings.openrouter_api_key.get_secret_value()


def crear_modelo_chat(
    settings: Settings | None = None, nombre: str | None = None
) -> BaseChatModel:
    """Modelo de chat: el real de OpenRouter o el simulado, según el modo."""
    settings = settings or get_settings()
    if settings.modo == "simulado":
        from src.reposicion.modelo_simulado import ModeloSimulado

        return ModeloSimulado()
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=nombre or settings.modelo_chat,
        base_url=settings.url_openrouter,
        api_key=_llave(settings),  # pyright: ignore[reportArgumentType]
        max_retries=3,
        timeout=90,
    )


def crear_embeddings(settings: Settings | None = None) -> Embeddings:
    """Embeddings de OpenRouter, con caché en disco si está activado."""
    settings = settings or get_settings()
    if settings.modo == "simulado":
        return DeterministicFakeEmbedding(size=64)
    from langchain_openai import OpenAIEmbeddings

    base = OpenAIEmbeddings(
        model=settings.modelo_embeddings,
        base_url=settings.url_openrouter,
        api_key=_llave(settings),  # pyright: ignore[reportArgumentType]
        check_embedding_ctx_length=False,
        max_retries=3,
    )
    if not settings.usar_cache:
        return base
    return EmbeddingsConCache(
        base,
        settings.directorio_cache / "embeddings.sqlite",
        settings.modelo_embeddings,
    )


def activar_cache_llm(settings: Settings | None = None) -> BaseCache | None:
    """Activa el caché de respuestas del modelo (y lo devuelve), si corresponde."""
    settings = settings or get_settings()
    if not settings.usar_cache:
        set_llm_cache(None)
        return None
    cache = CacheSQLite(settings.directorio_cache / "llm.sqlite")
    set_llm_cache(cache)
    return cache
