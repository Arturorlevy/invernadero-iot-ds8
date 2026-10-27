"""
red.py - Conectividad: WiFi y cliente MQTT con reconexión automática.

El cliente MQTT:
  * Publica en  <TOPICO_BASE>/telemetria | estado | eventos | conexion
  * Se suscribe a <TOPICO_BASE>/comandos
  * Configura un "Last Will" (LWT): si el ESP32 se desconecta de forma
    inesperada, el broker publica "offline" en <TOPICO_BASE>/conexion.
  * Es no bloqueante: `revisar()` se llama en cada vuelta del bucle,
    atiende mensajes entrantes, envía PINGs y reconecta si hace falta.
"""

import time

import network
import ujson
import machine
import ubinascii
from umqtt.simple import MQTTClient


def conectar_wifi(ssid, password, timeout_s=20):
    """Conecta la interfaz STA del ESP32. Devuelve True si lo logra."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True
    print("[wifi] conectando a", ssid)
    wlan.connect(ssid, password)
    inicio = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), inicio) > timeout_s * 1000:
            print("[wifi] tiempo de espera agotado")
            return False
        time.sleep_ms(200)
    print("[wifi] conectado, IP:", wlan.ifconfig()[0])
    return True


class ClienteMQTT:
    def __init__(self, broker, puerto, topico_base, keepalive_s,
                 intervalo_reconexion_ms, on_comando):
        """
        on_comando: función llamada con el dict JSON recibido en /comandos.
        """
        sufijo = ubinascii.hexlify(machine.unique_id()).decode()
        self.client_id = "esp32-inv-" + sufijo
        self.base = topico_base
        self.keepalive = keepalive_s
        self.intervalo_reconexion = intervalo_reconexion_ms
        self._on_comando = on_comando
        self._cliente = MQTTClient(self.client_id, broker, port=puerto,
                                   keepalive=keepalive_s)
        self._cliente.set_callback(self._al_recibir)
        self.conectado = False
        self._ultimo_intento = 0
        self._ultimo_ping = 0
        self.al_conectar = None  # callback opcional tras (re)conectar

    def topico(self, sufijo):
        return self.base + "/" + sufijo

    # -- conexión -----------------------------------------------------------
    def conectar(self):
        self._ultimo_intento = time.ticks_ms()
        try:
            self._cliente.set_last_will(self.topico("conexion"), b"offline",
                                        retain=True, qos=1)
            self._cliente.connect()
            self._cliente.publish(self.topico("conexion"), b"online",
                                  retain=True, qos=1)
            self._cliente.subscribe(self.topico("comandos"), qos=1)
            self.conectado = True
            self._ultimo_ping = time.ticks_ms()
            print("[mqtt] conectado como", self.client_id)
            if self.al_conectar:
                self.al_conectar()
        except OSError as e:
            self.conectado = False
            print("[mqtt] error de conexion:", e)
        return self.conectado

    def revisar(self):
        """Atiende la red sin bloquear. Llamar en cada vuelta del bucle."""
        ahora = time.ticks_ms()
        if not self.conectado:
            if time.ticks_diff(ahora, self._ultimo_intento) >= self.intervalo_reconexion:
                self.conectar()
            return
        try:
            self._cliente.check_msg()
            # umqtt.simple no envía PINGs solo: lo hacemos a mitad del keepalive
            if time.ticks_diff(ahora, self._ultimo_ping) >= self.keepalive * 500:
                self._cliente.ping()
                self._ultimo_ping = ahora
        except OSError as e:
            print("[mqtt] conexion perdida:", e)
            self.conectado = False

    # -- envío / recepción -------------------------------------------------
    def publicar(self, sufijo, datos, retain=False):
        """Publica `datos` (dict) como JSON. Devuelve True si se envió."""
        if not self.conectado:
            return False
        try:
            self._cliente.publish(self.topico(sufijo), ujson.dumps(datos),
                                  retain=retain)
            return True
        except OSError as e:
            print("[mqtt] error al publicar:", e)
            self.conectado = False
            return False

    def _al_recibir(self, topico, mensaje):
        try:
            cmd = ujson.loads(mensaje)
        except ValueError:
            print("[mqtt] comando no es JSON valido:", mensaje)
            return
        if isinstance(cmd, dict):
            self._on_comando(cmd)
