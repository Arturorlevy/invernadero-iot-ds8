"""
controlador.py - Lógica de control del invernadero.

Recibe lecturas y comandos (a través del bus de eventos) y decide qué
hacer con los actuadores. Tiene dos modos:

  * AUTO   : las reglas con umbrales + histéresis controlan los actuadores.
  * MANUAL : solo los comandos remotos encienden/apagan actuadores.

La alarma (buzzer + LED rojo) se evalúa SIEMPRE, en ambos modos, porque
es una función de seguridad.

Este módulo no toca GPIO directamente: recibe los actuadores ya creados,
lo que permite probarlo en una PC con objetos simulados.
"""

MODO_AUTO = "auto"
MODO_MANUAL = "manual"

# Actuadores que pueden controlarse con el comando "set"
ACTUADORES_CONTROLABLES = ("ventilador", "bomba", "luz")


class ControladorInvernadero:
    def __init__(self, bus, actuadores, umbrales, histeresis):
        """
        bus        : EventBus para emitir cambios/alertas.
        actuadores : dict nombre -> objeto con .estado y .establecer(bool).
                     Claves esperadas: ventilador, bomba, luz, alarma_led, buzzer.
        """
        self.bus = bus
        self.act = actuadores
        self.umbrales = dict(umbrales)
        self.hist = dict(histeresis)
        self.modo = MODO_AUTO
        self.alarma = False
        self.ultima_lectura = None

    # ------------------------------------------------------------------
    # Manejadores de eventos
    # ------------------------------------------------------------------
    def on_lectura(self, datos):
        """Evento 'lectura': aplica reglas automáticas y evalúa alarmas."""
        self.ultima_lectura = datos
        if self.modo == MODO_AUTO:
            self._reglas_automaticas(datos)
        self._evaluar_alarma(datos)

    def on_comando(self, cmd):
        """Evento 'comando': valida y ejecuta una orden remota.

        Siempre emite 'comando_procesado' con el resultado (ack), para que
        el gateway pueda registrar si el comando se ejecutó o se rechazó.
        """
        ok, motivo = self._ejecutar_comando(cmd)
        self.bus.emitir("comando_procesado", {
            "id": cmd.get("id"),
            "accion": cmd.get("accion"),
            "resultado": "ejecutado" if ok else "rechazado",
            "motivo": motivo,
        })
        self.bus.emitir("estado_cambiado", self.estado())

    def on_boton(self, _datos=None):
        """Evento 'boton': el botón físico alterna AUTO <-> MANUAL."""
        nuevo = MODO_MANUAL if self.modo == MODO_AUTO else MODO_AUTO
        self.cambiar_modo(nuevo, origen="boton")

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------
    def cambiar_modo(self, modo, origen):
        if modo == self.modo:
            return
        self.modo = modo
        self.bus.emitir("modo_cambiado", {"modo": modo, "origen": origen})
        if modo == MODO_AUTO and self.ultima_lectura:
            self._reglas_automaticas(self.ultima_lectura)
        self.bus.emitir("estado_cambiado", self.estado())

    def estado(self):
        """Fotografía del estado actual (se publica en el tópico 'estado')."""
        return {
            "modo": self.modo,
            "ventilador": self.act["ventilador"].estado,
            "bomba": self.act["bomba"].estado,
            "luz": self.act["luz"].estado,
            "alarma": self.alarma,
            "umbrales": self.umbrales,
        }

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------
    def _establecer(self, nombre, valor, origen):
        """Cambia un actuador solo si su estado es distinto, y lo notifica."""
        actuador = self.act[nombre]
        if actuador.estado == bool(valor):
            return
        actuador.establecer(valor)
        self.bus.emitir("actuador_cambiado", {
            "actuador": nombre, "valor": bool(valor), "origen": origen,
        })
        self.bus.emitir("estado_cambiado", self.estado())

    @staticmethod
    def _con_histeresis(encendido, valor, umbral_on, umbral_off, encender_si_mayor):
        """Control on/off con histéresis.

        encender_si_mayor=True  -> enciende si valor >= umbral_on (p. ej. calor)
        encender_si_mayor=False -> enciende si valor <= umbral_on (p. ej. sequía)
        Mientras el valor está entre ambos umbrales, se mantiene el estado.
        """
        if encender_si_mayor:
            if valor >= umbral_on:
                return True
            if valor <= umbral_off:
                return False
        else:
            if valor <= umbral_on:
                return True
            if valor >= umbral_off:
                return False
        return encendido

    def _reglas_automaticas(self, d):
        u, h = self.umbrales, self.hist
        ventilador = self._con_histeresis(
            self.act["ventilador"].estado, d["temperatura"],
            u["temp_max"], u["temp_max"] - h["temp"], True)
        bomba = self._con_histeresis(
            self.act["bomba"].estado, d["humedad_suelo"],
            u["suelo_min"], u["suelo_min"] + h["suelo"], False)
        luz = self._con_histeresis(
            self.act["luz"].estado, d["luminosidad"],
            u["luz_min"], u["luz_min"] + h["luz"], False)
        self._establecer("ventilador", ventilador, "auto")
        self._establecer("bomba", bomba, "auto")
        self._establecer("luz", luz, "auto")

    def _evaluar_alarma(self, d):
        u = self.umbrales
        motivos = []
        if d["temperatura"] >= u["temp_alerta"]:
            motivos.append("temperatura alta")
        if d["temperatura"] <= u["temp_min_alerta"]:
            motivos.append("temperatura baja")
        if d["humedad_suelo"] <= u["suelo_alerta"]:
            motivos.append("suelo muy seco")

        activa = bool(motivos)
        if activa == self.alarma:
            return
        self.alarma = activa
        self.act["alarma_led"].establecer(activa)
        self.act["buzzer"].establecer(activa)
        self.bus.emitir("alerta", {
            "activa": activa,
            "motivo": ", ".join(motivos) if activa else "condiciones normalizadas",
            "lectura": d,
        })
        self.bus.emitir("estado_cambiado", self.estado())

    def _ejecutar_comando(self, cmd):
        """Devuelve (ok, motivo)."""
        accion = cmd.get("accion")

        if accion == "modo":
            valor = str(cmd.get("valor", "")).lower()
            if valor not in (MODO_AUTO, MODO_MANUAL):
                return False, "modo invalido: {}".format(valor)
            self.cambiar_modo(valor, origen="remoto")
            return True, ""

        if accion == "set":
            nombre = cmd.get("actuador")
            if nombre not in ACTUADORES_CONTROLABLES:
                return False, "actuador desconocido: {}".format(nombre)
            if self.modo != MODO_MANUAL:
                return False, "el sistema esta en AUTO; cambie a MANUAL"
            self._establecer(nombre, bool(cmd.get("valor")), "remoto")
            return True, ""

        if accion == "umbral":
            parametro = cmd.get("parametro")
            if parametro not in self.umbrales:
                return False, "umbral desconocido: {}".format(parametro)
            try:
                self.umbrales[parametro] = float(cmd.get("valor"))
            except (TypeError, ValueError):
                return False, "valor de umbral invalido"
            if self.modo == MODO_AUTO and self.ultima_lectura:
                self._reglas_automaticas(self.ultima_lectura)
            return True, ""

        if accion == "estado":
            return True, ""  # solo pide que se republique el estado

        return False, "accion desconocida: {}".format(accion)
