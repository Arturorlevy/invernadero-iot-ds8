"""
config.py - Configuración central del dispositivo (ESP32 / MicroPython).

Todos los parámetros ajustables del invernadero viven aquí: red, MQTT,
pines GPIO, intervalos de muestreo y umbrales de control. Así el resto
de módulos no tiene "números mágicos" y se puede recalibrar sin tocar
la lógica.
"""

# ---------------------------------------------------------------------------
# Red WiFi (Wokwi expone una red abierta llamada "Wokwi-GUEST")
# ---------------------------------------------------------------------------
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

# ---------------------------------------------------------------------------
# MQTT (broker público de HiveMQ)
# IMPORTANTE: cambie DISPOSITIVO_ID por algo único (p. ej. sus iniciales),
# porque el broker es público y otros grupos podrían usar el mismo tópico.
# Debe coincidir con DISPOSITIVO_ID del archivo .env del gateway.
# ---------------------------------------------------------------------------
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE_S = 60
DISPOSITIVO_ID = "inv-ds8-zcmr"
TOPICO_RAIZ = "ds8/invernadero"
TOPICO_BASE = TOPICO_RAIZ + "/" + DISPOSITIVO_ID

# Sub-tópicos (TOPICO_BASE + "/" + sufijo)
T_TELEMETRIA = "telemetria"   # dispositivo -> nube : lecturas de sensores
T_ESTADO = "estado"           # dispositivo -> nube : estado de actuadores (retenido)
T_EVENTOS = "eventos"         # dispositivo -> nube : cambios, alertas, acks
T_CONEXION = "conexion"       # dispositivo -> nube : online/offline (LWT)
T_COMANDOS = "comandos"       # nube -> dispositivo : órdenes remotas

# ---------------------------------------------------------------------------
# Pines GPIO (ver diagram.json)
# ---------------------------------------------------------------------------
PIN_DHT22 = 15          # Sensor de temperatura y humedad del aire
PIN_LDR = 34            # Fotorresistencia (salida analógica AO)
PIN_SUELO = 35          # Potenciómetro que simula sensor de humedad de suelo
PIN_BOTON = 4           # Botón local: alterna modo AUTO / MANUAL
PIN_RELE_VENTILADOR = 26
PIN_RELE_BOMBA = 27
PIN_LED_CRECIMIENTO = 14  # Luz artificial de crecimiento
PIN_LED_ALARMA = 13
PIN_BUZZER = 25
PIN_I2C_SDA = 21
PIN_I2C_SCL = 22
LCD_DIRECCION_I2C = 0x27

# ---------------------------------------------------------------------------
# Tiempos (milisegundos)
# ---------------------------------------------------------------------------
INTERVALO_LECTURA_MS = 3000       # cada cuánto se leen sensores
INTERVALO_PUBLICACION_MS = 10000  # cada cuánto se envía telemetría
INTERVALO_RECONEXION_MS = 5000    # espera entre intentos de reconexión MQTT
ANTIRREBOTE_BOTON_MS = 300

# ---------------------------------------------------------------------------
# Umbrales de control automático (se pueden cambiar remotamente)
# ---------------------------------------------------------------------------
UMBRALES = {
    "temp_max": 30.0,         # °C  -> enciende ventilador
    "temp_alerta": 38.0,      # °C  -> alarma por calor extremo
    "temp_min_alerta": 10.0,  # °C  -> alarma por frío
    "suelo_min": 30.0,        # %   -> enciende bomba de riego
    "suelo_alerta": 10.0,     # %   -> alarma por sequía
    "luz_min": 30.0,          # %   -> enciende luz de crecimiento
}

# Histéresis: evita que un actuador "parpadee" cuando la lectura oscila
# alrededor del umbral. Se enciende al cruzar el umbral y se apaga solo
# cuando la variable se aleja HISTERESIS unidades.
HISTERESIS = {
    "temp": 1.5,
    "suelo": 15.0,
    "luz": 10.0,
}
