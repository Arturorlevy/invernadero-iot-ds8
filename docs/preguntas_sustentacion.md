# Banco de preguntas para la sustentación

Posibles preguntas del profesor, agrupadas por **quién debe responder**. Cada pregunta trae una respuesta corta (lo esencial que hay que decir) y, cuando aplica, el **archivo donde se puede mostrar** en el código.

## Cómo usar este documento

- **Cada integrante domina su sección.** Si el profesor pregunta un tema, responde el dueño del tema aunque la pregunta vaya dirigida a otro: "Esa parte la desarrolló Edwin, él le explica".
- **Todos estudian la sección "Preguntas generales"**, porque se le pueden hacer a cualquiera.
- **Respondan en 3 pasos:** la respuesta corta, el porqué y, si se puede, mostrarlo en el código o en la demo.
- **Si no saben algo, no lo inventen.** Digan "eso lo podemos mostrar en el código" y abran el archivo indicado, o pidan apoyo al compañero dueño del tema.

| Tema | Responde | Apoya |
|---|---|---|
| Preguntas generales | Cualquiera (sugerido en cada pregunta) | El resto del grupo |
| Arquitectura, circuito, eventos | **Alberto Chen** | Edwin |
| Sensores, actuadores, control | **Edwin Moreno** | Alberto |
| MQTT, gateway, nube | **Arturo Rodríguez** | Estefanny |
| Base de datos, históricos | **Estefanny Zambrano** | Arturo |

---

## 1. Preguntas generales (para todos)

**G1. ¿Qué hace su sistema, en una frase?** *(Alberto)*
Monitorea un invernadero (temperatura, humedad, luz y humedad del suelo), controla solo el ventilador, el riego y la luz cuando las variables se salen de rango, guarda todo en una base de datos y permite ver y controlar el invernadero desde un dashboard en la nube.

**G2. ¿Por qué eligieron el invernadero?** *(Alberto)*
Porque permite usar varios sensores y actuadores con reglas claras y fáciles de demostrar: calor → ventilador, suelo seco → riego, poca luz → luz artificial. Además tiene una función de seguridad, la alarma.

**G3. ¿Cómo cumplen cada requisito del parcial?** *(Estefanny, en el cierre)*
- 3 sensores (DHT22, LDR y potenciómetro como humedad de suelo) y 6 actuadores (2 relés, 2 LEDs, buzzer y LCD).
- Código Python modular (8 módulos en el ESP32) y documentado.
- GPIO con el módulo `machine` de MicroPython.
- Lectura en tiempo real cada 3 s.
- Cliente MQTT en el ESP32 con HiveMQ.
- Base de datos SQLite con lecturas, eventos y comandos, y consultas de históricos.
- Adafruit IO con dashboard en tiempo real y comandos desde la nube.
- Programación orientada a eventos con el `EventBus`.

**G4. ¿Qué aportó cada uno?** *(cada uno responde lo suyo)*
- **Estefanny:** base de datos y consultas.
- **Alberto:** arquitectura, diagramas, circuito y programación por eventos.
- **Edwin:** sensores, actuadores y lógica de control.
- **Arturo:** comunicación MQTT, gateway y plataforma en la nube.

**G5. ¿Qué librerías usaron?** *(Edwin para el ESP32, Arturo para el gateway)*
- **En el ESP32 (MicroPython):** `machine` (Pin, ADC, PWM, I2C) para el GPIO, `dht` para el sensor, `network` para el WiFi, `umqtt.simple` para MQTT y `ujson`. Todas vienen incluidas en el firmware.
- **En el gateway:** `paho-mqtt` para MQTT, `python-dotenv` para leer las credenciales, y `sqlite3` de la biblioteca estándar. Están en `requirements.txt`.

**G6. ¿Cuál fue la parte más difícil?** *(Arturo)*
La comunicación bidireccional con la nube: que el dashboard muestre siempre el estado real del ESP32 sin confundir sus propias actualizaciones con órdenes del usuario. Lo resolvimos con la sincronización de estado y la supresión de eco. También la reconexión cuando el WiFi de Wokwi tardaba en conectar.

**G7. ¿Cómo probaron que todo funciona?** *(Arturo)*
- Pruebas de la lógica del controlador y de la base de datos en la PC.
- Un simulador del ESP32 (`herramientas/simulador_dispositivo.py`) que usa el mismo controlador, para probar el gateway sin Wokwi.
- Corridas completas en Wokwi con el gateway en vivo: escenario normal y de alarma, con comandos aceptados y rechazados, todo registrado en SQLite.

