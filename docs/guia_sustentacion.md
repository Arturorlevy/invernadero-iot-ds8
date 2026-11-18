# Guía para la sustentación (50 % de la nota)

Esta guía está ordenada **en el orden en que se presenta**. Cada integrante tiene su sección con:
- cuánto tiempo le toca;
- qué debe estar en pantalla;
- qué decir (el guion, en primera persona, para estudiarlo y decirlo con sus palabras);
- cómo pasarle la palabra al siguiente;
- las preguntas que le pueden hacer, con su respuesta.

Al final hay **material de apoyo** para todos: el dashboard bloque por bloque, el LCD, el guion de los controles y más preguntas.

## Orden de la presentación

| Orden | Integrante | Tema | Tiempo | Pantalla |
|---|---|---|---|---|
| 1 | **Alberto Chen** | Introducción, arquitectura, circuito y programación orientada a eventos | 3 min | Diagrama de arquitectura → circuito en Wokwi |
| 2 | **Edwin Moreno** | Sensores, actuadores y lógica de control (demo en Wokwi) | 3 min | Wokwi corriendo |
| 3 | **Arturo Rodríguez** | Comunicación MQTT, gateway y nube (demo del dashboard) | 3 min | Log del gateway → dashboard de Adafruit IO |
| 4 | **Estefanny Zambrano** | Base de datos, históricos y cierre | 3 min | Terminal con las consultas |

**Total: unos 12 minutos**, más las preguntas del profesor.

## Antes de empezar (5 minutos antes)

1. Abrir una terminal en la carpeta `invernadero-iot` y ejecutar `python -m gateway`. Esperar a ver "Conectado a Adafruit IO" y "Conectado al broker del dispositivo".
2. Abrir el proyecto en Wokwi y pulsar ▶. Esperar a ver `[mqtt] conectado` en el monitor serie. Si el WiFi de Wokwi tarda, el ESP32 reintenta solo: esperar hasta un par de minutos.
3. Abrir el dashboard de Adafruit IO en otra pestaña y comprobar que los medidores muestran datos.
4. Dejar el modo en **AUTO** y el DHT22 en **26 °C**, para empezar desde condiciones normales.
5. Tener abiertas, en este orden: el diagrama de arquitectura (`docs/arquitectura.md` en GitHub, o `Arquitectura_IoT.docx`), la pestaña de Wokwi, el dashboard y una segunda terminal para las consultas.

---

## 1. Alberto Chen: introducción, arquitectura y eventos

**Tiempo:** 3 minutos.
**En pantalla:** primero el diagrama de capas de `arquitectura.md`, después el circuito en Wokwi y, al final, `event_bus.py`.

### Qué decir

**Apertura (todo el grupo):**
> "Buenos días. Somos Estefanny Zambrano, Alberto Chen, Edwin Moreno y Arturo Rodríguez, y les presentamos nuestro Sistema IoT de Invernadero Inteligente."

**El problema y la solución:**
> "Elegimos el escenario de invernadero inteligente. Un invernadero necesita mantener temperatura, humedad, luz y riego en rangos adecuados para las plantas. Nuestro sistema mide esas variables, actúa solo cuando se salen de rango y permite verlas y controlarlas desde la nube."

**La arquitectura (señalando el diagrama de capas):**
> "El sistema sigue la arquitectura IoT de cuatro capas:
> - **Percepción:** un ESP32 simulado en Wokwi, programado en MicroPython, con los sensores y actuadores.
> - **Red:** el ESP32 se conecta por WiFi y habla por MQTT con el broker público de HiveMQ.
> - **Procesamiento:** un gateway en Python que corre en la PC, guarda todo en SQLite y hace de puente con la nube.
> - **Aplicación:** Adafruit IO, donde está el dashboard con gráficas y controles remotos."

**Por qué hay un gateway:**
> "Pusimos un gateway en el medio por tres razones. El enunciado pide un broker MQTT como HiveMQ en el dispositivo. Una base de datos SQL no corre en un microcontrolador. Y así la clave de la nube no queda grabada en el ESP32. Esto se conoce como patrón *edge gateway*."

