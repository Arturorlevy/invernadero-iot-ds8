-- ===========================================================================
-- schema.sql - Esquema de la base de datos del Invernadero IoT (SQLite)
-- El gateway lo ejecuta automáticamente al iniciar (CREATE ... IF NOT EXISTS).
-- Todas las marcas de tiempo se guardan en hora local, formato ISO-8601.
-- ===========================================================================

PRAGMA foreign_keys = ON;

-- Dispositivos conocidos (se registran solos al recibir su primer mensaje)
CREATE TABLE IF NOT EXISTS dispositivos (
    id            TEXT PRIMARY KEY,
    descripcion   TEXT,
    ultimo_estado TEXT,              -- JSON del último estado reportado
    conexion      TEXT,              -- 'online' / 'offline'
    visto_en      TEXT,
    creado_en     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
);

-- Lecturas de sensores con timestamp
CREATE TABLE IF NOT EXISTS lecturas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    dispositivo_id TEXT    NOT NULL REFERENCES dispositivos(id),
    temperatura    REAL,             -- °C
    humedad        REAL,             -- % humedad relativa del aire
    luminosidad    REAL,             -- % luz relativa
    humedad_suelo  REAL,             -- % humedad del suelo
    uptime_ms      INTEGER,          -- tiempo encendido del ESP32
    timestamp      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_lecturas_disp_ts ON lecturas(dispositivo_id, timestamp);

-- Eventos reportados por el dispositivo:
--   actuador (cambio on/off), modo (AUTO/MANUAL), alerta, comando (ack), error
CREATE TABLE IF NOT EXISTS eventos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    dispositivo_id TEXT    NOT NULL REFERENCES dispositivos(id),
    tipo           TEXT    NOT NULL,
    detalle        TEXT,             -- JSON con los datos del evento
    timestamp      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_eventos_tipo_ts ON eventos(tipo, timestamp);

-- Comandos enviados al dispositivo y su resultado
CREATE TABLE IF NOT EXISTS comandos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    dispositivo_id TEXT    NOT NULL REFERENCES dispositivos(id),
    origen         TEXT    NOT NULL,  -- 'adafruit', 'cli', ...
    accion         TEXT    NOT NULL,  -- 'set', 'modo', 'umbral', 'estado'
    parametro      TEXT,              -- actuador o umbral afectado
    valor          TEXT,
    estado         TEXT    NOT NULL DEFAULT 'pendiente'
                   CHECK (estado IN ('pendiente', 'ejecutado', 'rechazado')),
    motivo         TEXT,              -- razón de rechazo, si aplica
    creado_en      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
    resuelto_en    TEXT
);
CREATE INDEX IF NOT EXISTS idx_comandos_estado ON comandos(estado, creado_en);