**G8. ¿Qué diferencia habría con un invernadero real?** *(Edwin)*
- El potenciómetro sería un sensor capacitivo de humedad de suelo.
- Los relés moverían un ventilador y una bomba reales, con su fuente de poder.
- El LED amarillo sería una lámpara de crecimiento.
- El código sería prácticamente el mismo: solo cambiaría la calibración de los sensores en `config.py`.

**G9. ¿Qué mejorarían?** *(Estefanny)*
- Seguridad en el broker MQTT (TLS y usuario, porque HiveMQ público es abierto).
- Hora real en el ESP32 por NTP.
- Guardar lecturas cuando no hay red y enviarlas al reconectar.
- Control PID para el riego.
- PostgreSQL si hubiera muchos dispositivos.

---

## 2. Alberto Chen: arquitectura, circuito y eventos

**A1. Explique la arquitectura del sistema.**
Cuatro capas:
- **percepción:** el ESP32 con sensores y actuadores;
- **red:** WiFi + MQTT con HiveMQ;
- **procesamiento:** el gateway Python con SQLite;
- **aplicación:** Adafruit IO con el dashboard.

Los datos suben por esa cadena y los comandos bajan por la misma. *Mostrar:* `docs/arquitectura.md`, diagrama 1.

**A2. ¿Por qué usan un gateway en vez de conectar el ESP32 directo a la nube?**
Por tres razones. El enunciado pide un broker HiveMQ, Mosquitto o EMQX en el dispositivo. La base de datos SQL no corre en un microcontrolador. Y así la clave de Adafruit queda en la PC y no grabada en el ESP32. Además, el gateway controla el límite de envíos del plan gratuito.

**A3. ¿Qué significa que el código esté "orientado a eventos"?**
Los módulos no se llaman directamente: emiten eventos ("lectura", "comando", "boton", "alerta"...) y otros módulos se suscriben a ellos. El `EventBus` los encola y los entrega en el bucle principal. *Mostrar:* `dispositivo/event_bus.py`, métodos `suscribir`, `emitir` y `despachar`.

**A4. ¿Qué ventaja tiene usar eventos?**
Desacoplamiento. Se puede agregar un nuevo actuador o una nueva pantalla suscribiéndolo a "lectura", sin modificar el código de los sensores. Y un error en un manejador no detiene a los demás: `despachar()` captura la excepción y continúa.

**A5. ¿Qué pasa si se acumulan muchos eventos?**
La cola tiene un máximo de 32. Si se llena, se descarta el más antiguo, para no quedarse sin memoria en el ESP32.

**A6. ¿Por qué el bucle principal no usa `sleep(3)` para leer cada 3 segundos?**
Porque `sleep` bloquea: mientras duerme no atendería el botón ni los mensajes MQTT. Usamos la clase `Temporizador`, que compara `time.ticks_ms()` con la última ejecución. El bucle da vueltas cada 20 ms y solo hace cada tarea cuando le toca. *Mostrar:* `dispositivo/main.py`, clase `Temporizador` y método `ejecutar()`.

**A7. ¿Cómo funciona el botón?**
Está en el GPIO 4 con resistencia *pull-up* interna y una interrupción por flanco de bajada (al presionarlo, el pin pasa de 1 a 0). La interrupción solo verifica el antirrebote de 300 ms y encola el evento "boton". El cambio de modo lo hace el controlador después. *Mostrar:* `main.py`, método `_isr_boton`.

**A8. ¿Qué es el antirrebote?**
Al presionar un botón físico, el contacto "rebota" y genera varios pulsos en milisegundos. Ignorando las pulsaciones que llegan antes de 300 ms de la anterior, una presión cuenta como una sola.

**A9. ¿Qué pin usa cada componente?**

| Componente | GPIO |
|---|---|
| DHT22 | 15 |
| LDR | 34 |
| Potenciómetro (suelo) | 35 |
| Botón | 4 |
| Relé ventilador | 26 |
| Relé bomba | 27 |
| LED luz de crecimiento | 14 |
| LED alarma | 13 |
| Buzzer | 25 |
| LCD (SDA / SCL) | 21 / 22 |

*Mostrar:* `dispositivo/config.py`.

