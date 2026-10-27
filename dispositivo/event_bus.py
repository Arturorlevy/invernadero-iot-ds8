"""
event_bus.py - Bus de eventos simple (patrón publicador/suscriptor).

Es el corazón de la programación orientada a eventos del dispositivo:
los módulos no se llaman entre sí directamente, sino que EMITEN eventos
("lectura", "comando", "boton", ...) y otros módulos se SUSCRIBEN a ellos.

Los eventos se encolan y se despachan desde el bucle principal. Esto es
importante porque algunos eventos nacen en interrupciones (el botón) o
en callbacks de red (MQTT), y no conviene ejecutar lógica pesada ahí.
"""


class EventBus:
    def __init__(self, max_cola=32):
        self._suscriptores = {}   # nombre_evento -> [handlers]
        self._cola = []
        self._max_cola = max_cola

    def suscribir(self, evento, handler):
        """Registra `handler(datos)` para ser llamado cuando ocurra `evento`."""
        self._suscriptores.setdefault(evento, []).append(handler)

    def emitir(self, evento, datos=None):
        """Encola un evento. Si la cola está llena se descarta el más antiguo."""
        if len(self._cola) >= self._max_cola:
            self._cola.pop(0)
        self._cola.append((evento, datos))

    def despachar(self):
        """Entrega todos los eventos pendientes a sus suscriptores.

        Un error en un handler no detiene a los demás: se informa y se
        continúa, para que un fallo puntual no congele el sistema.
        """
        while self._cola:
            evento, datos = self._cola.pop(0)
            for handler in self._suscriptores.get(evento, ()):
                try:
                    handler(datos)
                except Exception as e:
                    print("[bus] error en handler de '{}': {}".format(evento, e))
