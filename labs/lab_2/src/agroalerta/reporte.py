from src.agroalerta.sensores import Sensor


def contar_riesgos(
    sensores: list[Sensor], lecturas: dict[str, list[float]]
) -> dict[str, bool]:
    riesgos = {}

    for sensor in sensores:
        n_riesgos = 0
        for nombre, valores in lecturas.items():
            if sensor.nombre == nombre:
                for valor in valores:
                    n_riesgos += 1 if sensor.es_riesgo(valor) else 0
        riesgos[sensor.nombre] = n_riesgos
    return riesgos