**A10. ¿Por qué el LDR y el potenciómetro están en los pines 34 y 35?**
Porque son pines con ADC (conversor analógico-digital) del ESP32 y solo de entrada, ideales para leer sensores analógicos.

**A11. Explique el flujo de una lectura desde el sensor hasta el dashboard.**
1. El ESP32 lee los sensores cada 3 s y emite "lectura".
2. El controlador aplica las reglas.
3. Cada 10 s se publica la telemetría en MQTT.
4. El gateway la recibe, la guarda en SQLite y cada 20 s la reenvía a Adafruit IO, donde la grafica el dashboard.

*Mostrar:* `arquitectura.md`, diagrama 2.

**A12. ¿Cómo está organizado el código?**
- `dispositivo/`: firmware MicroPython en 8 módulos, cada uno con una responsabilidad: config, eventos, sensores, actuadores, LCD, controlador, red y main.
- `gateway/`: servicio Python con su configuración, base de datos, los dos enlaces MQTT, el orquestador y la CLI de consultas.
- `sql/`: los scripts.
- `docs/`: la documentación.

---

## 3. Edwin Moreno: sensores, actuadores y control

**E1. ¿Cómo se lee el DHT22?**
Con la librería `dht` de MicroPython. Usa un protocolo digital de un solo hilo en el GPIO 15. `measure()` hace la lectura y luego `temperature()` y `humidity()` devuelven °C y %. Si el sensor no responde, lanza un error que capturamos y reportamos como evento "error", sin detener el programa. *Mostrar:* `dispositivo/sensores.py`, clase `SensorDHT22`.

**E2. ¿Cómo se leen los sensores analógicos?**
Con el ADC del ESP32. `read_u16()` devuelve un valor de 0 a 65535, que convertimos a porcentaje. Configuramos atenuación de 11 dB para medir todo el rango de 0 a 3.3 V. *Mostrar:* `sensores.py`, clase `SensorAnalogico`.

**E3. ¿Por qué se invierte el valor del LDR?**
Porque en el módulo fotorresistor el voltaje de salida **baja** cuando hay más luz. Invertimos para que 100 % signifique mucha luz.

**E4. ¿Qué es la atenuación del ADC?**
Sin atenuación, el ADC del ESP32 solo mide hasta 1.1 V aproximadamente. Con 11 dB mide hasta unos 3.3 V, que es el voltaje con el que alimentamos los sensores.

**E5. Explique las reglas del modo automático.**

| Actuador | Enciende con | Apaga con |
|---|---|---|
| Ventilador | temperatura ≥ 30 °C | ≤ 28.5 °C |
| Bomba | suelo ≤ 30 % | ≥ 45 % |
| Luz de crecimiento | luz ≤ 30 % | ≥ 40 % |

*Mostrar:* `dispositivo/controlador.py`, método `_reglas_automaticas`.

**E6. ¿Qué es la histéresis y por qué la usan?**
Son dos umbrales distintos para encender y apagar. Sin histéresis, si la temperatura oscila entre 29.9 y 30.1 °C, el ventilador se prendería y apagaría en cada lectura (*chattering*), y eso desgasta los relés. *Mostrar:* `controlador.py`, método `_con_histeresis`.

**E7. ¿Cuándo se activa la alarma?**
Con temperatura ≥ 38 °C, ≤ 10 °C o suelo ≤ 10 %. Enciende el LED rojo y el buzzer intermitente, y envía una alerta a la nube. Funciona en **ambos modos**, porque es una función de seguridad. *Mostrar:* `controlador.py`, método `_evaluar_alarma`.

**E8. ¿Cómo suena el buzzer sin bloquear el programa?**
Con PWM a 2 kHz. El método `actualizar()` se llama en cada vuelta del bucle y, comparando tiempos, alterna sonido y silencio cada 500 ms. Nunca usa `sleep`. *Mostrar:* `dispositivo/actuadores.py`, clase `Buzzer`.

**E9. ¿Qué es PWM?**
Modulación por ancho de pulso: una señal digital que se prende y apaga muy rápido. La frecuencia define el tono del buzzer (2000 Hz) y el ciclo de trabajo, cuánto tiempo está encendida (usamos 50 %).

**E10. ¿Cómo funciona el LCD?**
Es un LCD 16×2 con un adaptador I2C PCF8574 en la dirección 0x27, conectado a SDA 21 y SCL 22. El adaptador convierte I2C en las líneas del LCD, que trabaja en modo de 4 bits: cada carácter se envía en dos mitades. El controlador lo escribimos nosotros. *Mostrar:* `dispositivo/lcd_i2c.py`.

