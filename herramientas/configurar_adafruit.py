"""
configurar_adafruit.py - Crea en Adafruit IO los feeds y el dashboard del invernadero.

Usa la API REST de Adafruit IO (https://io.adafruit.com/api/docs) con las
credenciales del archivo .env (AIO_USERNAME, AIO_KEY). Es idempotente: si
un feed, el dashboard o sus bloques ya existen, no los duplica.

Uso:
    python herramientas/configurar_adafruit.py
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gateway import config  # noqa: E402

API = f"https://io.adafruit.com/api/v2/{config.AIO_USERNAME}"
P = config.AIO_PREFIJO
DASHBOARD_KEY = f"{P}-invernadero"

FEEDS = {
    f"{P}-temperatura": "Temperatura (°C)",
    f"{P}-humedad": "Humedad del aire (%)",
    f"{P}-luminosidad": "Luminosidad (%)",
    f"{P}-humedad-suelo": "Humedad del suelo (%)",
    f"{P}-ventilador": "Ventilador",
    f"{P}-bomba": "Bomba de riego",
    f"{P}-luz": "Luz de crecimiento",
    f"{P}-modo": "Modo AUTO/MANUAL",
    f"{P}-temp-max": "Umbral temperatura máx.",
    f"{P}-alertas": "Alertas",
}

TOGGLE = {"onText": "ON", "offText": "OFF", "onValue": "ON", "offValue": "OFF"}

# (nombre, tipo visual, feeds, propiedades, columna, fila, ancho, alto)
BLOQUES = [
    ("Temperatura y humedad", "line_chart", [f"{P}-temperatura", f"{P}-humedad"],
     {"historyHours": "1", "xAxisLabel": "Hora", "yAxisLabel": "°C / %"}, 0, 0, 6, 4),
    ("Luz y suelo", "line_chart", [f"{P}-luminosidad", f"{P}-humedad-suelo"],
     {"historyHours": "1", "xAxisLabel": "Hora", "yAxisLabel": "%"}, 6, 0, 6, 4),
    ("Temperatura", "gauge", [f"{P}-temperatura"],
     {"minValue": "0", "maxValue": "50", "label": "°C", "decimalPlaces": "1"}, 0, 4, 3, 3),
    ("Humedad suelo", "gauge", [f"{P}-humedad-suelo"],
     {"minValue": "0", "maxValue": "100", "label": "%", "decimalPlaces": "0"}, 3, 4, 3, 3),
    ("Modo", "toggle", [f"{P}-modo"],
     {"onText": "AUTO", "offText": "MANUAL", "onValue": "AUTO", "offValue": "MANUAL"}, 6, 4, 2, 2),
    ("Ventilador", "toggle", [f"{P}-ventilador"], TOGGLE, 8, 4, 2, 2),
    ("Bomba", "toggle", [f"{P}-bomba"], TOGGLE, 10, 4, 2, 2),
    ("Luz crecimiento", "toggle", [f"{P}-luz"], TOGGLE, 6, 6, 2, 2),
    ("Temp. máxima (ventilador)", "slider", [f"{P}-temp-max"],
     {"min": "20", "max": "40", "step": "0.5"}, 8, 6, 4, 2),
    ("Alertas", "stream", [f"{P}-alertas"],
     {"fontSize": "12", "showName": "no", "showTimestamp": "yes"}, 0, 7, 12, 3),
]


def api(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(f"{API}{ruta}", data=datos, method=metodo,
                                 headers={"X-AIO-Key": config.AIO_KEY,
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        detalle = e.read().decode(errors="replace")
        raise RuntimeError(f"{metodo} {ruta} -> HTTP {e.code}: {detalle}") from None


def main():
    if not config.adafruit_habilitado():
        sys.exit("Configure AIO_USERNAME y AIO_KEY en el archivo .env")

    existentes = {f["key"]: f for f in api("GET", "/feeds")}
    ids = {}
    for clave, nombre in FEEDS.items():
        if clave in existentes:
            print(f"  feed {clave}: ya existe")
            ids[clave] = existentes[clave]["id"]
        else:
            feed = api("POST", "/feeds", {"feed": {"name": clave, "key": clave,
                                                   "description": nombre}})
            print(f"  feed {clave}: creado")
            ids[clave] = feed["id"]

    tableros = {d["key"] for d in api("GET", "/dashboards")}
    if DASHBOARD_KEY not in tableros:
        api("POST", "/dashboards", {"dashboard": {
            "name": "Invernadero IoT", "key": DASHBOARD_KEY,
            "description": "Desarrollo de Software VIII - Parcial 2"}})
        print(f"  dashboard {DASHBOARD_KEY}: creado")

    actuales = {b["name"] for b in api("GET", f"/dashboards/{DASHBOARD_KEY}/blocks")}
    for nombre, tipo, feeds, props, col, fila, ancho, alto in BLOQUES:
        if nombre in actuales:
            print(f"  bloque '{nombre}': ya existe")
            continue
        api("POST", f"/dashboards/{DASHBOARD_KEY}/blocks", {"block": {
            "name": nombre, "visual_type": tipo, "properties": props,
            "column": col, "row": fila, "size_x": ancho, "size_y": alto,
            "block_feeds": [{"feed_id": str(ids[f])} for f in feeds]}})
        print(f"  bloque '{nombre}' ({tipo}): creado")

    print(f"\nListo: https://io.adafruit.com/{config.AIO_USERNAME}/dashboards/{DASHBOARD_KEY}")


if __name__ == "__main__":
    main()
