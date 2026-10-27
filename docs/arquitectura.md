# Arquitectura IoT — Invernadero Inteligente

## 1. Vista general (capas)

El sistema sigue la arquitectura IoT clásica de capas: **percepción → red → procesamiento/almacenamiento → aplicación**.

```mermaid
flowchart LR
    subgraph P["Capa de percepción - ESP32 en Wokwi (MicroPython)"]
        S1[DHT22<br/>temp + humedad] --> C
        S2[LDR<br/>luminosidad] --> C
        S3[Potenciómetro<br/>humedad suelo] --> C
        B[Pulsador<br/>AUTO/MAN] -->|IRQ| C
        C{{Controlador<br/>+ bus de eventos}}
        C --> A1[Relé ventilador]
        C --> A2[Relé bomba]
        C --> A3[LED crecimiento]
        C --> A4[LED alarma + buzzer]
        C --> A5[LCD 16x2]
    end

    subgraph R["Capa de red"]
        H[(Broker MQTT<br/>HiveMQ público<br/>:1883)]
    end

    subgraph G["Capa de procesamiento - Gateway Python (PC)"]
        ED[enlace_dispositivo] <--> SV[servicio<br/>orquestador]
        SV <--> DB[(SQLite<br/>invernadero.db)]
        SV <--> EA[enlace_adafruit]
        CLI[CLI consultas] --> DB
    end

    subgraph N["Capa de aplicación - Nube"]
        AIO[(Adafruit IO<br/>MQTT/TLS :8883)]
        D[Dashboard<br/>gráficas + toggles + slider]
        AIO <--> D
    end

    C <-->|WiFi · MQTT| H
    H <-->|MQTT| ED
    EA <-->|MQTT TLS| AIO
```

**¿Por qué un gateway?** El ESP32 habla con un broker MQTT liviano (HiveMQ), como pide el enunciado. El gateway agrega lo que un microcontrolador no hace bien:

- persistir datos en SQL,
- guardar las credenciales de la nube fuera del dispositivo,
- respetar el límite de tasa de Adafruit IO (30 datos/min en el plan gratuito),
- llevar la trazabilidad de cada comando.

Es el patrón **edge/fog gateway**.

## 2. Flujo de datos

### 2.1 Telemetría (dispositivo → nube)

```mermaid
sequenceDiagram
    participant S as Sensores
    participant E as ESP32 (main.py)
    participant H as HiveMQ
    participant G as Gateway
    participant DB as SQLite
    participant A as Adafruit IO

    loop cada 3 s
        E->>S: leer_todo()
        S-->>E: {temperatura, humedad, luminosidad, humedad_suelo}
        E->>E: bus.emitir("lectura") → controlador aplica reglas
        opt cambia un actuador
            E->>H: /eventos {tipo: actuador}
            E->>H: /estado (retenido)
        end
    end
    loop cada 10 s
        E->>H: /telemetria (JSON)
        H->>G: /telemetria
        G->>DB: INSERT INTO lecturas
        opt han pasado ≥ 20 s desde el último envío
            G->>A: inv-temperatura, inv-humedad, inv-luminosidad, inv-humedad-suelo
        end
    end
```

### 2.2 Comando remoto (nube → dispositivo)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant A as Adafruit IO
    participant G as Gateway
    participant DB as SQLite
    participant H as HiveMQ
    participant E as ESP32

    U->>A: toggle "Ventilador" = ON
    A->>G: inv-ventilador = "ON"
    G->>DB: INSERT comandos (estado = pendiente) → id = 12
    G->>H: /comandos {"id":12,"accion":"set","actuador":"ventilador","valor":1}
    H->>E: /comandos
    E->>E: controlador valida (¿modo MANUAL?)
    alt aceptado
        E->>E: relé ON
        E->>H: /eventos {tipo: comando, id:12, resultado: ejecutado}
    else rechazado (modo AUTO)
        E->>H: /eventos {tipo: comando, id:12, resultado: rechazado, motivo}
    end
    E->>H: /estado (estado real)
    H->>G: /eventos + /estado
    G->>DB: UPDATE comandos SET estado = ... WHERE id = 12
    G->>A: sincroniza toggles con el estado real (y aviso en inv-alertas si se rechazó)
