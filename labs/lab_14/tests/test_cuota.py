"""Etapa 0: la cuota se lee de OpenRouter y los errores se explican."""

import httpx
import pytest

from src.reposicion.config import Settings
from src.reposicion.cuota import consultar_cuota, traducir_error

pytestmark = pytest.mark.etapa0


def _settings(llave: str | None) -> Settings:
    campos = {"openrouter_api_key": llave} if llave else {}
    return Settings(_env_file=None, **campos)  # pyright: ignore[reportCallIssue]


def _cliente(estado: int, cuerpo: dict | None = None) -> httpx.Client:
    def responder(peticion: httpx.Request) -> httpx.Response:
        assert peticion.url.path.endswith("/key")
        assert peticion.headers["authorization"] == "Bearer llave-x"
        return httpx.Response(estado, json=cuerpo or {})

    return httpx.Client(transport=httpx.MockTransport(responder))


def test_lee_las_solicitudes_usadas_y_el_limite():
    cuerpo = {"data": {"free_model_daily_requests": {"used": 12, "limit": 50}}}
    cuota = consultar_cuota(_settings("llave-x"), _cliente(200, cuerpo))
    assert cuota is not None
    assert (cuota.usadas, cuota.limite, cuota.restantes) == (12, 50, 38)


def test_sin_llave_no_hay_cuota():
    assert consultar_cuota(_settings(None), _cliente(200)) is None


@pytest.mark.parametrize("estado", [401, 429, 500])
def test_un_error_http_no_rompe_la_consulta(estado: int):
    assert consultar_cuota(_settings("llave-x"), _cliente(estado)) is None


def test_una_respuesta_sin_el_dato_devuelve_none():
    assert (
        consultar_cuota(_settings("llave-x"), _cliente(200, {"data": {}}))
        is None
    )


class _ErrorHttp(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__("error")
        self.status_code = status_code


def test_el_error_429_se_explica_con_los_limites():
    mensaje = traducir_error(_ErrorHttp(429))
    assert "20 solicitudes por minuto" in mensaje
    assert "50 por día" in mensaje


def test_el_429_del_proveedor_no_se_atribuye_a_la_cuenta():
    error = _ErrorHttp(429)
    error.args = ("Error code: 429 - Provider returned error",)
    mensaje = traducir_error(error)
    assert "MODELO_CHAT" in mensaje
    assert "50 por día" not in mensaje


def test_el_error_de_llave_nombra_la_variable():
    assert "OPENROUTER_API_KEY" in traducir_error(_ErrorHttp(401))
