"""
config.py - Configuración del gateway, leída desde variables de entorno / .env.

Las credenciales (clave de Adafruit IO) NUNCA se escriben en el código:
se colocan en un archivo .env que está excluido de Git (.gitignore).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ_PROYECTO / ".env")

# --- Broker MQTT del dispositivo (HiveMQ) -----------------------------------
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPICO_RAIZ = os.getenv("TOPICO_RAIZ", "ds8/invernadero")
DISPOSITIVO_ID = os.getenv("DISPOSITIVO_ID", "inv-ds8-zcmr")
TOPICO_BASE = f"{TOPICO_RAIZ}/{DISPOSITIVO_ID}"

# --- Base de datos -------------------------------------------------------------
DB_PATH = Path(os.getenv("DB_PATH", RAIZ_PROYECTO / "data" / "invernadero.db"))
SCHEMA_PATH = RAIZ_PROYECTO / "sql" / "schema.sql"

# --- Adafruit IO (plataforma en la nube) -------------------------------------
AIO_USERNAME = os.getenv("AIO_USERNAME", "")
AIO_KEY = os.getenv("AIO_KEY", "")
AIO_PREFIJO = os.getenv("AIO_PREFIJO", "inv")
# Plan gratuito: máx. 30 datos/minuto. 4 feeds cada 20 s = 12/min.
AIO_INTERVALO_S = float(os.getenv("AIO_INTERVALO_S", "20"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def adafruit_habilitado():
    return bool(AIO_USERNAME and AIO_KEY)
