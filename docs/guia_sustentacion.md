# Guía para la sustentación (50 % de la nota)

## Demo sugerida (5–7 minutos)

1. **Arquitectura (1 min)**: muestre el diagrama de [arquitectura.md](arquitectura.md). Explique las 4 capas y por qué hay un gateway.
2. **Wokwi (2 min)**: arranque la simulación y muestre el monitor serie (WiFi y MQTT conectados) y el LCD.
   - Suba la temperatura del DHT22 a 32 °C: el ventilador enciende y en el LCD aparece la `V`.
   - Bájela a 29 °C: el ventilador **sigue encendido** gracias a la histéresis. A 28 °C se apaga.
   - Suba la temperatura a 39 °C: suenan el buzzer y el LED rojo, y llega la alerta al dashboard.
   - Presione el botón azul: el modo cambia a MAN.
3. **Dashboard (1.5 min)**: muestre las gráficas en vivo. Encienda la bomba desde el toggle en MANUAL. Luego, en AUTO, intente encenderla y muestre el rechazo.
4. **Base de datos (1 min)**:
   ```
   python -m gateway.consultas ultimas -n 5
   python -m gateway.consultas comandos
   python -m gateway.consultas eventos --tipo alerta
   ```
5. **Código (1 min)**: abra `controlador.py` (reglas) y `event_bus.py` (eventos).

> **Antes de la demo:** encienda el gateway (`python -m gateway`) y luego la simulación de Wokwi. Espere a ver `[mqtt] conectado` en el monitor serie. Si el WiFi de Wokwi tarda, el ESP32 lo reintenta solo: espere hasta un par de minutos.

## El dashboard bloque por bloque

El dashboard de Adafruit IO tiene 3 zonas: **gráficas** arriba, **medidores y controles** en el medio y **alertas** abajo.

### Gráficas (zona superior)

| Bloque | Qué muestra | Cómo explicarlo |
|---|---|---|
| **Temperatura y humedad** | Dos líneas en el tiempo: temperatura del aire (°C) y humedad relativa del aire (%), ambas del **DHT22** | "Es el historial de la última hora. Cada punto es una lectura que el ESP32 envió por MQTT, el gateway guardó en SQLite y reenvió a Adafruit IO." |
| **Luz y suelo** | Dos líneas: luminosidad (%) del **LDR** y humedad del suelo (%) del **potenciómetro**, que simula un sensor de suelo | "Con estas dos variables decidimos cuándo prender la luz artificial y cuándo regar." |

- **Por qué las líneas a veces son planas:** en Wokwi los sensores son simulados y fijos hasta que se mueven sus deslizadores. Al cambiarlos durante la demo, la línea se mueve.
- **Por qué hay un retraso de 10 a 30 s:** el ESP32 publica cada 10 s y el gateway reenvía a la nube cada 20 s. Así se respeta el límite del plan gratuito de Adafruit IO: 30 datos por minuto, y nosotros enviamos 12.

### Medidores

| Bloque | Qué muestra |
|---|---|
| **Temperatura** | El valor más reciente en °C (escala 0–50) |
| **Humedad suelo** | El valor más reciente en % (escala 0–100) |

"Las gráficas muestran la tendencia y los medidores el valor actual de un vistazo."

### Controles

Para entender los controles hay que tener clara la idea de los dos modos:
- **AUTO:** el ESP32 decide solo, con reglas y umbrales.
- **MANUAL:** el usuario decide desde el dashboard.

| Control | Qué hace | Regla automática (en AUTO) |
|---|---|---|
| **Modo** (AUTO / MANUAL) | Cambia quién manda sobre los actuadores. También se cambia con el **botón azul** del circuito | — |
| **Ventilador** (ON / OFF) | Activa el relé 1 (GPIO 26), que en un invernadero real movería un ventilador para bajar la temperatura | Enciende con **≥ 30 °C** y apaga con **≤ 28.5 °C** |
| **Bomba** (ON / OFF) | Activa el relé 2 (GPIO 27), que movería una bomba de riego | Enciende con suelo **≤ 30 %** y apaga con **≥ 45 %** |
| **Luz crecimiento** (ON / OFF) | Enciende el LED amarillo (GPIO 14), que representa la luz artificial para las plantas | Enciende con luz **≤ 30 %** y apaga con **≥ 40 %** |
| **Temp. máxima** (slider 20–40) | Cambia en vivo el umbral de temperatura a partir del cual se enciende el ventilador | Si lo baja a 25 °C con el DHT22 en 26 °C, el ventilador enciende al instante |

