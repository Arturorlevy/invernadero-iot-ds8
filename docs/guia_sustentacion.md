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
En el ESP32, `red.py` detecta el error, marca la conexión como caída y reintenta cada 5 s sin bloquear el control local: el invernadero sigue funcionando sin Internet. En el gateway, paho-mqtt reconecta solo (`reconnect_delay_set`).

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
- **En la demo:** en Wokwi sube la temperatura (ventilador e histéresis), mueve el potenciómetro (bomba), baja la luz (LED) y provoca la alarma a 39 °C.
- **Debe saber explicar:**
  - el DHT22 (protocolo de un hilo);
  - el ADC de 12 bits con `ATTN_11DB` y por qué se invierte el LDR;
  - el PWM del buzzer y por qué no bloquea;
  - el LCD por I2C (PCF8574, modo 4 bits);
  - la histéresis con números (30 °C enciende / 28.5 °C apaga);
  - modos AUTO/MANUAL y por qué se rechaza `set` en AUTO.

### Arturo Rodríguez: MQTT y nube
- **Estudiar:** `dispositivo/red.py`, `gateway/enlace_dispositivo.py`, `gateway/enlace_adafruit.py`, `gateway/servicio.py`, `docs/configuracion_adafruit_io.md`.
- **En la demo:** muestra el log del gateway y el dashboard de Adafruit IO. Envía comandos desde los toggles, incluido uno rechazado.
- **Debe saber explicar:**
  - MQTT (broker, tópicos, publicar/suscribir);
  - QoS 0 vs 1;
  - mensajes retenidos y Last Will;
  - reconexión sin bloquear y el PING del keepalive;
  - TLS en el puerto 8883 hacia Adafruit IO;
  - el límite de 30 datos/min y cómo se respeta;
  - la supresión de eco;
  - cómo el ack con `id` cierra el ciclo del comando.
