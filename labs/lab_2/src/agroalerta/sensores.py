class Sensor:
    def __init__(self, nombre: str, unidad: str):
        self.nombre = nombre
        self.unidad = unidad

    def es_riesgo(self, valor: float) -> bool:
        return False


class SensorTemperatura(Sensor):
    def __init__(self, minimo: float, maximo: float) -> None:
        super().__init__("temperatura", "°C")
        self.minimo = minimo
        self.maximo = maximo

    def es_riesgo(self, valor: float) -> bool:
        return valor < self.minimo or valor > self.maximo


class SensorViento(Sensor):
    def __init__(self, maximo: float) -> None:
        super().__init__("viento", "km/s")
        self.maximo = maximo

    def es_riesgo(self, valor: float) -> bool:
        return valor > self.maximo


class SensorHumedad(Sensor):
    def __init__(self, maximo: float) -> None:
        super().__init__("humedad", "%")
        self.maximo = maximo

    def es_riesgo(self, valor: float) -> bool:
        return valor > self.maximo