```

### 2.3 Programación orientada a eventos en el ESP32

```mermaid
flowchart TD
    L((Bucle principal<br/>no bloqueante)) --> T1{¿Venció el temporizador<br/>de lectura?}
    T1 -- sí --> R[leer sensores] --> EV1[/evento: lectura/]
    L --> T2{¿Venció el temporizador<br/>de publicación?} -- sí --> PUB[publicar telemetría]
    L --> M[mqtt.revisar] --> EV2[/evento: comando/]
    IRQ[Interrupción del botón] --> EV3[/evento: boton/]
    EV1 & EV2 & EV3 --> Q[(Cola del EventBus)]
    L --> D[bus.despachar]
    Q --> D
    D --> CTRL[Controlador]
    D --> LCD[Pantalla]
    CTRL --> EV4[/actuador_cambiado · alerta ·<br/>modo_cambiado · comando_procesado/]
    EV4 --> Q
    D --> MQ[Publicación MQTT de eventos / estado]
```

Los módulos no se llaman entre sí. Se comunican por eventos a través de `EventBus`, y eso permite agregar un consumidor (por ejemplo, un nuevo actuador) sin tocar a los productores.

## 3. Modelo de datos

```mermaid
erDiagram
    dispositivos ||--o{ lecturas : registra
    dispositivos ||--o{ eventos : genera
    dispositivos ||--o{ comandos : recibe
    dispositivos {
        TEXT id PK
        TEXT ultimo_estado
        TEXT conexion
        TEXT visto_en
    }
    lecturas {
        INTEGER id PK
        TEXT dispositivo_id FK
        REAL temperatura
        REAL humedad
        REAL luminosidad
        REAL humedad_suelo
        TEXT timestamp
    }
    eventos {
        INTEGER id PK
        TEXT dispositivo_id FK
        TEXT tipo
        TEXT detalle "JSON"
        TEXT timestamp
    }
    comandos {
        INTEGER id PK
        TEXT dispositivo_id FK
        TEXT origen
        TEXT accion
        TEXT parametro
        TEXT valor
        TEXT estado "pendiente|ejecutado|rechazado"
        TEXT motivo
        TEXT creado_en
        TEXT resuelto_en
    }
```

El *timestamp* lo pone el gateway al recibir el mensaje, porque el ESP32 no tiene reloj de tiempo real. El ESP32 envía además `uptime_ms` como referencia.

## 4. Tópicos MQTT y QoS

| Tópico | QoS | Retenido | Motivo |
|---|---|---|---|
| `…/telemetria` | 0 | no | Lecturas frecuentes; si se pierde una, llega otra en 10 s |
| `…/eventos` | 0 | no | Notificaciones |
| `…/estado` | 0 | **sí** | Quien se conecte recibe de inmediato el último estado |
| `…/conexion` | 1 | **sí** | *Last Will*: el broker publica `offline` si el ESP32 cae |
| `…/comandos` | 1 | no | Una orden debe llegar al menos una vez |

## 5. Decisiones de diseño

| Decisión | Alternativa | Razón |
|---|---|---|
| Gateway en PC entre HiveMQ y Adafruit IO | ESP32 directo a Adafruit IO | El enunciado pide un broker HiveMQ/Mosquitto/EMQX en el dispositivo. Además, SQLite no corre en el ESP32 y así las credenciales de la nube no quedan en el firmware |
| SQLite | MySQL/PostgreSQL | Sin servidor que instalar. Un solo archivo fácil de entregar y revisar |
| Control on/off con histéresis | Umbral simple | Evita el *chattering* (conmutación rápida) que desgasta los relés |
| Rechazar `set` en modo AUTO | Aceptarlo siempre | Si no, la regla automática deshace la orden manual en la siguiente lectura y el usuario no entiende qué pasó |
| Ack con `id` de comando | *Fire and forget* | Trazabilidad: la tabla `comandos` sabe qué se ejecutó y qué se rechazó |
| Bus de eventos + temporizadores por software | `sleep()` en el bucle | El bucle nunca se bloquea: atiende botón, red y sensores "a la vez" |
