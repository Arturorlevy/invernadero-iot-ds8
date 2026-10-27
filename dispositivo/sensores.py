"""
sensores.py - Abstracciones de los sensores del invernadero.

Cada clase encapsula el acceso al GPIO de un sensor y devuelve valores
ya convertidos a unidades útiles (°C, %), de modo que el resto del
programa no necesita saber cómo se lee cada componente.
"""

import dht
from machine import ADC, Pin


class SensorDHT22:
    """Temperatura (°C) y humedad relativa del aire (%) por bus de un hilo."""

    def __init__(self, pin):
        self._sensor = dht.DHT22(Pin(pin))

    def leer(self):
        self._sensor.measure()  # puede lanzar OSError si el sensor no responde
        return {
            "temperatura": round(self._sensor.temperature(), 1),
            "humedad": round(self._sensor.humidity(), 1),
        }


class SensorAnalogico:
    """Sensor analógico genérico que entrega un porcentaje 0-100 %.

    Se usa ATTN_11DB para medir el rango completo 0-3.3 V del ADC del ESP32.
    `invertir=True` sirve para sensores cuyo voltaje BAJA cuando la magnitud
    SUBE (como el módulo LDR de Wokwi: más luz -> menor voltaje en AO).
    """

    def __init__(self, pin, invertir=False):
        self._adc = ADC(Pin(pin))
        self._adc.atten(ADC.ATTN_11DB)
        self._invertir = invertir

    def porcentaje(self):
        bruto = self._adc.read_u16()          # 0 .. 65535
        valor = bruto * 100.0 / 65535
        if self._invertir:
            valor = 100.0 - valor
        return round(valor, 1)


class SensorLuz(SensorAnalogico):
    """Luminosidad relativa (%) a partir del módulo fotorresistor (LDR)."""

    def __init__(self, pin):
        super().__init__(pin, invertir=True)


class SensorHumedadSuelo(SensorAnalogico):
    """Humedad del suelo (%). En Wokwi se simula con un potenciómetro."""

    def __init__(self, pin):
        super().__init__(pin, invertir=False)


class GestorSensores:
    """Agrupa todos los sensores y produce una única lectura consolidada."""

    def __init__(self, pin_dht, pin_ldr, pin_suelo):
        self.dht = SensorDHT22(pin_dht)
        self.luz = SensorLuz(pin_ldr)
        self.suelo = SensorHumedadSuelo(pin_suelo)

    def leer_todo(self):
        datos = self.dht.leer()
        datos["luminosidad"] = self.luz.porcentaje()
        datos["humedad_suelo"] = self.suelo.porcentaje()
        return datos