**Cómo se comportan los toggles (lo más importante para la demo):**
1. **En MANUAL**, el toggle manda. Al pulsar "Ventilador ON", el relé se enciende en Wokwi en 1 o 2 segundos.
2. **En AUTO**, el toggle refleja lo que decidió el ESP32. Si el ESP32 enciende el ventilador por calor, el toggle cambia solo a ON: el gateway lo sincroniza con el estado real.
3. **Si alguien pulsa un toggle en AUTO**, el ESP32 **rechaza** la orden. En *Alertas* aparece "Comando rechazado: el sistema está en AUTO; cambie a MANUAL" y el toggle vuelve solo a su posición real. Explicación: "Si la aceptáramos, la regla automática la desharía 3 segundos después. Preferimos rechazarla con un motivo claro."

**Qué pasa por dentro al pulsar un toggle (para quien pregunte):**
```
Toggle "Bomba ON" en Adafruit IO
  → Adafruit lo publica en el feed inv-bomba (MQTT con TLS)
  → el gateway lo recibe, lo guarda en la tabla comandos como "pendiente" con un id
  → lo envía al ESP32 por HiveMQ: {"id": 7, "accion": "set", "actuador": "bomba", "valor": 1}
  → el controlador del ESP32 lo valida (¿está en MANUAL?) y enciende el relé
  → el ESP32 responde con un ack: {"tipo": "comando", "id": 7, "resultado": "ejecutado"}
  → el gateway marca el comando 7 como "ejecutado" en SQLite
```

### Alertas (zona inferior)

Es una lista con fecha y hora de los avisos importantes:
- `ALERTA: temperatura alta`: temperatura ≥ 38 °C. También suenan el buzzer y se enciende el LED rojo en Wokwi.
- `ALERTA: temperatura baja`: ≤ 10 °C.
- `ALERTA: suelo muy seco`: suelo ≤ 10 %.
- `OK: condiciones normalizadas`: la alarma se apagó.
- `Comando rechazado: ...`: una orden que el ESP32 no aceptó, con el motivo.
- `Dispositivo online` / `Dispositivo offline`: el ESP32 se conectó o se desconectó. El offline lo publica el broker gracias al Last Will.

"La alarma funciona en ambos modos, AUTO y MANUAL, porque es una función de seguridad."

## El LCD del circuito

```
T26.0 H 60% AUTO      → Temperatura, Humedad del aire, Modo (AUTO o MAN)
L 76% S 54% VBL!      → Luz, Suelo, actuadores encendidos y alarma
```

En la última posición de la segunda línea:
- **V**: ventilador encendido.
- **B**: bomba encendida.
- **L**: luz de crecimiento encendida.
- **!**: alarma activa.
- Un guion `-` en lugar de la letra indica que ese actuador está apagado.

## Guion de demo de los controles (2 minutos)

| Paso | Qué hace el presentador | Qué se ve |
|---|---|---|
| 1 | Con el sistema en **AUTO**, sube el DHT22 a **32 °C** en Wokwi | `V` en el LCD, relé 1 encendido, toggle *Ventilador* pasa solo a ON |
| 2 | Pulsa el toggle **Bomba** en el dashboard | Se rechaza: aviso en *Alertas* y el toggle vuelve a OFF |
| 3 | Cambia **Modo** a **MANUAL**, en el dashboard o con el botón azul | El LCD muestra `MAN` |
| 4 | Pulsa **Bomba ON** | Relé 2 encendido en Wokwi, `B` en el LCD |
| 5 | Pulsa **Ventilador OFF** | Se apaga aunque haga 32 °C: en MANUAL manda el usuario |
| 6 | Vuelve a **AUTO** | El ESP32 reaplica las reglas: el ventilador se enciende otra vez y la bomba se apaga |
| 7 | Sube el DHT22 a **39 °C** | Buzzer y LED rojo, `!` en el LCD, "ALERTA: temperatura alta" en el dashboard |
| 8 | Ejecuta `python -m gateway.consultas comandos` | Todos los comandos anteriores con su resultado |

