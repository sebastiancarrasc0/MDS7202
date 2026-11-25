"""Etapa 0: las políticas son coherentes con los datos de las bodegas."""

import re

import pytest

from src.reposicion.servidor.datos import (
    COTIZACIONES_MINIMAS,
    MONTO_VISACION_GERENCIA_CLP,
    PRODUCTOS,
)

from .conftest import POLITICAS

pytestmark = pytest.mark.etapa0

# producto -> (nombre corto de las viñetas, documento)
DOCUMENTO_DE = {
    "merluza": ("Merluza", "pescado.md"),
    "salmon": ("Salmón", "pescado.md"),
    "tomate": ("Tomate", "tomate_y_palta.md"),
    "palta": ("Palta", "tomate_y_palta.md"),
    "lechuga": ("Lechuga", "lechuga.md"),
    "pollo": ("Pollo", "pollo.md"),
    "huevos": ("Huevos", "huevos.md"),
    "leche": ("Leche UHT", "leche_uht.md"),
}
SECCIONES = {
    "Cobertura mínima": "minima",
    "Urgencia": "urgencia",
    "Cobertura objetivo": "objetivo",
}
DOCUMENTOS = sorted(p.name for p in POLITICAS.glob("*.md"))


def _secciones(texto: str) -> dict[str, str]:
    partes = re.split(r"^## ", texto, flags=re.MULTILINE)[1:]
    return {p.split("\n", 1)[0].strip(): p.split("\n", 1)[1] for p in partes}


def _dias(seccion: str, nombre: str) -> int:
    patron = rf"^- {re.escape(nombre)}:.*\*\*(\d+) días?\*\*"
    encontrado = re.search(patron, seccion, flags=re.MULTILINE)
    assert encontrado, f"No hay una viñeta de «{nombre}» con su cifra."
    return int(encontrado.group(1))


def test_hay_diez_documentos():
    assert len(DOCUMENTOS) == 10


@pytest.mark.parametrize("archivo", DOCUMENTOS)
def test_cada_documento_tiene_un_titulo_y_secciones_con_texto(archivo: str):
    texto = (POLITICAS / archivo).read_text(encoding="utf-8")
    assert len(re.findall(r"^# ", texto, flags=re.MULTILINE)) == 1
    secciones = re.split(r"^#{2,3} ", texto, flags=re.MULTILINE)[1:]
    assert len(secciones) >= 5, f"{archivo} tiene pocas secciones."
    for seccion in secciones:
        cuerpo = seccion.split("\n", 1)[1].strip()
        assert cuerpo, (
            f"En {archivo}, la sección «{seccion.splitlines()[0]}» está vacía."
        )


@pytest.mark.parametrize("producto", sorted(PRODUCTOS))
def test_las_cifras_de_cada_producto_coinciden_con_los_datos(producto: str):
    nombre, archivo = DOCUMENTO_DE[producto]
    secciones = _secciones((POLITICAS / archivo).read_text(encoding="utf-8"))
    for titulo, clave in SECCIONES.items():
        assert titulo in secciones, f"A {archivo} le falta «{titulo}»."
        assert _dias(secciones[titulo], nombre) == PRODUCTOS[producto][clave], (
            f"{nombre}: la cifra de «{titulo}» no coincide con los datos."
        )


def test_el_monto_de_visacion_y_las_cotizaciones_coinciden():
    texto = (POLITICAS / "proveedores_y_compras.md").read_text(encoding="utf-8")
    monto = f"${MONTO_VISACION_GERENCIA_CLP:,}".replace(",", ".")
    assert monto in texto
    assert str(COTIZACIONES_MINIMAS) in texto