**El circuito (cambiando a Wokwi):**
> "Este es el circuito. Usamos tres sensores:
> - el DHT22 para temperatura y humedad del aire, en el GPIO 15;
> - un sensor de luz LDR en el GPIO 34;
> - un potenciómetro que simula un sensor de humedad de suelo, en el GPIO 35.
>
> Y seis actuadores y salidas:
> - dos relés, uno para el ventilador (GPIO 26) y otro para la bomba de riego (GPIO 27);
> - un LED amarillo como luz de crecimiento;
> - un LED rojo y un buzzer para la alarma;
> - una pantalla LCD por I2C.
>
> Además hay un botón para cambiar entre modo automático y manual."

**Programación orientada a eventos (mostrando `event_bus.py`):**
> "El código es modular y orientado a eventos. El corazón es este `EventBus`, un patrón publicador/suscriptor. Los módulos no se llaman entre sí: los sensores emiten un evento 'lectura', MQTT emite 'comando' y el botón emite 'boton'. El controlador, la pantalla y la publicación MQTT se suscriben a esos eventos.
>
> El bucle principal nunca se bloquea. En vez de usar `sleep` largos, usa temporizadores por software: lee los sensores cada 3 segundos y publica cada 10. El botón usa una interrupción que solo encola el evento, con un antirrebote de 300 milisegundos."

**Transición:**
> "Ahora Edwin les va a mostrar cómo funcionan los sensores y la lógica de control en vivo."

### Preguntas que le pueden hacer
- **¿Por qué orientado a eventos?** Porque desacopla los módulos: se puede agregar un nuevo actuador suscribiéndolo a un evento, sin tocar el código de los sensores. Además, el bucle atiende sensores, red y botón "a la vez" sin bloquearse.
- **¿Por qué la interrupción no ejecuta la lógica directamente?** Porque el código dentro de una interrupción debe ser mínimo y rápido. Solo encola el evento, y el bucle principal lo procesa después con `bus.despachar()`.
- **¿Qué pasa si se cae Internet?** El control local sigue funcionando, porque las reglas corren en el ESP32. Arturo explica la reconexión.
- **¿Qué es el Temporizador?** Una clase que compara `ticks_ms()` con la última ejecución. Si pasó el intervalo, devuelve `True`. Así se programan tareas periódicas sin `sleep`.

---

## 2. Edwin Moreno: sensores, actuadores y control

**Tiempo:** 3 minutos.
**En pantalla:** Wokwi corriendo, con el LCD y el monitor serie visibles. Si sobra tiempo, `controlador.py`.

### Qué decir

**Los sensores:**
> "Les explico cómo leemos cada sensor:
> - El **DHT22** usa un protocolo digital de un solo hilo y entrega la temperatura en grados y la humedad en porcentaje.
> - El **LDR** y el **potenciómetro** son analógicos. Los leemos con el ADC de 12 bits del ESP32, configurado con atenuación de 11 dB para medir de 0 a 3.3 voltios, y convertimos el valor a porcentaje.
> - El LDR lo invertimos, porque su voltaje baja cuando hay más luz."

**El LCD (señalándolo):**
> "En el LCD la primera línea muestra temperatura, humedad y el modo, AUTO o MAN. La segunda muestra luz, humedad del suelo y qué actuadores están encendidos: V de ventilador, B de bomba, L de luz, y un signo de exclamación si hay alarma."

**La lógica de control:**
> "En modo automático el sistema decide solo con tres reglas:
> - **Ventilador:** se enciende cuando la temperatura llega a 30 °C.
> - **Bomba de riego:** se enciende cuando la humedad del suelo baja a 30 %.
> - **Luz de crecimiento:** se enciende cuando la luz baja a 30 %."

