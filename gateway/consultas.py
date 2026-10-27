"""
consultas.py - CLI para consultar el histórico y enviar comandos manuales.

Ejemplos:
    python -m gateway.consultas ultimas -n 10
    python -m gateway.consultas rango "2026-10-26 08:00:00" "2026-10-26 18:00:00"
    python -m gateway.consultas resumen --horas 24
    python -m gateway.consultas por-hora
    python -m gateway.consultas eventos --tipo alerta
    python -m gateway.consultas comandos
    python -m gateway.consultas exportar lecturas.csv
    python -m gateway.consultas enviar modo manual
    python -m gateway.consultas enviar set ventilador 1
    python -m gateway.consultas enviar umbral temp_max 28
"""

import argparse
import csv
import sys
import time

from gateway import config
from gateway.database import BaseDatos


def imprimir_tabla(filas):
    if not filas:
        print("(sin resultados)")
        return
    columnas = list(filas[0].keys())
    anchos = [max(len(str(c)), *(len(str(f[c])) for f in filas)) for c in columnas]
    anchos = [min(a, 60) for a in anchos]
    fmt = "  ".join(f"{{:<{a}}}" for a in anchos)
    print(fmt.format(*columnas))
    print("  ".join("-" * a for a in anchos))
    for f in filas:
        print(fmt.format(*(str(f[c])[:60] for c in columnas)))


def enviar(db, accion, parametro, valor):
    """Envía un comando usando el mismo flujo que el gateway (queda registrado)."""
    from gateway.enlace_dispositivo import EnlaceDispositivo
    from gateway.servicio import ServicioGateway

    enlace = EnlaceDispositivo(config.MQTT_BROKER, config.MQTT_PORT, config.TOPICO_BASE)
    servicio = ServicioGateway(db, enlace, dispositivo_id=config.DISPOSITIVO_ID)
    # Solo enviamos: el gateway en ejecución es quien guarda lo que llega
    enlace.on_telemetria = enlace.on_estado = enlace.on_evento = enlace.on_conexion = None
    enlace.iniciar()
    time.sleep(2)  # dar tiempo a conectar
    if accion == "modo":
        valor, parametro = parametro, None
    elif valor is not None:
        try:
            valor = float(valor) if accion == "umbral" else int(valor)
        except ValueError:
            sys.exit(f"Valor inválido: {valor}")
    cid = servicio.enviar_comando("cli", accion, parametro, valor)
    time.sleep(1)
    enlace.detener()
    print(f"Comando #{cid} enviado. El gateway registrará el resultado al recibir el ack.")


def main():
    p = argparse.ArgumentParser(description="Consultas del Invernadero IoT")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ultimas", help="últimas lecturas")
    s.add_argument("-n", type=int, default=20)
    s = sub.add_parser("rango", help="lecturas entre dos fechas (YYYY-MM-DD HH:MM:SS)")
    s.add_argument("desde")
    s.add_argument("hasta")
    s = sub.add_parser("resumen", help="estadísticas de las últimas N horas")
    s.add_argument("--horas", type=int, default=24)
    sub.add_parser("por-hora", help="promedios por hora")
    s = sub.add_parser("eventos", help="historial de eventos")
    s.add_argument("--tipo", choices=["actuador", "modo", "alerta", "comando",
                                      "conexion", "error"])
    s.add_argument("-n", type=int, default=50)
    sub.add_parser("comandos", help="comandos enviados y su resultado")
    s = sub.add_parser("exportar", help="exportar todas las lecturas a CSV")
    s.add_argument("archivo")
    s = sub.add_parser("enviar", help="enviar un comando al dispositivo")
    s.add_argument("accion", choices=["set", "modo", "umbral", "estado"])
    s.add_argument("parametro", nargs="?", help="actuador | auto/manual | umbral")
    s.add_argument("valor", nargs="?")

    args = p.parse_args()
    db = BaseDatos(config.DB_PATH, config.SCHEMA_PATH)

    if args.cmd == "ultimas":
        imprimir_tabla(db.ultimas_lecturas(args.n))
    elif args.cmd == "rango":
        imprimir_tabla(db.lecturas_rango(args.desde, args.hasta))
    elif args.cmd == "resumen":
        imprimir_tabla(db.resumen(args.horas))
    elif args.cmd == "por-hora":
        imprimir_tabla(db.promedios_por_hora())
    elif args.cmd == "eventos":
        imprimir_tabla(db.eventos(args.tipo, args.n))
    elif args.cmd == "comandos":
        imprimir_tabla(db.comandos())
        print()
        imprimir_tabla(db.estadisticas_comandos())
    elif args.cmd == "exportar":
        filas = db.lecturas_rango("0000-01-01", "9999-12-31")
        with open(args.archivo, "w", newline="", encoding="utf-8") as f:
            if filas:
                w = csv.DictWriter(f, fieldnames=filas[0].keys())
                w.writeheader()
                w.writerows(filas)
        print(f"{len(filas)} lecturas exportadas a {args.archivo}")
    elif args.cmd == "enviar":
        enviar(db, args.accion, args.parametro, args.valor)
    db.cerrar()


if __name__ == "__main__":
    main()