**E11. ¿Qué significan las letras del LCD?**
- **Línea 1:** temperatura, humedad y modo (AUTO o MAN).
- **Línea 2:** luz, suelo y actuadores encendidos: V ventilador, B bomba, L luz y `!` alarma. Un guion indica apagado.

**E12. ¿Qué diferencia hay entre modo AUTO y MANUAL?**
En AUTO las reglas controlan los actuadores. En MANUAL las reglas se desactivan y solo obedecen comandos remotos. Se cambia con el botón azul o desde el dashboard. Al volver a AUTO, las reglas se aplican de inmediato con la última lectura.

**E13. ¿Por qué el sistema rechaza un comando en modo AUTO?**
Porque si lo aceptara, la regla automática lo desharía en la siguiente lectura, 3 segundos después, y el usuario no entendería qué pasó. Es mejor rechazarlo con un motivo claro: "el sistema está en AUTO; cambie a MANUAL".

**E14. ¿Por qué un relé y no conectar el ventilador directo al pin?**
Un pin del ESP32 entrega 3.3 V y muy poca corriente. Un ventilador o una bomba necesitan más voltaje y corriente. El relé es un interruptor que el pin activa para conmutar esa carga de potencia de forma aislada.

**E15. ¿Por qué usaron un potenciómetro como sensor de suelo?**
Wokwi no tiene sensor de humedad de suelo. El potenciómetro entrega un voltaje analógico variable, que es justo lo que entrega un sensor de suelo real, así que el código de lectura es el mismo.

---

## 4. Arturo Rodríguez: MQTT, gateway y nube

**R1. ¿Qué es MQTT y por qué lo usaron?**
Es un protocolo de mensajería publicador/suscriptor sobre TCP, muy liviano. Por eso es ideal para dispositivos con poca memoria y redes inestables. Los clientes publican en *tópicos* y un *broker* reparte los mensajes a los suscriptores.

**R2. ¿Qué es un broker? ¿Cuál usaron?**
Es el servidor que recibe y reparte los mensajes MQTT. Usamos el broker público de HiveMQ (`broker.hivemq.com`, puerto 1883), uno de los que pide el enunciado.

**R3. ¿Qué diferencia hay entre MQTT y HTTP?**
HTTP es petición-respuesta: el cliente pregunta y el servidor responde. Para recibir comandos, el ESP32 tendría que preguntar a cada rato (*polling*). MQTT mantiene una conexión abierta: el broker le **empuja** el comando apenas llega. Además, los mensajes son mucho más pequeños.

**R4. ¿Qué tópicos usa el ESP32?**
Todos bajo `ds8/invernadero/inv-ds8-zcmr/`:
- `telemetria`: lecturas;
- `estado`: actuadores (retenido);
- `eventos`: cambios, alertas y confirmaciones;
- `conexion`: online u offline;
- `comandos`: órdenes que recibe.

Los mensajes van en JSON. *Mostrar:* `README.md`, tabla del protocolo MQTT.

**R5. ¿Qué QoS usaron?**
QoS 0 en la telemetría: se envía cada 10 s, y si se pierde una llega la siguiente. QoS 1 en comandos y conexión: garantiza que el mensaje llegue al menos una vez. QoS 2 (exactamente una vez) no lo necesitamos y es más lento.

**R6. ¿Qué es un mensaje retenido?**
El broker guarda el último mensaje de ese tópico y se lo entrega a cualquiera que se suscriba después. Lo usamos en `estado` y `conexion`: el gateway conoce el estado actual del ESP32 apenas se conecta, sin esperar un cambio.

**R7. ¿Qué es el Last Will?**
Un mensaje de "última voluntad" que el ESP32 registra en el broker al conectarse. Si se desconecta sin avisar (corte de energía o de red), el broker publica `offline` en el tópico `conexion` en su nombre. Así el gateway y el dashboard saben que se cayó. *Mostrar:* `dispositivo/red.py`, `set_last_will`.

**R8. ¿Qué pasa si se cae el WiFi o el broker?**
El control local sigue funcionando. Si el WiFi no conecta, `red.py` lo reintenta cada 20 s sin interrumpir un intento en curso. Si hay WiFi pero se cae el broker, reintenta MQTT cada 5 s. En el gateway, paho-mqtt reconecta solo. *Mostrar:* `red.py`, métodos `revisar()` y `reintentar_wifi()`.

