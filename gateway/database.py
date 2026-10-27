"""
database.py - Capa de acceso a datos (patrón Repositorio) sobre SQLite.

Centraliza TODO el SQL del gateway: el resto del código llama métodos
como `guardar_lectura()` o `resumen()` sin escribir consultas.

Los callbacks de MQTT se ejecutan en hilos distintos, por eso se usa
un Lock para serializar el acceso a la conexión.
"""

import json
import sqlite3
import threading
from pathlib import Path


class BaseDatos:
    def __init__(self, ruta_db, ruta_schema):
        Path(ruta_db).parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(ruta_db, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._con:
            self._con.executescript(Path(ruta_schema).read_text(encoding="utf-8"))

    def cerrar(self):
        self._con.close()

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    def _ejecutar(self, sql, params=()):
        with self._lock, self._con:
            return self._con.execute(sql, params)

    def _consultar(self, sql, params=()):
        with self._lock:
            return [dict(f) for f in self._con.execute(sql, params).fetchall()]

    def _asegurar_dispositivo(self, dispositivo_id):
        self._ejecutar(
            "INSERT OR IGNORE INTO dispositivos (id) VALUES (?)", (dispositivo_id,))

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------
    def guardar_lectura(self, dispositivo_id, datos):
        self._asegurar_dispositivo(dispositivo_id)
        cur = self._ejecutar(
            """INSERT INTO lecturas
               (dispositivo_id, temperatura, humedad, luminosidad, humedad_suelo, uptime_ms)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (dispositivo_id, datos.get("temperatura"), datos.get("humedad"),
             datos.get("luminosidad"), datos.get("humedad_suelo"), datos.get("uptime_ms")))
        return cur.lastrowid

    def guardar_evento(self, dispositivo_id, tipo, detalle):
        self._asegurar_dispositivo(dispositivo_id)
        cur = self._ejecutar(
            "INSERT INTO eventos (dispositivo_id, tipo, detalle) VALUES (?, ?, ?)",
            (dispositivo_id, tipo, json.dumps(detalle, ensure_ascii=False)))
        return cur.lastrowid

    def registrar_comando(self, dispositivo_id, origen, accion, parametro=None, valor=None):
        """Inserta el comando como 'pendiente' y devuelve su id."""
        self._asegurar_dispositivo(dispositivo_id)
        cur = self._ejecutar(
            """INSERT INTO comandos (dispositivo_id, origen, accion, parametro, valor)
               VALUES (?, ?, ?, ?, ?)""",
            (dispositivo_id, origen, accion, parametro,
             None if valor is None else str(valor)))
        return cur.lastrowid

    def resolver_comando(self, comando_id, estado, motivo=None):
        """Marca un comando como 'ejecutado' o 'rechazado' (ack del dispositivo)."""
        self._ejecutar(
            """UPDATE comandos
               SET estado = ?, motivo = ?,
                   resuelto_en = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
               WHERE id = ?""",
            (estado, motivo or None, comando_id))

    def actualizar_dispositivo(self, dispositivo_id, estado=None, conexion=None):
        self._asegurar_dispositivo(dispositivo_id)
        if estado is not None:
            self._ejecutar("UPDATE dispositivos SET ultimo_estado = ? WHERE id = ?",
                           (json.dumps(estado), dispositivo_id))
        if conexion is not None:
            self._ejecutar("UPDATE dispositivos SET conexion = ? WHERE id = ?",
                           (conexion, dispositivo_id))
        self._ejecutar(
            """UPDATE dispositivos
               SET visto_en = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
               WHERE id = ?""", (dispositivo_id,))

    # ------------------------------------------------------------------
    # Consultas de históricos
    # ------------------------------------------------------------------
    def ultimas_lecturas(self, n=20):
        return self._consultar(
            """SELECT timestamp, temperatura, humedad, luminosidad, humedad_suelo
               FROM lecturas ORDER BY id DESC LIMIT ?""", (n,))

    def lecturas_rango(self, desde, hasta):
        return self._consultar(
            """SELECT timestamp, temperatura, humedad, luminosidad, humedad_suelo
               FROM lecturas WHERE timestamp BETWEEN ? AND ?
               ORDER BY timestamp""", (desde, hasta))

    def resumen(self, horas=24):
        return self._consultar(
            """SELECT COUNT(*) AS muestras,
                      ROUND(AVG(temperatura), 2) AS temp_promedio,
                      MIN(temperatura) AS temp_min, MAX(temperatura) AS temp_max,
                      ROUND(AVG(humedad), 2) AS humedad_promedio,
                      ROUND(AVG(luminosidad), 2) AS luz_promedio,
                      ROUND(AVG(humedad_suelo), 2) AS suelo_promedio
               FROM lecturas
               WHERE timestamp >= strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime', ?)""",
            (f"-{int(horas)} hours",))

    def promedios_por_hora(self, limite=24):
        return self._consultar(
            """SELECT strftime('%Y-%m-%d %H:00', timestamp) AS hora,
                      COUNT(*) AS muestras,
                      ROUND(AVG(temperatura), 2) AS temp,
                      ROUND(AVG(humedad), 2) AS humedad,
                      ROUND(AVG(luminosidad), 2) AS luz,
                      ROUND(AVG(humedad_suelo), 2) AS suelo
               FROM lecturas GROUP BY hora ORDER BY hora DESC LIMIT ?""", (limite,))

    def eventos(self, tipo=None, n=50):
        if tipo:
            return self._consultar(
                """SELECT timestamp, tipo, detalle FROM eventos
                   WHERE tipo = ? ORDER BY id DESC LIMIT ?""", (tipo, n))
        return self._consultar(
            "SELECT timestamp, tipo, detalle FROM eventos ORDER BY id DESC LIMIT ?", (n,))

    def comandos(self, n=50):
        return self._consultar(
            """SELECT id, creado_en, origen, accion, parametro, valor, estado, motivo
               FROM comandos ORDER BY id DESC LIMIT ?""", (n,))

    def estadisticas_comandos(self):
        return self._consultar(
            """SELECT origen, COUNT(*) AS total,
                      SUM(estado = 'ejecutado') AS ejecutados,
                      SUM(estado = 'rechazado') AS rechazados,
                      SUM(estado = 'pendiente') AS pendientes
               FROM comandos GROUP BY origen""")
