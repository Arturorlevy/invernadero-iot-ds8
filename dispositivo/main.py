"""
main.py - Punto de entrada del Invernadero Inteligente (ESP32 + MicroPython).

Arma el sistema y ejecuta el bucle principal orientado a eventos:

    sensores --(lectura)--> controlador --(actuador_cambiado/alerta)--> MQTT
    MQTT ------(comando)--> controlador --(comando_procesado)---------> MQTT
    botón -----(boton)----> controlador --(modo_cambiado)-------------> MQTT

El bucle nunca se bloquea: usa temporizadores por software (ticks_ms)
para decidir cuándo leer, cuándo publicar y cuándo refrescar la pantalla.
"""

import time
from machine import Pin

import config
from event_bus import EventBus
from sensores import GestorSensores
from actuadores import Rele, Led, Buzzer, PantallaLCD
from controlador import ControladorInvernadero
from red import conectar_wifi, ClienteMQTT


class Temporizador:
    """Temporizador por software no bloqueante."""

    def __init__(self, intervalo_ms):
        self.intervalo = intervalo_ms
        self._ultimo = time.ticks_ms() - intervalo_ms  # dispara de inmediato

    def vencido(self):
        ahora = time.ticks_ms()
        if time.ticks_diff(ahora, self._ultimo) >= self.intervalo:
            self._ultimo = ahora
            return True
        return False


class Invernadero:
    def __init__(self):
        self.bus = EventBus()

        # --- Hardware -------------------------------------------------------
        self.pantalla = PantallaLCD(config.PIN_I2C_SDA, config.PIN_I2C_SCL,
                                    config.LCD_DIRECCION_I2C)
        self.pantalla.mostrar("Invernadero IoT", "Iniciando...")
        self.sensores = GestorSensores(config.PIN_DHT22, config.PIN_LDR,
                                       config.PIN_SUELO)
        self.buzzer = Buzzer(config.PIN_BUZZER)
        actuadores = {
            "ventilador": Rele(config.PIN_RELE_VENTILADOR, "ventilador"),
            "bomba": Rele(config.PIN_RELE_BOMBA, "bomba"),
            "luz": Led(config.PIN_LED_CRECIMIENTO, "luz"),
            "alarma_led": Led(config.PIN_LED_ALARMA, "alarma"),
            "buzzer": self.buzzer,
        }
        self.controlador = ControladorInvernadero(
            self.bus, actuadores, config.UMBRALES, config.HISTERESIS)

        # Botón con interrupción (flanco de bajada, pull-up interno)
        self._ultimo_boton = 0
        self.boton = Pin(config.PIN_BOTON, Pin.IN, Pin.PULL_UP)
        self.boton.irq(trigger=Pin.IRQ_FALLING, handler=self._isr_boton)

        # --- Red ------------------------------------------------------------
        self.mqtt = ClienteMQTT(
            config.MQTT_BROKER, config.MQTT_PORT, config.TOPICO_BASE,
            config.MQTT_KEEPALIVE_S, config.INTERVALO_RECONEXION_MS,
            on_comando=lambda cmd: self.bus.emitir("comando", cmd))
        self.mqtt.al_conectar = lambda: self._publicar_estado(forzar=True)

        self.ultima_lectura = None
        self._ultimo_estado = None
        self.t_lectura = Temporizador(config.INTERVALO_LECTURA_MS)
        self.t_publicacion = Temporizador(config.INTERVALO_PUBLICACION_MS)
        self._suscribir_eventos()

    # ------------------------------------------------------------------
    # Cableado de eventos -> manejadores
    # ------------------------------------------------------------------
    def _suscribir_eventos(self):
        b, c = self.bus, self.controlador
        b.suscribir("lectura", c.on_lectura)
        b.suscribir("lectura", self._actualizar_pantalla)
        b.suscribir("comando", c.on_comando)
        b.suscribir("boton", c.on_boton)

        b.suscribir("actuador_cambiado", lambda d: self._evento("actuador", d))
        b.suscribir("modo_cambiado", lambda d: self._evento("modo", d))
        b.suscribir("alerta", lambda d: self._evento("alerta", d))
        b.suscribir("comando_procesado", lambda d: self._evento("comando", d))
        b.suscribir("comando_procesado", lambda _d: self._publicar_estado(forzar=True))
        b.suscribir("estado_cambiado", lambda _d: self._publicar_estado())

    def _isr_boton(self, _pin):
        """Interrupción del botón: solo encola el evento (con antirrebote)."""
        ahora = time.ticks_ms()
        if time.ticks_diff(ahora, self._ultimo_boton) > config.ANTIRREBOTE_BOTON_MS:
            self._ultimo_boton = ahora
            self.bus.emitir("boton")

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def _leer_sensores(self):
        try:
            datos = self.sensores.leer_todo()
        except OSError as e:
            print("[sensores] error de lectura:", e)
            self._evento("error", {"origen": "sensores", "detalle": str(e)})
            return
        self.ultima_lectura = datos
        self.bus.emitir("lectura", datos)

    def _publicar_telemetria(self):
        if self.ultima_lectura is None:
            return
        datos = dict(self.ultima_lectura)
        datos["uptime_ms"] = time.ticks_ms()
        if self.mqtt.publicar(config.T_TELEMETRIA, datos):
            print("[telemetria]", datos)

    def _publicar_estado(self, forzar=False):
        """Publica el estado (retenido) solo si cambió desde la última vez."""
        estado = self.controlador.estado()
        if not forzar and estado == self._ultimo_estado:
            return
        if self.mqtt.publicar(config.T_ESTADO, estado, retain=True):
            # copia: 'umbrales' es un dict que el controlador puede modificar
            estado["umbrales"] = dict(estado["umbrales"])
            self._ultimo_estado = estado

    def _evento(self, tipo, detalle):
        print("[evento]", tipo, detalle)
        self.mqtt.publicar(config.T_EVENTOS, {"tipo": tipo, "detalle": detalle})

    def _actualizar_pantalla(self, d):
        c = self.controlador
        modo = "AUTO" if c.modo == "auto" else "MAN "
        banderas = ("V" if c.act["ventilador"].estado else "-") + \
                   ("B" if c.act["bomba"].estado else "-") + \
                   ("L" if c.act["luz"].estado else "-") + \
                   ("!" if c.alarma else " ")
        self.pantalla.mostrar(
            "T{:4.1f} H{:3.0f}% {}".format(d["temperatura"], d["humedad"], modo),
            "L{:3.0f}% S{:3.0f}% {}".format(d["luminosidad"], d["humedad_suelo"], banderas))

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def iniciar(self):
        if conectar_wifi(config.WIFI_SSID, config.WIFI_PASSWORD):
            self.pantalla.mostrar("WiFi OK", "Conectando MQTT")
            self.mqtt.conectar()
        else:
            self.pantalla.mostrar("Sin WiFi", "Modo local")

    def ejecutar(self):
        self.iniciar()
        while True:
            if self.t_lectura.vencido():
                self._leer_sensores()
            if self.t_publicacion.vencido():
                self._publicar_telemetria()
            self.mqtt.revisar()      # puede emitir eventos "comando"
            self.buzzer.actualizar()
            self.bus.despachar()     # entrega todos los eventos pendientes
            time.sleep_ms(20)


Invernadero().ejecutar()
