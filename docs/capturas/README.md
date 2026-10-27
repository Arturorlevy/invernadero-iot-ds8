# Capturas

| Archivo | Qué muestra |
|---|---|
| `01_circuito_wokwi.png` | Circuito completo en Wokwi: ESP32, DHT22, LDR, potenciómetro, 2 relés, LEDs, buzzer, botón y LCD I2C |
| `02_simulacion_normal.png` | Simulación en condiciones normales (26 °C): el LCD muestra las lecturas, modo AUTO, actuadores apagados. El monitor serie muestra la conexión WiFi/MQTT y la telemetría |
| `03_simulacion_alerta.png` | Condiciones extremas (39 °C, suelo 20 %, poca luz): ventilador, bomba y luz encendidos (`VBL`), alarma activa (`!`, LED rojo y buzzer) |
| `04_comandos_remotos.png` | Comandos enviados desde la PC por MQTT y ejecutados por el ESP32 (cambio de modo, apagar ventilador), vistos en el monitor serie |
| `05_gateway_ejecucion.png` | Log del gateway: recibe la telemetría, guarda en SQLite, registra eventos y el ack de cada comando |
| `06_consultas_sqlite.png` | Consultas de históricos: últimas lecturas, resumen estadístico, comandos (ejecutados y rechazados) y eventos |
| `07_dashboard_adafruit.png` | Dashboard de Adafruit IO con gráficas en tiempo real y controles remotos |
