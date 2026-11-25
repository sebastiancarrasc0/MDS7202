"""Etapa 2: la fragmentación parte cada política en una regla por fragmento."""

import re

import pytest

from src.reposicion.contratos import TAMANO_MAXIMO
from src.reposicion.rag import fragmentar_politica

from .conftest import POLITICAS

pytestmark = pytest.mark.etapa2

DOCUMENTOS = sorted(POLITICAS.glob("*.md"))
EJEMPLO = """# Política de bodega\n\n## Cobertura mínima\n\nLa cobertura mínima es de 3 días.\n\n## Urgencia\n\nBajo 1 día es urgente.\n"""


def test_cada_fragmento_conserva_su_archivo_y_su_ruta_de_seccion():
    fragmentos = fragmentar_politica(EJEMPLO, "bodega.md")
    assert [f.metadata["ruta_seccion"] for f in fragmentos] == [
        "Política de bodega > Cobertura mínima",
        "Política de bodega > Urgencia",
    ]
    assert {f.metadata["archivo"] for f in fragmentos} == {"bodega.md"}
    assert [f.metadata["indice"] for f in fragmentos] == [0, 1]


def test_la_ruta_se_antepone_al_texto_del_fragmento():
    primero = fragmentar_politica(EJEMPLO, "bodega.md")[0]
    assert primero.page_content.startswith(
        "Política de bodega > Cobertura mínima"
    )
    assert "3 días" in primero.page_content


def test_un_fragmento_no_mezcla_dos_secciones():
    for fragmento in fragmentar_politica(EJEMPLO, "bodega.md"):
        assert not (
            "3 días" in fragmento.page_content
            and "Bajo 1 día" in fragmento.page_content
        )


def test_una_seccion_larga_se_parte_sin_cambiar_de_ruta():
    largo = "# Doc\n\n## Regla larga\n\n" + (
        "La merluza se guarda sobre hielo. " * 120
    )
    fragmentos = fragmentar_politica(largo, "largo.md")
    assert len(fragmentos) > 1
    assert {f.metadata["ruta_seccion"] for f in fragmentos} == {
        "Doc > Regla larga"
    }
    assert [f.metadata["indice"] for f in fragmentos] == list(
        range(len(fragmentos))
    )


@pytest.mark.parametrize("documento", DOCUMENTOS, ids=lambda d: d.name)
def test_los_documentos_reales_dan_un_fragmento_por_regla(documento):
    texto = documento.read_text(encoding="utf-8")
    secciones_con_texto = [
        s
        for s in re.split(r"^#{2,3} ", texto, flags=re.MULTILINE)[1:]
        if s.split("\n", 1)[1].strip()
    ]
    fragmentos = fragmentar_politica(texto, documento.name)
    assert len(fragmentos) == len(secciones_con_texto)
    assert all(len(f.page_content) <= TAMANO_MAXIMO + 200 for f in fragmentos)
    assert all(f.metadata["archivo"] == documento.name for f in fragmentos)