**Demo de la histéresis (subir el DHT22 a 32 °C):**
> "Subo la temperatura a 32 grados... y se enciende el ventilador: el relé se activa y aparece la V en el LCD."

*(Bajar a 29 °C.)*
> "Ahora la bajo a 29 y el ventilador **sigue encendido**. Esto es la **histéresis**: se enciende a 30 pero solo se apaga cuando baja de 28.5. Sin ella, si la temperatura oscila entre 29.9 y 30.1, el relé se prendería y apagaría en cada lectura, y eso desgasta los relés."

*(Bajar a 28 °C.)*
> "A 28 grados se apaga."

**Demo de la alarma (subir a 39 °C):**
> "Si la temperatura llega a 38 grados, se activa la alarma: el LED rojo se enciende y el buzzer suena de forma intermitente. El buzzer funciona con PWM a 2 kHz y alterna sonido y silencio cada medio segundo sin bloquear el programa. La alarma también salta con temperatura bajo 10 grados o suelo bajo 10 %. Funciona en los dos modos, porque es una función de seguridad."

*(Volver a 26 °C.)*

**Los modos (pulsar el botón azul):**
> "Con el botón cambiamos a modo manual: el LCD muestra MAN. En manual, las reglas se desactivan y los actuadores solo obedecen órdenes remotas desde la nube. Si alguien intenta controlar un actuador en modo automático, el sistema rechaza la orden, porque la regla la desharía tres segundos después."

*(Volver a AUTO con el botón.)*

**Transición:**
> "¿Y cómo llegan esas órdenes desde la nube? Arturo les explica la comunicación."

### Preguntas que le pueden hacer
- **¿Qué es la histéresis?** Usar dos umbrales distintos para encender y apagar, para evitar que el actuador conmute sin parar alrededor del umbral.
- **¿Por qué atenuación de 11 dB?** Para que el ADC del ESP32 mida todo el rango de 0 a 3.3 V. Sin atenuación solo mide hasta unos 1.1 V.
- **¿Qué es PWM?** Modulación por ancho de pulso: una señal que se prende y apaga muy rápido. En el buzzer, la frecuencia define el tono (2 kHz) y el ciclo de trabajo, el volumen (50 %).
- **¿Cómo funciona el LCD?** Por I2C, con un adaptador PCF8574 en la dirección 0x27. El LCD trabaja en modo de 4 bits, así que cada carácter se envía en dos mitades. El controlador lo escribimos nosotros en `lcd_i2c.py`.
- **¿Por qué un potenciómetro como sensor de suelo?** Wokwi no tiene sensor de humedad de suelo. El potenciómetro entrega un voltaje analógico variable, igual que un sensor capacitivo real.
- **¿Cómo cambian los valores en Wokwi?** Los sensores son simulados: se cambian con los deslizadores al hacer clic en cada componente.

---

## 3. Arturo Rodríguez: MQTT, gateway y nube

**Tiempo:** 3 minutos.
**En pantalla:** primero la terminal con el log del gateway, después el dashboard de Adafruit IO.

### Qué decir

**MQTT:**
> "Para la comunicación usamos **MQTT**, un protocolo publicador/suscriptor muy liviano, pensado para IoT. Los dispositivos no se hablan directamente: publican mensajes en *tópicos* y un *broker*, en nuestro caso HiveMQ, los reparte a quienes estén suscritos."

**Los tópicos:**
> "El ESP32 usa cinco tópicos:
> - **telemetria:** las lecturas, cada 10 segundos.
> - **estado:** qué actuadores están encendidos. Es un mensaje *retenido*: el broker guarda el último y se lo entrega a cualquiera que se conecte.
> - **eventos:** cambios de actuadores, alertas y las confirmaciones de los comandos.
> - **conexion:** online u offline.
> - **comandos:** las órdenes que llegan desde la nube."

**QoS y Last Will:**
> "Usamos QoS 0 para la telemetría: si se pierde una lectura, llega otra en 10 segundos. Para los comandos usamos QoS 1, que garantiza que lleguen al menos una vez. Además configuramos un **Last Will**: si el ESP32 se desconecta de golpe, el broker publica 'offline' en su nombre y nos enteramos."

