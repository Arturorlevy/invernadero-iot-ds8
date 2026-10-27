"""
Punto de entrada del gateway.

Uso:
    python -m gateway

Detener con Ctrl+C.
"""

import logging
import time

from gateway import config
from gateway.database import BaseDatos
from gateway.enlace_adafruit import EnlaceAdafruit
from gateway.enlace_dispositivo import EnlaceDispositivo
from gateway.servicio import ServicioGateway


def main():
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format="%(asctime)s [%(levelname)-7s] %(name)-11s %(message)s",
        datefmt="%H:%M:%S")
    log = logging.getLogger("gateway")

    db = BaseDatos(config.DB_PATH, config.SCHEMA_PATH)
    log.info("Base de datos: %s", config.DB_PATH)

    dispositivo = EnlaceDispositivo(config.MQTT_BROKER, config.MQTT_PORT,
                                    config.TOPICO_BASE)

    adafruit = None
    if config.adafruit_habilitado():
        adafruit = EnlaceAdafruit(config.AIO_USERNAME, config.AIO_KEY, feeds_control=[])
    else:
        log.warning("AIO_USERNAME/AIO_KEY no configurados: se omite Adafruit IO "
                    "(solo MQTT + SQLite).")

    servicio = ServicioGateway(db, dispositivo, adafruit,
                               prefijo=config.AIO_PREFIJO,
                               intervalo_nube_s=config.AIO_INTERVALO_S,
                               dispositivo_id=config.DISPOSITIVO_ID)
    if adafruit:
        adafruit.feeds_control = set(servicio.feeds_control())
        adafruit.iniciar()
    dispositivo.iniciar()

    log.info("Gateway en ejecución. Ctrl+C para salir.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Deteniendo gateway...")
    finally:
        dispositivo.detener()
        if adafruit:
            adafruit.detener()
        db.cerrar()


if __name__ == "__main__":
    main()