**R9. ¿Qué es el keepalive?**
El tiempo máximo (60 s) que el broker espera sin mensajes antes de considerar muerto al cliente. Como la librería del ESP32 no envía PINGs sola, el código manda un PING cada 30 s.

**R10. ¿Qué hace el gateway?**
Tiene tres piezas:
- `enlace_dispositivo.py`: cliente MQTT hacia HiveMQ;
- `enlace_adafruit.py`: cliente MQTT seguro hacia Adafruit IO;
- `servicio.py`: el orquestador.

Guarda cada lectura y evento en SQLite, reenvía las lecturas a la nube, convierte las órdenes del dashboard en comandos para el ESP32 y mantiene los botones sincronizados con el estado real. *Mostrar:* `gateway/servicio.py`.

**R11. ¿Cómo se conectan con Adafruit IO?**
Por MQTT con TLS (cifrado) en `io.adafruit.com:8883`. El usuario es el de Adafruit y la contraseña es la clave AIO, que está en el archivo `.env` y no se sube a GitHub. Cada feed es un tópico: `usuario/feeds/inv-temperatura`.

**R12. ¿Por qué Adafruit IO y no ThingSpeak?**
Adafruit IO funciona por MQTT en ambos sentidos y trae botones y sliders en el dashboard, así que el control remoto es directo. En ThingSpeak, para recibir comandos el dispositivo tiene que consultar un canal por HTTP cada cierto tiempo.

**R13. ¿Cómo respetan el límite del plan gratuito?**
Adafruit permite 30 datos por minuto. El gateway agrupa los envíos: manda las 4 lecturas cada 20 s, es decir 12 por minuto. Si se excede (por ejemplo, al pulsar muchos botones seguidos), Adafruit avisa con un *throttle warning* y el gateway lo registra en el log.

**R14. ¿Por qué los botones del dashboard se mueven solos?**
Porque el gateway los sincroniza con el estado real. Cuando el ESP32 publica su `estado` y algún botón no coincide, el gateway lo actualiza. Por ejemplo, si en AUTO el ventilador se enciende por calor, el botón pasa a ON.

**R15. ¿No se confunde el gateway con sus propias actualizaciones?**
Adafruit reenvía a los suscriptores todo lo publicado, incluido lo que publica el gateway. Por eso el gateway recuerda qué valor publicó en cada botón e ignora la primera vez que ese mismo valor regresa. Se llama supresión de eco. *Mostrar:* `gateway/enlace_adafruit.py`, diccionario `_eco`.

**R16. ¿Cómo viaja un comando desde el dashboard hasta el relé?**
1. El botón publica en el feed.
2. El gateway lo recibe, lo guarda en la tabla `comandos` como "pendiente" con un `id` y lo envía al ESP32 por HiveMQ.
3. El controlador lo valida y lo ejecuta o lo rechaza.
4. El ESP32 responde con una confirmación (*ack*) con el mismo `id`.
5. El gateway actualiza el comando en la base.

*Mostrar:* `arquitectura.md`, diagrama 3.

**R17. ¿Qué tan seguro es el sistema?**
La conexión con Adafruit va cifrada con TLS y la clave no está en el código. El punto débil es HiveMQ público, que no tiene usuario ni cifrado: cualquiera que conozca el tópico podría leerlo. Lo mitigamos con un tópico propio (`inv-ds8-zcmr`). En producción usaríamos un broker privado con TLS y autenticación.

---

## 5. Estefanny Zambrano: base de datos y históricos

**Z1. ¿Qué base de datos usaron y por qué?**
SQLite: una base SQL completa en un solo archivo (`data/invernadero.db`), sin instalar un servidor. Es suficiente para un gateway y fácil de entregar. Si hubiera muchos dispositivos, se migraría a PostgreSQL cambiando solo `database.py`.

**Z2. ¿Qué tablas tiene?**
- **dispositivos:** cada ESP32 con su último estado y conexión.
- **lecturas:** temperatura, humedad, luminosidad, humedad del suelo y fecha.
- **eventos:** tipo y detalle en JSON (cambios de actuadores, modo, alertas, confirmaciones, conexión).
- **comandos:** origen, acción, parámetro, valor, estado, motivo y fechas.