## Preguntas probables y cómo responderlas

**¿Qué es MQTT y por qué usarlo en IoT?**
Es un protocolo publicador/suscriptor sobre TCP, muy liviano (encabezado de 2 bytes). Los dispositivos no se conocen entre sí: publican en *tópicos* y un *broker* reparte los mensajes. Es ideal para equipos con poca memoria y redes inestables.

**¿Qué QoS usaron y por qué?**
QoS 0 en telemetría: es frecuente y perder una lectura no importa. QoS 1 en comandos y en el estado de conexión: un comando debe llegar al menos una vez.

**¿Qué es el Last Will (LWT)?**
Un mensaje que el ESP32 deja registrado en el broker al conectarse. Si se desconecta sin avisar, el broker publica `offline` en `/conexion` en su nombre. Así el gateway sabe que el dispositivo cayó.

**¿Qué es un mensaje retenido?**
El broker guarda el último mensaje del tópico y se lo entrega a cada nuevo suscriptor. Lo usamos en `/estado` para que el gateway conozca el estado actual apenas se conecta.

**¿Dónde está la programación orientada a eventos?**
En `event_bus.py`. Los sensores, el botón (por interrupción) y MQTT *emiten* eventos. El controlador, la pantalla y la publicación MQTT se *suscriben* a ellos. El bucle principal nunca se bloquea: usa temporizadores por software (`ticks_ms`) en lugar de `sleep` largos.

**¿Por qué el botón usa interrupción?**
Para no tener que preguntar su estado todo el tiempo (*polling*). La interrupción solo encola el evento y aplica antirrebote de 300 ms. La lógica se ejecuta después, fuera de la interrupción.

**¿Qué es la histéresis?**
Usar dos umbrales distintos para encender y apagar. Sin ella, si la temperatura oscila entre 29.9 y 30.1 °C, el relé conmutaría cada lectura. Con ella, el ventilador enciende a 30 °C y apaga recién a 28.5 °C.

**¿Por qué rechazan comandos en modo AUTO?**
Porque la regla automática deshace la orden en la siguiente lectura (3 s después). Es mejor rechazarla con un motivo claro y que el dashboard vuelva al estado real.

**¿Cómo saben si un comando se ejecutó?**
El gateway guarda cada comando en SQLite como `pendiente` con un `id` y lo envía con ese id. El ESP32 responde con un ack (`ejecutado` o `rechazado`) y el gateway actualiza la fila.

**¿Por qué no conectan el ESP32 directo a Adafruit IO?**
Por tres razones. El enunciado pide un broker HiveMQ, Mosquitto o EMQX. SQLite no corre en un microcontrolador. Y así la clave de la nube no queda grabada en el firmware. El gateway además controla el límite de 30 datos/min del plan gratuito.

**¿Cómo se manejan las desconexiones?**
En dos niveles, sin bloquear nunca el control local: el invernadero sigue regulando temperatura, riego y luz aunque no haya Internet.
- **WiFi:** si no conecta en 30 s al arrancar, el programa sigue funcionando y `red.py` revisa el WiFi cada 20 s. Si el ESP32 no está ya intentando conectarse (`STAT_CONNECTING`), relanza la conexión. Esto se probó en Wokwi: con la red simulada lenta, el ESP32 arrancó sin WiFi, se recuperó solo y empezó a publicar.
- **MQTT:** cuando hay WiFi pero se cae el broker, `revisar()` detecta el error, marca la conexión como caída y reintenta cada 5 s.

En el gateway, paho-mqtt reconecta solo (`reconnect_delay_set`).

**¿Por qué SQLite?**
No necesita servidor y es un solo archivo, suficiente para un gateway. El esquema está en `sql/schema.sql`, con índices por fecha para las consultas de históricos.

**¿Cómo se lee el LDR y el potenciómetro?**
Con el ADC de 12 bits del ESP32 y atenuación de 11 dB (rango 0–3.3 V). `read_u16()` devuelve 0–65535 y se convierte a porcentaje. El LDR se invierte porque su voltaje baja cuando hay más luz.

