"""
servicio.py - Orquestador del gateway (lógica de integración).

Conecta las tres piezas, reaccionando a eventos:

  ESP32 --telemetria--> [Servicio] --> SQLite (lecturas)
                                   --> Adafruit IO (gráficas, con límite de tasa)
  ESP32 --eventos-----> [Servicio] --> SQLite (eventos) + ack de comandos
  ESP32 --estado------> [Servicio] --> sincroniza toggles del dashboard
  Adafruit IO --orden-> [Servicio] --> SQLite (comandos) --> ESP32
"""

import logging
import time

log = logging.getLogger("servicio")

ACTUADORES = ("ventilador", "bomba", "luz")
SENSORES = ("temperatura", "humedad", "luminosidad", "humedad_suelo")


class ServicioGateway:
    def __init__(self, db, dispositivo, adafruit=None, prefijo="inv",
                 intervalo_nube_s=20, dispositivo_id="inv-ds8-zcmr"):
        self.db = db
        self.dispositivo = dispositivo
        self.adafruit = adafruit
        self.dispositivo_id = dispositivo_id
        self.intervalo_nube = intervalo_nube_s
        self._ultimo_envio_nube = 0.0

        # Nombres de feeds en Adafruit IO
        p = prefijo
        self.feeds_sensores = {s: f"{p}-{s.replace('_', '-')}" for s in SENSORES}
        self.feeds_actuadores = {a: f"{p}-{a}" for a in ACTUADORES}
        self.feed_modo = f"{p}-modo"
        self.feed_temp_max = f"{p}-temp-max"
        self.feed_alertas = f"{p}-alertas"

        dispositivo.on_telemetria = self.procesar_telemetria
        dispositivo.on_estado = self.procesar_estado
        dispositivo.on_evento = self.procesar_evento
        dispositivo.on_conexion = self.procesar_conexion
        if adafruit:
            adafruit.on_control = self.procesar_orden_nube

    def feeds_control(self):
        """Feeds del dashboard que generan comandos hacia el dispositivo."""
        return list(self.feeds_actuadores.values()) + [self.feed_modo, self.feed_temp_max]

    # ------------------------------------------------------------------
    # Dispositivo -> gateway
    # ------------------------------------------------------------------
    def procesar_telemetria(self, dispositivo_id, datos):
        self.db.guardar_lectura(dispositivo_id, datos)
        log.info("Lectura guardada: T=%s°C H=%s%% L=%s%% S=%s%%",
                 datos.get("temperatura"), datos.get("humedad"),
                 datos.get("luminosidad"), datos.get("humedad_suelo"))

        ahora = time.monotonic()
        if self.adafruit and ahora - self._ultimo_envio_nube >= self.intervalo_nube:
            self._ultimo_envio_nube = ahora
            for sensor, feed in self.feeds_sensores.items():
                if datos.get(sensor) is not None:
                    self.adafruit.publicar(feed, datos[sensor])

    def procesar_evento(self, dispositivo_id, evento):
        tipo = evento.get("tipo", "desconocido")
        detalle = evento.get("detalle", {})
        self.db.guardar_evento(dispositivo_id, tipo, detalle)
        log.info("Evento [%s]: %s", tipo, detalle)

        if tipo == "comando" and detalle.get("id") is not None:
            self.db.resolver_comando(detalle["id"], detalle.get("resultado", "ejecutado"),
                                     detalle.get("motivo"))
            if detalle.get("resultado") == "rechazado":
                self._avisar(f"Comando rechazado: {detalle.get('motivo')}")
        elif tipo == "alerta":
            prefijo = "ALERTA" if detalle.get("activa") else "OK"
            self._avisar(f"{prefijo}: {detalle.get('motivo')}")

    def procesar_estado(self, dispositivo_id, estado):
        """Mantiene el dashboard igual al estado REAL del dispositivo."""
        self.db.actualizar_dispositivo(dispositivo_id, estado=estado)
        if not self.adafruit:
            return
        deseados = {feed: "ON" if estado.get(act) else "OFF"
                    for act, feed in self.feeds_actuadores.items()}
        deseados[self.feed_modo] = "AUTO" if estado.get("modo") == "auto" else "MANUAL"
        for feed, valor in deseados.items():
            if self.adafruit.valores.get(feed) != valor:
                self.adafruit.publicar(feed, valor, sincronizacion=True)

        temp_max = estado.get("umbrales", {}).get("temp_max")
        if temp_max is not None and not self._mismo_numero(
                self.adafruit.valores.get(self.feed_temp_max), temp_max):
            self.adafruit.publicar(self.feed_temp_max, temp_max, sincronizacion=True)

    def procesar_conexion(self, dispositivo_id, estado_conexion):
        self.db.actualizar_dispositivo(dispositivo_id, conexion=estado_conexion)
        self.db.guardar_evento(dispositivo_id, "conexion", {"estado": estado_conexion})
        log.info("Dispositivo %s: %s", dispositivo_id, estado_conexion)
        self._avisar(f"Dispositivo {estado_conexion}")

    # ------------------------------------------------------------------
    # Nube / CLI -> dispositivo
    # ------------------------------------------------------------------
    def procesar_orden_nube(self, feed, valor):
        """Traduce un cambio en el dashboard a un comando del dispositivo."""
        for actuador, f in self.feeds_actuadores.items():
            if feed == f:
                self.enviar_comando("adafruit", "set", actuador,
                                    1 if valor.upper() in ("ON", "1", "TRUE") else 0)
                return
        if feed == self.feed_modo:
            self.enviar_comando("adafruit", "modo", None,
                                "auto" if valor.upper() == "AUTO" else "manual")
        elif feed == self.feed_temp_max:
            try:
                self.enviar_comando("adafruit", "umbral", "temp_max", float(valor))
            except ValueError:
                log.warning("Valor de temp_max inválido: %s", valor)

    def enviar_comando(self, origen, accion, parametro=None, valor=None):
        """Registra el comando en la BD (pendiente) y lo envía con su id."""
        comando_id = self.db.registrar_comando(self.dispositivo_id, origen, accion,
                                               parametro, valor)
        comando = {"id": comando_id, "accion": accion}
        if accion == "set":
            comando["actuador"] = parametro
        elif accion == "umbral":
            comando["parametro"] = parametro
        if valor is not None:
            comando["valor"] = valor
        self.dispositivo.enviar_comando(comando)
        return comando_id

    # ------------------------------------------------------------------
    def _avisar(self, texto):
        if self.adafruit:
            self.adafruit.publicar(self.feed_alertas, texto)

    @staticmethod
    def _mismo_numero(a, b):
        try:
            return abs(float(a) - float(b)) < 1e-6
        except (TypeError, ValueError):
            return False