*Mostrar:* `sql/schema.sql`.

**Z3. ¿Cómo se relacionan las tablas?**
`lecturas`, `eventos` y `comandos` tienen una llave foránea `dispositivo_id` que apunta a `dispositivos`. Un dispositivo tiene muchas lecturas, eventos y comandos (relación uno a muchos). *Mostrar:* `arquitectura.md`, diagrama 5.

**Z4. ¿Quién crea la base de datos?**
El gateway, al arrancar: ejecuta `sql/schema.sql`. Todas las sentencias usan `CREATE TABLE IF NOT EXISTS`, así que se puede ejecutar siempre sin borrar datos.

**Z5. ¿Por qué la fecha y hora la pone el gateway y no el ESP32?**
Porque el ESP32 no tiene reloj de tiempo real: al encender no sabe la hora. El gateway sí, así que marca cada registro al recibirlo. El ESP32 envía además `uptime_ms`, el tiempo que lleva encendido, como referencia.

**Z6. ¿Cómo registran que un comando se ejecutó?**
El comando se inserta como **pendiente** y su `id` viaja con el comando. El ESP32 responde con un evento de confirmación con ese mismo `id` y el resultado. El gateway actualiza la fila a **ejecutado** o **rechazado**, con el motivo y la hora. Un `CHECK` en la tabla solo permite esos tres estados.

**Z7. ¿Qué consultas de históricos implementaron?**
- últimas N lecturas;
- lecturas entre dos fechas;
- resumen estadístico de las últimas horas (cantidad, promedio, mínimo y máximo);
- promedios por hora;
- historial de alertas;
- cambios de actuadores y quién los provocó;
- comandos con su resultado;
- tasa de éxito por origen;
- exportar a CSV.

*Mostrar:* `sql/consultas.sql` y `python -m gateway.consultas --help`.

**Z8. ¿Qué es `json_extract`?**
Una función de SQLite que extrae un campo de un texto JSON. La tabla `eventos` guarda el detalle en JSON, porque cada tipo de evento tiene datos distintos. Con `json_extract(detalle, '$.actuador')` consultamos qué actuador cambió sin necesitar una tabla por cada tipo.

**Z9. ¿Qué índices tienen y para qué sirven?**
- Lecturas por dispositivo y fecha.
- Eventos por tipo y fecha.
- Comandos por estado y fecha.

Aceleran las búsquedas por rango de fechas y por tipo, que son las consultas de históricos más comunes.

**Z10. ¿Por qué hay un `Lock` en `database.py`?**
Porque los mensajes MQTT llegan en hilos distintos: uno para HiveMQ y otro para Adafruit IO. El `Lock` asegura que solo un hilo use la conexión a la base a la vez, para evitar errores por escrituras simultáneas.

**Z11. ¿Cuántos datos genera el sistema?**
Una lectura cada 10 s son 360 por hora y 8 640 por día, más los eventos y comandos. En SQLite eso ocupa muy poco (del orden de 1 MB por día o menos) y con los índices las consultas siguen siendo rápidas.

**Z12. ¿Qué es el patrón Repositorio que usaron?**
Todo el SQL está en una sola clase, `BaseDatos`. El resto del código llama métodos como `guardar_lectura()` o `resumen()` sin escribir SQL. Si cambiáramos de base de datos, solo se modificaría esa clase. *Mostrar:* `gateway/database.py`.

---

## 6. Preguntas de profundidad y "qué pasaría si…"

**P1. ¿Qué pasa si se apaga el gateway?** *(Arturo)*
El ESP32 sigue controlando el invernadero con sus reglas locales. Las lecturas de ese periodo no se guardan en la base ni llegan a la nube. Al volver el gateway, recibe el estado retenido y continúa. Una mejora sería guardar en el ESP32 mientras no hay conexión.

**P2. ¿Qué pasa si llegan dos comandos al mismo tiempo?** *(Alberto)*
Cada comando entra a la cola del `EventBus` y se procesa uno por uno, en orden. Cada uno recibe su propia confirmación con su `id`.

**P3. ¿Cómo agregarían un segundo invernadero?** *(Arturo)*
Con otro ESP32 con un `DISPOSITIVO_ID` distinto: cada dispositivo tiene su propio tópico. La base ya guarda el `dispositivo_id` en cada registro, y el gateway se configuraría para escuchar ambos.

