"""
enlace_dispositivo.py - Cliente MQTT hacia el broker del dispositivo (HiveMQ).

Se suscribe a <TOPICO_BASE>/# y traduce cada mensaje a una llamada de
callback según el sub-tópico (telemetria, estado, eventos, conexion).
También permite enviar comandos al ESP32 por <TOPICO_BASE>/comandos.
"""

import json
import logging
import uuid

import paho.mqtt.client as mqtt

log = logging.getLogger("dispositivo")


class EnlaceDispositivo:
    def __init__(self, broker, puerto, topico_base):
        self.broker = broker
        self.puerto = puerto
        self.base = topico_base
        # Callbacks que asigna el servicio: f(dispositivo_id, datos)
        self.on_telemetria = None
        self.on_estado = None
        self.on_evento = None
        self.on_conexion = None

        self._cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                    client_id=f"gateway-inv-{uuid.uuid4().hex[:8]}")
        self._cliente.on_connect = self._al_conectar
        self._cliente.on_disconnect = self._al_desconectar
        self._cliente.on_message = self._al_recibir
        self._cliente.reconnect_delay_set(min_delay=1, max_delay=30)

    def iniciar(self):
        log.info("Conectando a %s:%s (tópico %s/#)", self.broker, self.puerto, self.base)
        self._cliente.connect_async(self.broker, self.puerto, keepalive=60)
        self._cliente.loop_start()  # hilo propio con reconexión automática

    def detener(self):
        self._cliente.loop_stop()
        self._cliente.disconnect()

    def enviar_comando(self, comando):
        """Publica un comando (dict) hacia el ESP32 con QoS 1."""
        carga = json.dumps(comando)
        info = self._cliente.publish(f"{self.base}/comandos", carga, qos=1)
        log.info("Comando -> dispositivo: %s", carga)
        return info.rc == mqtt.MQTT_ERR_SUCCESS

    # ------------------------------------------------------------------
    def _al_conectar(self, cliente, _userdata, _flags, reason_code, _props):
        if reason_code.is_failure:
            log.error("Conexión rechazada: %s", reason_code)
            return
        log.info("Conectado al broker del dispositivo")
        cliente.subscribe(f"{self.base}/#", qos=1)

    def _al_desconectar(self, _cliente, _userdata, _flags, reason_code, _props):
        if reason_code.is_failure:
            log.warning("Desconectado del broker (%s); reintentando...", reason_code)

    def _al_recibir(self, _cliente, _userdata, msg):
        partes = msg.topic.split("/")
        sufijo = partes[-1]
        dispositivo_id = partes[-2] if len(partes) >= 2 else "desconocido"
        texto = msg.payload.decode("utf-8", errors="replace")

        if sufijo == "comandos":
            return  # son nuestros propios comandos (eco del broker)
        if sufijo == "conexion":
            self._llamar(self.on_conexion, dispositivo_id, texto)
            return
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError:
            log.warning("JSON inválido en %s: %s", msg.topic, texto)
            return

        destino = {"telemetria": self.on_telemetria,
                   "estado": self.on_estado,
                   "eventos": self.on_evento}.get(sufijo)
        self._llamar(destino, dispositivo_id, datos)

    @staticmethod
    def _llamar(callback, *args):
        if callback is None:
            return
        try:
            callback(*args)
        except Exception:
            log.exception("Error procesando mensaje")