**Reconexión:**
> "Si se cae el WiFi o el broker, el ESP32 reintenta solo en segundo plano, sin detener el control local. Lo comprobamos en Wokwi: con la red lenta, el ESP32 arrancó sin WiFi y se recuperó solo."

**El gateway (mostrando el log):**
> "Este es el gateway en Python. Aquí se ve cómo recibe cada lectura del ESP32 por MQTT y la guarda en la base de datos. También se conecta a Adafruit IO por MQTT seguro, con TLS en el puerto 8883, y reenvía las lecturas. Lo hace cada 20 segundos, porque el plan gratuito de Adafruit permite 30 datos por minuto, y nosotros enviamos 12."

**El dashboard (cambiando a Adafruit IO):**
> "Este es el dashboard:
> - **Arriba**, dos gráficas con el historial: temperatura y humedad del aire, y luz y humedad del suelo.
> - **En el medio**, los medidores con el valor actual y los controles: el modo, el ventilador, la bomba, la luz de crecimiento y un slider para cambiar el umbral de temperatura.
> - **Abajo**, las alertas."

**Demo de los controles:**

*(Con el sistema en AUTO, pulsar "Bomba".)*
> "Si intento encender la bomba en modo automático, el sistema rechaza la orden. Aparece el aviso en Alertas y el botón vuelve solo a su posición real."

*(Cambiar "Modo" a MANUAL y pulsar "Bomba ON".)*
> "Ahora cambio a manual y enciendo la bomba... y en Wokwi se activa el relé y aparece la B en el LCD."

*(Volver a AUTO.)*

> "Cuando pulso un botón, la orden viaja así: de Adafruit IO al gateway, el gateway la registra y la manda al ESP32 por HiveMQ con un número de identificación, el ESP32 la ejecuta o la rechaza, y responde con una confirmación."

**Transición:**
> "Todas esas lecturas, eventos y comandos quedan guardados. Estefanny les muestra la base de datos."

### Preguntas que le pueden hacer
- **¿Qué diferencia hay entre QoS 0, 1 y 2?** 0: se envía una vez, sin confirmación. 1: al menos una vez, con confirmación (puede duplicarse). 2: exactamente una vez, más lento. Usamos 0 y 1.
- **¿Qué es un mensaje retenido?** El broker guarda el último mensaje de un tópico y se lo entrega a cada nuevo suscriptor. Así el gateway conoce el estado actual apenas se conecta.
- **¿Por qué los botones del dashboard se mueven solos?** Porque el gateway los sincroniza con el estado real del ESP32. Si en AUTO se enciende el ventilador por calor, el botón pasa a ON.
- **¿No se confunde el gateway con sus propios mensajes?** Adafruit reenvía todo lo publicado, incluso lo que publica el gateway. Por eso el gateway recuerda lo que publicó e ignora ese "eco": se llama supresión de eco.
- **¿Qué es TLS?** Cifrado de la conexión. La clave de Adafruit viaja protegida, y está en un archivo `.env` que no se sube a GitHub.
- **¿Qué es el keepalive?** El intervalo en el que el cliente avisa al broker que sigue vivo. El ESP32 envía un PING cada 30 segundos.
- **¿Qué pasa si se pulsa muy rápido?** Adafruit limita a 30 datos por minuto y muestra un aviso de *throttle*. Por eso el gateway agrupa los envíos.

---

## 4. Estefanny Zambrano: base de datos, históricos y cierre

**Tiempo:** 3 minutos.
**En pantalla:** la segunda terminal, con las consultas. Si preguntan, `sql/schema.sql`.

### Qué decir

**La base de datos:**
> "Para el almacenamiento usamos **SQLite**, una base de datos SQL en un solo archivo, sin servidor, ideal para un gateway. El gateway la crea solo al arrancar a partir del script `sql/schema.sql`."

