"""
lcd_i2c.py - Controlador mínimo para LCD HD44780 (16x2) con adaptador I2C PCF8574.

El PCF8574 convierte I2C en 8 salidas paralelas. El LCD se maneja en
modo de 4 bits, así que cada byte se envía en dos "nibbles":
    P0=RS  P1=RW  P2=E (enable)  P3=luz de fondo  P4..P7=D4..D7
"""

import time

_RS = 0x01
_E = 0x04
_LUZ = 0x08
_OFFSETS_FILA = (0x00, 0x40, 0x14, 0x54)


class LcdI2C:
    def __init__(self, i2c, direccion=0x27, columnas=16, filas=2):
        self.i2c = i2c
        self.direccion = direccion
        self.columnas = columnas
        self.filas = filas
        time.sleep_ms(50)
        # Secuencia de inicialización estándar para entrar en modo 4 bits
        for _ in range(3):
            self._escribir_nibble(0x30)
            time.sleep_ms(5)
        self._escribir_nibble(0x20)
        time.sleep_ms(1)
        self._comando(0x28)  # 4 bits, 2 líneas, fuente 5x8
        self._comando(0x0C)  # display encendido, sin cursor
        self._comando(0x06)  # el cursor avanza a la derecha
        self.limpiar()

    # -- bajo nivel ---------------------------------------------------------
    def _escribir_i2c(self, dato):
        self.i2c.writeto(self.direccion, bytes([dato | _LUZ]))

    def _escribir_nibble(self, nibble, rs=0):
        dato = (nibble & 0xF0) | rs
        self._escribir_i2c(dato | _E)   # flanco de subida en E
        time.sleep_us(1)
        self._escribir_i2c(dato)        # flanco de bajada: el LCD captura el dato
        time.sleep_us(50)

    def _enviar(self, valor, rs):
        self._escribir_nibble(valor & 0xF0, rs)
        self._escribir_nibble((valor << 4) & 0xF0, rs)

    def _comando(self, cmd):
        self._enviar(cmd, 0)
        if cmd in (0x01, 0x02):  # limpiar / home tardan más
            time.sleep_ms(2)

    # -- API pública --------------------------------------------------------
    def limpiar(self):
        self._comando(0x01)

    def mover(self, columna, fila):
        self._comando(0x80 | (columna + _OFFSETS_FILA[fila]))

    def escribir(self, texto):
        for caracter in texto:
            self._enviar(ord(caracter), _RS)
