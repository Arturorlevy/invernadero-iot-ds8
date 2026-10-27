"""
enlace_adafruit.py - Cliente MQTT seguro (TLS) hacia Adafruit IO.

Adafruit IO expone cada "feed" como un tópico MQTT:
    <usuario>/feeds/<clave-del-feed>

  * Publicamos lecturas en feeds de telemetría (para las gráficas).
  * Nos suscribimos a feeds de control (toggles y slider del dashboard)
    y convertimos cada cambio en un comando para el dispositivo.

Supresión de eco: Adafruit reenvía a los suscriptores TODO lo publicado
en un feed, incluso lo que publica el propio gateway. Si sincronizamos
un toggle con el estado real del ESP32, nos llegaría de vuelta y lo
confundiríamos con una orden del usuario. Por eso se recuerda lo que
publicamos y se ignora el primer mensaje idéntico que regrese.
"""

import logging
import ssl
import threading
import uuid

import paho.mqtt.client as mqtt

log = logging.getLogger("adafruit")

HOST = "io.adafruit.com"
PUERTO_TLS = 8883


class EnlaceAdafruit:
    def __init__(self, usuario, clave, feeds_control):
        """feeds_control: claves de feeds cuyo cambio debe generar un comando."""
        self.usuario = usuario
        self.feeds_control = set(feeds_control)
        self.on_control = None      # callback f(feed, valor_texto)
        self._eco = {}              # feed -> valor publicado por nosotros
        self.valores = {}           # feed -> último valor conocido en la nube
        self._lock = threading.Lock()

        self._cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                    client_id=f"gateway-inv-{uuid.uuid4().hex[:8]}")
        self._cliente.username_pw_set(usuario, clave)
        self._cliente.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        self._cliente.on_connect = self._al_conectar
        self._cliente.on_disconnect = self._al_desconectar
        self._cliente.on_message = self._al_recibir
        self._cliente.reconnect_delay_set(min_delay=2, max_delay=60)

    def topico(self, feed):
        return f"{self.usuario}/feeds/{feed}"

    def iniciar(self):
        log.info("Conectando a Adafruit IO como '%s'", self.usuario)
        self._cliente.connect_async(HOST, PUERTO_TLS, keepalive=60)
        self._cliente.loop_start()

    def detener(self):
        self._cliente.loop_stop()
        self._cliente.disconnect()

    def publicar(self, feed, valor, sincronizacion=False):
        """Publica `valor` en un feed.

        sincronizacion=True indica que es una actualización de estado hecha
        por el gateway (no una orden), así que su eco debe ignorarse.
        """
        texto = str(valor)
        with self._lock:
            if sincronizacion:
                self._eco[feed] = texto
            self.valores[feed] = texto
        self._cliente.publish(self.topico(feed), texto, qos=0)
        log.debug("-> %s = %s", feed, texto)

    # ------------------------------------------------------------------
    def _al_conectar(self, cliente, _userdata, _flags, reason_code, _props):
        if reason_code.is_failure:
            log.error("Adafruit IO rechazó la conexión (%s). Revise AIO_USERNAME/AIO_KEY.",
                      reason_code)
            return
        log.info("Conectado a Adafruit IO")
        for feed in self.feeds_control:
            cliente.subscribe(self.topico(feed), qos=1)
        # Mensajes de diagnóstico que envía Adafruit (límite de tasa, errores)
        cliente.subscribe(f"{self.usuario}/throttle")
        cliente.subscribe(f"{self.usuario}/errors")

    def _al_desconectar(self, _cliente, _userdata, _flags, reason_code, _props):
        if reason_code.is_failure:
            log.warning("Desconectado de Adafruit IO (%s); reintentando...", reason_code)

    def _al_recibir(self, _cliente, _userdata, msg):
        texto = msg.payload.decode("utf-8", errors="replace").strip()
        if msg.topic.endswith(("/throttle", "/errors")):
            log.warning("Adafruit IO: %s", texto)
            return

        feed = msg.topic.rsplit("/", 1)[-1]
        with self._lock:
            if self._eco.get(feed) == texto:
                del self._eco[feed]     # es el eco de nuestra sincronización
                return
            self.valores[feed] = texto

        log.info("Orden desde el dashboard: %s = %s", feed, texto)
        if self.on_control:
            try:
                self.on_control(feed, texto)
            except Exception:
                log.exception("Error procesando orden de Adafruit IO")