**P4. ¿Cómo cambiarían el umbral del ventilador sin reprogramar?** *(Edwin)*
Desde el slider "Temp. máxima" del dashboard, o con `python -m gateway.consultas enviar umbral temp_max 28`. El ESP32 lo aplica al instante con el comando `umbral`.

**P5. ¿Qué pasa si el sensor DHT22 falla?** *(Edwin)*
La lectura lanza un error, que se captura y se reporta como evento "error" a la base de datos. El programa no se detiene: vuelve a intentar en la siguiente lectura.

**P6. ¿Qué formato tienen los mensajes y por qué?** *(Arturo)*
JSON: es legible, lo entienden tanto MicroPython (`ujson`) como Python, y permite agregar campos sin romper nada. Por ejemplo: `{"temperatura": 26.0, "humedad": 60.0, "luminosidad": 75.6, "humedad_suelo": 53.8}`.

**P7. ¿Por qué el ESP32 publica el estado solo cuando cambia?** *(Alberto)*
Para no saturar la red ni la nube. El estado se compara con el último publicado y solo se envía si hay diferencia, o cuando se reconecta o responde un comando.

**P8. ¿Qué es un "edge gateway" o computación en el borde?** *(Alberto)*
Procesar datos cerca del dispositivo, en la red local, en vez de enviarlo todo a la nube. Nuestro gateway guarda, filtra y controla localmente, y solo manda a la nube lo necesario.

---

## 7. Si algo falla durante la demo

| Situación | Qué decir y hacer | Quién |
|---|---|---|
| El WiFi de Wokwi tarda en conectar | "El WiFi simulado de Wokwi a veces tarda. Nuestro código lo reintenta solo cada 20 segundos, que es justo el manejo de desconexiones." Esperar | Arturo |
| El dashboard no se actualiza al instante | "El gateway reenvía a la nube cada 20 segundos para respetar el límite del plan gratuito." Esperar unos segundos | Arturo |
| Aparece "THROTTLE WARNING" en Adafruit | "Pulsamos muchos controles seguidos y superamos los 30 datos por minuto del plan gratuito. El sistema sigue funcionando." Esperar entre clics | Arturo |
| Un botón no responde en el dashboard | Revisar el modo: en AUTO se rechaza a propósito. Mostrar el aviso en *Alertas* | Edwin |
| Wokwi no conecta en absoluto | Usar `python herramientas/simulador_dispositivo.py`, que simula el ESP32 con el mismo controlador, y seguir la demo del dashboard y la base de datos | Arturo |
| Una consulta no muestra datos | Verificar que el gateway esté corriendo. Mostrar `python -m gateway.consultas comandos`, que tiene datos de las pruebas | Estefanny |

---

## 8. "Muéstrenme en el código…"

| Si el profesor pide ver… | Archivo | Qué buscar | Quién |
|---|---|---|---|
| La programación por eventos | `dispositivo/event_bus.py` | `suscribir`, `emitir`, `despachar` | Alberto |
| El bucle principal | `dispositivo/main.py` | `ejecutar()` y `Temporizador` | Alberto |
| La interrupción del botón | `dispositivo/main.py` | `_isr_boton` | Alberto |
| La lectura de sensores | `dispositivo/sensores.py` | `SensorDHT22`, `SensorAnalogico` | Edwin |
| El manejo de GPIO | `dispositivo/actuadores.py` | `SalidaDigital`, `Buzzer` | Edwin |
| Las reglas y la histéresis | `dispositivo/controlador.py` | `_reglas_automaticas`, `_con_histeresis` | Edwin |
| La alarma | `dispositivo/controlador.py` | `_evaluar_alarma` | Edwin |
| Los umbrales y pines | `dispositivo/config.py` | `UMBRALES`, `PIN_*` | Edwin |
| El cliente MQTT del ESP32 | `dispositivo/red.py` | `ClienteMQTT`, `set_last_will`, `revisar` | Arturo |
| La conexión con Adafruit | `gateway/enlace_adafruit.py` | `tls_set`, `_eco` | Arturo |
| La lógica del gateway | `gateway/servicio.py` | `procesar_telemetria`, `procesar_orden_nube` | Arturo |
| El esquema de la base | `sql/schema.sql` | las 4 tablas | Estefanny |
| Las consultas SQL | `sql/consultas.sql` | las 9 consultas | Estefanny |
| El acceso a datos | `gateway/database.py` | `BaseDatos` | Estefanny |
