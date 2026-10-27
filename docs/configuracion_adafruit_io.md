# Configuración de la plataforma Cloud — Adafruit IO

## 1. Cuenta y clave

1. Cree una cuenta gratuita en <https://io.adafruit.com>.
2. Haga clic en el ícono de **llave (My Key)** arriba a la derecha.
3. Copie el **Username** y la **Active Key** en el archivo `.env`:

   ```
   AIO_USERNAME=su_usuario
   AIO_KEY=aio_xxxxxxxxxxxxxxxxxxxx
   ```

> ⚠️ La clave **no** se sube a GitHub (`.env` está en `.gitignore`). Si se filtra, se regenera desde la misma ventana.

## 2. Creación automática (recomendado)

Con `.env` configurado, este comando crea los 10 feeds, el dashboard "Invernadero IoT" y todos sus bloques usando la API REST de Adafruit IO:

```bash
python herramientas/configurar_adafruit.py
```

Las secciones 3 y 4 describen lo que crea, por si prefieren hacerlo a mano.

## 3. Feeds

Un *feed* es un canal de datos. El plan gratuito permite **10 feeds** y **30 datos por minuto**. Este proyecto usa exactamente 10. Puede crearlos en **Feeds → New Feed**, o dejar que el gateway los cree solo al publicar por primera vez.

| Feed (clave) | Tipo | Lo escribe | Uso en el dashboard |
|---|---|---|---|
| `inv-temperatura` | telemetría | gateway | Gráfica de línea + medidor |
| `inv-humedad` | telemetría | gateway | Gráfica de línea |
| `inv-luminosidad` | telemetría | gateway | Gráfica / medidor |
| `inv-humedad-suelo` | telemetría | gateway | Gráfica / medidor |
| `inv-ventilador` | control | usuario ↔ gateway | Toggle ON/OFF |
| `inv-bomba` | control | usuario ↔ gateway | Toggle ON/OFF |
| `inv-luz` | control | usuario ↔ gateway | Toggle ON/OFF |
| `inv-modo` | control | usuario ↔ gateway | Toggle AUTO/MANUAL |
| `inv-temp-max` | control | usuario ↔ gateway | Slider 20–40 |
| `inv-alertas` | texto | gateway | Bloque *Text* / *Stream* |

## 4. Dashboard

**Dashboards → New Dashboard** → nombre "Invernadero". Luego, con el ícono ⚙️ → **Create New Block**:

| Bloque | Feed | Configuración |
|---|---|---|
| **Line Chart** | `inv-temperatura`, `inv-humedad` | Historial 1 hora |
| **Gauge** | `inv-temperatura` | Mín 0, máx 50, etiqueta "°C" |
| **Gauge** | `inv-humedad-suelo` | Mín 0, máx 100, etiqueta "%" |
| **Line Chart** | `inv-luminosidad`, `inv-humedad-suelo` | Historial 1 hora |
| **Toggle** | `inv-modo` | Button On Text: `AUTO` · Button Off Text: `MANUAL` |
| **Toggle** | `inv-ventilador` | On: `ON` · Off: `OFF` |
| **Toggle** | `inv-bomba` | On: `ON` · Off: `OFF` |
| **Toggle** | `inv-luz` | On: `ON` · Off: `OFF` |
| **Slider** | `inv-temp-max` | Mín 20, máx 40, paso 0.5 |
| **Stream** | `inv-alertas` | Muestra alertas y comandos rechazados |

Para la sustentación, tome una captura del dashboard funcionando y guárdela en `docs/capturas/`.

## 5. Cómo funciona la conexión

- **Protocolo**: MQTT sobre TLS, `io.adafruit.com:8883`, usuario = `AIO_USERNAME`, contraseña = `AIO_KEY`.
- **Tópicos**: `<usuario>/feeds/<feed>`. Ejemplo: `jperez/feeds/inv-temperatura`.
- **Límite de tasa**: el gateway envía las 4 lecturas cada `AIO_INTERVALO_S` = 20 s, o sea 12 datos/min. Si se excede el límite, Adafruit avisa por `<usuario>/throttle` y el gateway lo muestra en el log.
- **Sincronización**: cuando el ESP32 cambia un actuador por su cuenta (modo AUTO), el gateway actualiza el toggle correspondiente para que el dashboard muestre el estado real. Esos ecos se ignoran para no confundirlos con órdenes del usuario.

## 6. Prueba rápida

1. Inicie Wokwi (o el simulador) y luego `python -m gateway`.
2. En el log debe aparecer `Conectado a Adafruit IO`, y a los ~20 s los gauges deben moverse.
3. Ponga el toggle **Modo** en `MANUAL` y luego encienda **Ventilador**. El relé de Wokwi debe conmutar.
4. Vuelva a `AUTO` e intente encender la bomba. Se rechaza: aparece "Comando rechazado…" en el bloque de alertas y el toggle vuelve solo a su estado real.
5. `python -m gateway.consultas comandos` muestra todo lo anterior registrado en SQLite.
