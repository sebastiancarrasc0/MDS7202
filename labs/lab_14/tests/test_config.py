"""Etapa 0: la configuración se lee del entorno y no expone las llaves."""

from pathlib import Path

import pytest

from src.reposicion.config import Settings, get_settings, llaves_faltantes

pytestmark = pytest.mark.etapa0


def _settings(**campos) -> Settings:
    # `_env_file=None`: la prueba no debe leer el `.env` de quien la ejecuta.
    return Settings(_env_file=None, **campos)  # pyright: ignore[reportCallIssue]


def test_los_valores_por_defecto_sirven_sin_ninguna_variable():
    settings = _settings()
    assert settings.modo == "real"
    assert settings.modelo_chat.endswith(":free")
    assert settings.url_api_bodegas == "http://127.0.0.1:8100"
    assert settings.endpoint_phoenix == "http://localhost:6006/v1/traces"


def test_lee_las_variables_del_entorno(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MODELO_CHAT", "otro/modelo:free")
    monkeypatch.setenv("REPOSICION_MODO", "simulado")
    settings = _settings()
    assert settings.modelo_chat == "otro/modelo:free"
    assert settings.modo == "simulado"


def test_las_llaves_no_salen_al_imprimir(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-secreta-123")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-secreta-456")
    settings = _settings()
    assert "secreta" not in repr(settings)
    assert "secreta" not in str(settings)
    assert settings.openrouter_api_key.get_secret_value() == "sk-or-secreta-123"  # type: ignore[union-attr]


def test_las_llaves_faltantes_se_nombran(monkeypatch: pytest.MonkeyPatch):
    assert llaves_faltantes(_settings()) == [
        "OPENROUTER_API_KEY",
        "TAVILY_API_KEY",
    ]
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    assert llaves_faltantes(_settings()) == ["TAVILY_API_KEY"]


def test_una_variable_vacia_cuenta_como_ausente(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    assert _settings().openrouter_api_key is None


def test_lee_el_env_de_la_raiz_aunque_se_ejecute_desde_otra_carpeta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / ".env").write_text("TAVILY_API_KEY=desde-el-archivo\n")
    (tmp_path / "notebooks").mkdir()
    monkeypatch.chdir(tmp_path / "notebooks")
    settings = get_settings()
    assert settings.tavily_api_key.get_secret_value() == "desde-el-archivo"  # type: ignore[union-attr]


def test_las_carpetas_cuelgan_de_la_raiz_y_no_de_donde_se_ejecuta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("REPOSICION_RAIZ", str(tmp_path))
    monkeypatch.chdir(tmp_path.parent)
    settings = _settings()
    assert settings.directorio_chroma == tmp_path / "data/processed/chroma"
    assert settings.directorio_cache == tmp_path / ".cache"


def test_get_settings_lee_una_sola_vez(monkeypatch: pytest.MonkeyPatch):
    primera = get_settings()
    monkeypatch.setenv("MODELO_CHAT", "cambia/despues:free")
    assert get_settings() is primera


def test_el_archivo_de_ejemplo_no_trae_llaves_reales():
    ejemplo = (
        Path(__file__).resolve().parent.parent / ".env.example"
    ).read_text()
    for linea in ejemplo.splitlines():
        if linea.startswith(("OPENROUTER_API_KEY=", "TAVILY_API_KEY=")):
            assert linea.split("=", 1)[1].startswith("cambiar"), linea
