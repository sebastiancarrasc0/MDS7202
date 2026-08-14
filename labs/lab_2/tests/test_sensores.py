from src.agroalerta.reporte import contar_riesgos
from src.agroalerta.sensores import (
    SensorHumedad,
    SensorTemperatura,
    SensorViento,
)


def test_temperatura_bajo_cero_es_riesgosa():
    sensor = SensorTemperatura(0, 40)
    assert sensor.es_riesgo(-2) is True


def test_temperatura_templada_no_es_riesgosa():
    sensor = SensorTemperatura(0, 40)
    assert sensor.es_riesgo(18) is False


def test_viento_normal_no_es_riesgoso():
    sensor = SensorViento(25)
    assert sensor.es_riesgo(10) is False


def test_contar_riesgos_conteo_correcto():
    sensores = [
        SensorTemperatura(0, 40),
        SensorViento(25),
        SensorHumedad(85),
    ]
    lecturas = {
        "temperatura": [18.5, 22.0, 35.0, 42.0],
        "viento": [10.5, 30.0, 20.0],
        "humedad": [70.5, 90.0, 80.0],
    }
    esperado = {"temperatura": 1, "viento": 1, "humedad": 1}
    assert contar_riesgos(sensores, lecturas) == esperado
