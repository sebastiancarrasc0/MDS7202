import argparse
from pathlib import Path

from src.agroalerta.datos import cargar_lecturas
from src.agroalerta.reporte import contar_riesgos
from src.agroalerta.sensores import (
    SensorHumedad,
    SensorTemperatura,
    SensorViento,
)


def main():
    parser = argparse.ArgumentParser(description="AgroAlerta")
    parser.add_argument("--fecha", default="2026-06-15")
    args = parser.parse_args()

    ruta = Path(__file__).parent / "data" / "lecturas.csv"
    lecturas = cargar_lecturas(ruta, args.fecha)

    sensores = [
        SensorTemperatura(0, 40),
        SensorViento(25),
        SensorHumedad(85),
    ]
    riesgos = contar_riesgos(sensores, lecturas)
    print(f"Situaciones de riesgo en {args.fecha}: {riesgos}")


if __name__ == "__main__":
    main()
