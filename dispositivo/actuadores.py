"""
actuadores.py - Abstracciones de los actuadores del invernadero.

Relés (ventilador, bomba), LEDs (luz de crecimiento, alarma), buzzer y
pantalla LCD. Cada clase oculta los detalles del GPIO y expone una
interfaz sencilla: encender(), apagar(), establecer(valor), estado.
"""

import time
from machine import I2C, PWM, Pin

from lcd_i2c import LcdI2C


class SalidaDigital:
    """Salida GPIO on/off. Base para relés y LEDs."""

    def __init__(self, pin, nombre):
        self.nombre = nombre
        self._pin = Pin(pin, Pin.OUT, value=0)
        self._estado = False

    @property
    def estado(self):
        return self._estado

    def establecer(self, encendido):
        self._estado = bool(encendido)
        self._pin.value(1 if self._estado else 0)

    def encender(self):
        self.establecer(True)

    def apagar(self):
        self.establecer(False)


class Rele(SalidaDigital):
    """Módulo relé (activo en alto). Conmuta cargas como ventilador o bomba."""


class Led(SalidaDigital):
    """LED indicador o de iluminación."""


class Buzzer:
    """Buzzer pasivo manejado por PWM.

    En modo alarma suena de forma intermitente SIN bloquear el programa:
    `actualizar()` se llama en cada vuelta del bucle principal y alterna
    el sonido según el tiempo transcurrido.
    """

    def __init__(self, pin, frecuencia=2000, periodo_ms=500):
        self._pwm = PWM(Pin(pin), freq=frecuencia)
        self._pwm.duty_u16(0)
        self._periodo = periodo_ms
        self._alarma = False
        self._sonando = False
        self._ultimo_cambio = time.ticks_ms()

    @property
    def estado(self):
        return self._alarma

    def establecer(self, alarma):
        self._alarma = bool(alarma)
        if not self._alarma:
            self._silenciar()

    def actualizar(self):
        if not self._alarma:
            return
        ahora = time.ticks_ms()
        if time.ticks_diff(ahora, self._ultimo_cambio) >= self._periodo:
            self._ultimo_cambio = ahora
            if self._sonando:
                self._silenciar()
            else:
                self._pwm.duty_u16(32768)  # 50 % de ciclo útil
                self._sonando = True

    def _silenciar(self):
        self._pwm.duty_u16(0)
        self._sonando = False


class PantallaLCD:
    """LCD 16x2 por I2C para mostrar lecturas y estado localmente."""

    def __init__(self, sda, scl, direccion):
        i2c = I2C(0, sda=Pin(sda), scl=Pin(scl), freq=400000)
        self._lcd = LcdI2C(i2c, direccion, 16, 2)

    def mostrar(self, linea1, linea2=""):
        for fila, texto in enumerate((linea1, linea2)):
            self._lcd.mover(0, fila)
            self._lcd.escribir("{:<16}".format(texto)[:16])