**¿Cómo funciona el buzzer sin bloquear?**
Por PWM a 2 kHz. `actualizar()` se llama en cada vuelta del bucle y alterna sonido y silencio cada 500 ms comparando tiempos.

**¿Qué mejorarían?**
- MQTT con TLS y usuario en el broker (el público de HiveMQ es abierto).
- Sincronizar la hora del ESP32 con NTP.
- Guardar lecturas localmente mientras no hay red y enviarlas al reconectar.
- Usar un control PID para el riego.
- Pasar la BD a PostgreSQL si hubiera muchos dispositivos.

## Reparto por integrante

Cada integrante presenta su parte y debe dominar las preguntas de su sección. Todos deben poder explicar la vista general (sección 1 de `arquitectura.md`).

### Estefanny Zambrano: Base de datos y consultas
- **Estudiar:** `sql/schema.sql`, `sql/consultas.sql`, `gateway/database.py`, `gateway/consultas.py`.
- **En la demo:** ejecuta `ultimas`, `resumen`, `eventos --tipo alerta` y `comandos`.
- **Debe saber explicar:**
  - las 4 tablas y sus relaciones (diagrama ER en `arquitectura.md` §3);
  - por qué el timestamp lo pone el gateway;
  - los índices;
  - el ciclo de un comando (`pendiente → ejecutado / rechazado`);
  - el uso de `json_extract`;
  - por qué hay un `Lock` (hilos de MQTT);
  - por qué SQLite y no MySQL.

### Alberto Chen: Arquitectura, diagramas y eventos
- **Estudiar:** `docs/arquitectura.md` (los 5 diagramas), `dispositivo/diagram.json`, `dispositivo/event_bus.py`, `dispositivo/main.py`.
- **En la demo:** abre la presentación con la arquitectura por capas y muestra el circuito en Wokwi.
- **Debe saber explicar:**
  - las 4 capas IoT y por qué existe un gateway;
  - el flujo de telemetría y el de un comando (diagramas de secuencia);
  - qué es el patrón publicador/suscriptor del `EventBus`;
  - por qué el bucle no usa `sleep` largos (clase `Temporizador`);
  - cómo la interrupción del botón solo encola un evento;
  - qué pin usa cada componente.

### Edwin Moreno: Sensores, actuadores y control
- **Estudiar:** `dispositivo/sensores.py`, `actuadores.py`, `lcd_i2c.py`, `controlador.py`, `config.py`.
- **En la demo:** en Wokwi sube la temperatura (ventilador e histéresis), mueve el potenciómetro (bomba), baja la luz (LED) y provoca la alarma a 39 °C. Explica las secciones **"El LCD del circuito"** y la tabla de **reglas automáticas** de los controles.
- **Debe saber explicar:**
  - el DHT22 (protocolo de un hilo);
  - el ADC de 12 bits con `ATTN_11DB` y por qué se invierte el LDR;
  - el PWM del buzzer y por qué no bloquea;
  - el LCD por I2C (PCF8574, modo 4 bits);
  - la histéresis con números (30 °C enciende / 28.5 °C apaga);
  - modos AUTO/MANUAL y por qué se rechaza `set` en AUTO.

### Arturo Rodríguez: MQTT y nube
- **Estudiar:** `dispositivo/red.py`, `gateway/enlace_dispositivo.py`, `gateway/enlace_adafruit.py`, `gateway/servicio.py`, `docs/configuracion_adafruit_io.md`.
- **En la demo:** muestra el log del gateway y el dashboard de Adafruit IO. Explica **"El dashboard bloque por bloque"** y dirige el **guion de demo de los controles**, incluido el comando rechazado.
- **Debe saber explicar:**
  - MQTT (broker, tópicos, publicar/suscribir);
  - QoS 0 vs 1;
  - mensajes retenidos y Last Will;
  - reconexión sin bloquear y el PING del keepalive;
  - TLS en el puerto 8883 hacia Adafruit IO;
  - el límite de 30 datos/min y cómo se respeta;
  - la supresión de eco;
  - cómo el ack con `id` cierra el ciclo del comando.
