"""Datos ficticios y deterministas de Mar y Huerta (material provisto).

Son los mismos números cada vez que se importa el módulo. Se calibran contra las
políticas de `data/raw/politicas/`: una bodega necesita reposición (merluza en
Coronel), una está justo en el límite (tomate en Placilla) y un producto no
necesita reposición en ninguna bodega (leche UHT).
"""

import unicodedata

# Cobertura = días de consumo que alcanza el stock de una bodega.
# `minima`: bajo ese valor hace falta reponer. `urgencia`: bajo ese valor la
# reposición es urgente. `objetivo`: cobertura a la que se repone.
PRODUCTOS: dict[str, dict] = {
    "merluza": {
        "nombre": "Merluza austral",
        "unidad": "kg",
        "minima": 3,
        "urgencia": 1,
        "objetivo": 7,
    },
    "salmon": {
        "nombre": "Salmón atlántico",
        "unidad": "kg",
        "minima": 3,
        "urgencia": 1,
        "objetivo": 7,
    },
    "tomate": {
        "nombre": "Tomate larga vida",
        "unidad": "kg",
        "minima": 4,
        "urgencia": 2,
        "objetivo": 8,
    },
    "palta": {
        "nombre": "Palta hass",
        "unidad": "kg",
        "minima": 4,
        "urgencia": 2,
        "objetivo": 8,
    },
    "lechuga": {
        "nombre": "Lechuga escarola",
        "unidad": "unidades",
        "minima": 2,
        "urgencia": 1,
        "objetivo": 5,
    },
    "pollo": {
        "nombre": "Pollo entero",
        "unidad": "kg",
        "minima": 3,
        "urgencia": 1,
        "objetivo": 7,
    },
    "huevos": {
        "nombre": "Huevos blancos",
        "unidad": "bandejas",
        "minima": 5,
        "urgencia": 2,
        "objetivo": 10,
    },
    "leche": {
        "nombre": "Leche UHT",
        "unidad": "litros",
        "minima": 10,
        "urgencia": 4,
        "objetivo": 20,
    },
}

# Una orden sobre este monto, en pesos chilenos, requiere además la visación de
# la gerencia de abastecimiento.
MONTO_VISACION_GERENCIA_CLP = 3_000_000
COTIZACIONES_MINIMAS = 3

BODEGAS: dict[str, dict] = {
    "lo_espejo": {
        "nombre": "Lo Espejo",
        "ciudad": "Santiago",
        "region": "Metropolitana",
    },
    "placilla": {
        "nombre": "Placilla",
        "ciudad": "Valparaíso",
        "region": "Valparaíso",
    },
    "coronel": {"nombre": "Coronel", "ciudad": "Coronel", "region": "Biobío"},
    "alerce": {
        "nombre": "Alerce",
        "ciudad": "Puerto Montt",
        "region": "Los Lagos",
    },
}

# (producto, bodega, cantidad en stock, consumo diario)
_STOCK: list[tuple[str, str, float, float]] = [
    ("merluza", "lo_espejo", 420, 70),
    ("merluza", "placilla", 260, 50),
    ("merluza", "coronel", 90, 60),
    ("merluza", "alerce", 300, 40),
    ("salmon", "lo_espejo", 210, 60),
    ("salmon", "alerce", 500, 80),
    ("tomate", "lo_espejo", 800, 160),
    ("tomate", "placilla", 200, 50),
    ("tomate", "coronel", 300, 60),
    ("palta", "lo_espejo", 450, 90),
    ("palta", "placilla", 300, 60),
    ("lechuga", "lo_espejo", 300, 100),
    ("lechuga", "placilla", 120, 50),
    ("pollo", "lo_espejo", 900, 150),
    ("pollo", "coronel", 400, 100),
    ("pollo", "alerce", 250, 50),
    ("huevos", "lo_espejo", 600, 100),
    ("huevos", "placilla", 300, 50),
    ("huevos", "alerce", 200, 40),
    ("leche", "lo_espejo", 3000, 250),
    ("leche", "placilla", 1500, 120),
    ("leche", "coronel", 1000, 90),
    ("leche", "alerce", 800, 60),
]


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con guiones bajos: «Lo Espejo» → `lo_espejo`."""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return sin_tildes.strip().lower().replace(" ", "_")


def filas_de_stock() -> list[dict]:
    """Todas las filas de stock, con la cobertura calculada."""
    filas = []
    for producto_id, bodega_id, cantidad, consumo in _STOCK:
        producto = PRODUCTOS[producto_id]
        bodega = BODEGAS[bodega_id]
        filas.append(
            {
                "producto_id": producto_id,
                "producto": producto["nombre"],
                "bodega_id": bodega_id,
                "bodega": bodega["nombre"],
                "ciudad": bodega["ciudad"],
                "cantidad": cantidad,
                "unidad": producto["unidad"],
                "consumo_diario": consumo,
                "dias_cobertura": round(cantidad / consumo, 2),
            }
        )
    return filas