**Las tablas:**
> "Tiene cuatro tablas:
> - **dispositivos:** los ESP32 conocidos y su último estado.
> - **lecturas:** cada medición de los sensores con su fecha y hora.
> - **eventos:** los cambios de actuadores, las alertas y las conexiones.
> - **comandos:** cada orden enviada y su resultado.
>
> Las tres últimas se relacionan con dispositivos por una llave foránea. Tienen índices por fecha para que las consultas de históricos sean rápidas."

**El timestamp:**
> "La fecha y hora la pone el gateway al recibir el mensaje, porque el ESP32 no tiene un reloj de tiempo real."

**Demo de consultas:**

*(Ejecutar `python -m gateway.consultas ultimas -n 5`.)*
> "Aquí están las últimas lecturas que acaban de llegar durante la demo."

*(Ejecutar `python -m gateway.consultas resumen --horas 24`.)*
> "Este es un resumen de las últimas 24 horas: cantidad de muestras, temperatura promedio, mínima y máxima, y los promedios de humedad, luz y suelo."

*(Ejecutar `python -m gateway.consultas eventos --tipo alerta`.)*
> "Este es el historial de alertas, por ejemplo la de temperatura alta que provocó Edwin."

*(Ejecutar `python -m gateway.consultas comandos`.)*
> "Y aquí la trazabilidad de los comandos. Cada comando se guarda como *pendiente* con un número. Cuando el ESP32 responde, se marca como *ejecutado* o *rechazado*, con el motivo. Aquí está el que rechazó el sistema en la demo de Arturo, con el motivo 'el sistema está en AUTO'. Abajo están las estadísticas por origen."

> "Las mismas consultas también están en SQL puro en `sql/consultas.sql`, para ejecutarlas en cualquier cliente de SQLite."

**Cierre:**
> "En resumen, cumplimos todos los requisitos del parcial:
> - tres sensores y seis actuadores;
> - código Python modular y orientado a eventos;
> - cliente MQTT en el dispositivo con HiveMQ;
> - base de datos SQLite con históricos;
> - plataforma en la nube con dashboard en tiempo real;
> - control remoto bidireccional.
>
> Todo el código, los scripts SQL, los diagramas y las capturas están en nuestro repositorio de GitHub. Muchas gracias. Quedamos atentos a sus preguntas."

### Preguntas que le pueden hacer
- **¿Por qué SQLite y no MySQL?** No necesita instalar un servidor y es un solo archivo, fácil de entregar y revisar. Para muchos dispositivos se migraría a PostgreSQL o MySQL, y solo cambiaría `database.py`.
- **¿Qué es `json_extract`?** Una función de SQLite que extrae un campo de un texto JSON. La tabla `eventos` guarda el detalle en JSON, y con `json_extract` consultamos, por ejemplo, qué actuador cambió.
- **¿Por qué hay un `Lock` en `database.py`?** Porque los mensajes MQTT llegan en hilos distintos (uno para HiveMQ y otro para Adafruit). El Lock evita que dos hilos escriban en la base al mismo tiempo.
- **¿Cómo se registra que un comando se ejecutó?** El gateway inserta el comando como pendiente, lo envía con su `id`, y el ESP32 responde con un evento de confirmación (*ack*) con ese mismo `id`. Con eso se actualiza la fila.
- **¿Qué es un índice?** Una estructura que acelera las búsquedas. Tenemos índices por dispositivo y fecha en lecturas, por tipo y fecha en eventos, y por estado en comandos.
- **¿Qué mejorarían?**
  - MQTT con TLS y usuario también en HiveMQ.
  - Sincronizar la hora del ESP32 por NTP.
  - Guardar lecturas cuando no hay red y enviarlas al reconectar.
  - Pasar a PostgreSQL con muchos dispositivos.

---

## Material de apoyo para todos

Todos deben poder responder sobre la vista general del sistema. Lo que sigue amplía cada tema.

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

## Más preguntas probables (para todos)

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
