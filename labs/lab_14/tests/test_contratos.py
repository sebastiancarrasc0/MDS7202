"""Etapa 0: los modelos que vienen dados rechazan datos inválidos y se explican."""

import pytest
from pydantic import ValidationError

from src.reposicion.contratos import (
    ErrorHerramienta,
    ReservaBodega,
    ReservasProducto,
    RespuestaAgente,
)

pytestmark = pytest.mark.etapa0

RESERVA = {
    "bodega": "Coronel",
    "ciudad": "Coronel",
    "cantidad": 90,
    "unidad": "kg",
    "consumo_diario": 60,
    "dias_cobertura": 1.5,
}


def test_una_reserva_valida_se_acepta():
    assert ReservaBodega(**RESERVA).dias_cobertura == 1.5


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("cantidad", -1),
        ("consumo_diario", 0),
        ("dias_cobertura", -0.5),
        ("bodega", ""),
        ("unidad", "toneladas"),
    ],
)
def test_un_dato_invalido_se_rechaza_nombrando_el_campo(campo: str, valor):
    with pytest.raises(ValidationError) as error:
        ReservaBodega(**{**RESERVA, campo: valor})
    assert campo in str(error.value)


def test_un_producto_necesita_al_menos_una_reserva():
    with pytest.raises(ValidationError, match="reservas"):
        ReservasProducto(producto="merluza", reservas=[])


def test_el_error_de_herramienta_solo_acepta_tipos_conocidos():
    assert ErrorHerramienta(tipo="no_encontrado", mensaje="No existe").tipo
    with pytest.raises(ValidationError, match="tipo"):
        ErrorHerramienta(tipo="explotó", mensaje="no sé")  # type: ignore[arg-type]


def test_una_respuesta_minima_se_acepta_y_trae_sus_valores_por_omision():
    respuesta = RespuestaAgente(respuesta="Quedan 90 kg.")
    assert respuesta.politicas_citadas == []


def test_una_respuesta_completa_conserva_sus_campos():
    respuesta = RespuestaAgente(
        respuesta="Hay que reponer.",
        politicas_citadas=["pescado.md"],
    )
    assert respuesta.politicas_citadas == ["pescado.md"]


def test_la_respuesta_no_puede_estar_vacia_ni_pasar_de_1500_caracteres():
    for texto in ("", "x" * 1501):
        with pytest.raises(ValidationError, match="respuesta"):
            RespuestaAgente(respuesta=texto)
    assert RespuestaAgente(respuesta="x" * 1500)


def test_las_listas_por_omision_no_se_comparten_entre_respuestas():
    primera = RespuestaAgente(respuesta="uno")
    primera.politicas_citadas.append("pescado.md")
    assert RespuestaAgente(respuesta="dos").politicas_citadas == []


def test_cada_campo_tiene_su_descripcion():
    assert RespuestaAgente.model_fields, "RespuestaAgente no declara campos."
    for nombre, campo in RespuestaAgente.model_fields.items():
        assert campo.description, (
            f"RespuestaAgente.{nombre} no tiene description."
        )
