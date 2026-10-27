"""
simulador_dispositivo.py - Simula el ESP32 en la PC (sin Wokwi).

Sirve para probar el gateway, la base de datos y Adafruit IO cuando Wokwi
no está disponible. Reutiliza el MISMO controlador del dispositivo
(dispositivo/controlador.py) con actuadores falsos, así que la lógica de
control es idéntica a la del ESP32.

Uso:
    python herramientas/simulador_dispositivo.py
"""

import json
import math
import random
import sys
import time
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "dispositivo"))
sys.path.insert(0, str(RAIZ))

from event_bus import EventBus                      # noqa: E402
from controlador import ControladorInvernadero      # noqa: E402
from gateway import config as cfg_gw                # noqa: E402

UMBRALES = {"temp_max": 30.0, "temp_alerta": 38.0, "temp_min_alerta": 10.0,
            "suelo_min": 30.0, "suelo_alerta": 10.0, "luz_min": 30.0}
HISTERESIS = {"temp": 1.5, "suelo": 15.0, "luz": 10.0}


class ActuadorFalso:
    def __init__(self):
        self.estado = False

    def establecer(self, valor):
        self.estado = bool(valor)


def main():
    base = cfg_gw.TOPICO_BASE
    bus = EventBus()
    act = {n: ActuadorFalso() for n in ("ventilador", "bomba", "luz", "alarma_led", "buzzer")}
    ctrl = ControladorInvernadero(bus, act, UMBRALES, HISTERESIS)

    cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                      client_id=f"sim-inv-{uuid.uuid4().hex[:8]}")
    cli.will_set(f"{base}/conexion", "offline", qos=1, retain=True)

    def al_conectar(c, *_):
        c.publish(f"{base}/conexion", "online", qos=1, retain=True)
        c.subscribe(f"{base}/comandos", qos=1)
        c.publish(f"{base}/estado", json.dumps(ctrl.estado()), retain=True)
        print("[sim] conectado a", cfg_gw.MQTT_BROKER, "base", base)

    def al_recibir(_c, _u, msg):
        try:
            bus.emitir("comando", json.loads(msg.payload))
        except json.JSONDecodeError:
            pass

    cli.on_connect = al_conectar
    cli.on_message = al_recibir
    cli.connect(cfg_gw.MQTT_BROKER, cfg_gw.MQTT_PORT, 60)
    cli.loop_start()

    def evento(tipo):
        return lambda d: cli.publish(f"{base}/eventos",
                                     json.dumps({"tipo": tipo, "detalle": d}))

    bus.suscribir("lectura", ctrl.on_lectura)
    bus.suscribir("comando", ctrl.on_comando)
    bus.suscribir("actuador_cambiado", evento("actuador"))
    bus.suscribir("modo_cambiado", evento("modo"))
    bus.suscribir("alerta", evento("alerta"))
    bus.suscribir("comando_procesado", evento("comando"))
    bus.suscribir("estado_cambiado",
                  lambda e: cli.publish(f"{base}/estado", json.dumps(e), retain=True))

    inicio = time.time()
    ultimo = 0.0
    try:
        while True:
            t = time.time() - inicio
            if time.time() - ultimo >= 5:
                ultimo = time.time()
                # Señales suaves que cruzan los umbrales para ver al controlador actuar
                datos = {
                    "temperatura": round(28 + 4 * math.sin(t / 40) + random.uniform(-.3, .3), 1),
                    "humedad": round(60 + 10 * math.sin(t / 60), 1),
                    "luminosidad": round(50 + 40 * math.sin(t / 50), 1),
                    "humedad_suelo": round(45 + 25 * math.sin(t / 70), 1),
                    "uptime_ms": int(t * 1000),
                }
                bus.emitir("lectura", datos)
                cli.publish(f"{base}/telemetria", json.dumps(datos))
                print("[sim]", datos, "modo", ctrl.modo)
            bus.despachar()
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        cli.publish(f"{base}/conexion", "offline", qos=1, retain=True)
        cli.loop_stop()
        cli.disconnect()


if __name__ == "__main__":
    main()
