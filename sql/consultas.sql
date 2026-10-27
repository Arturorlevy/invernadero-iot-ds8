-- ===========================================================================
-- consultas.sql - Consultas de históricos del Invernadero IoT
-- Se pueden ejecutar en DB Browser for SQLite, en la extensión SQLite de
-- VS Code, o con:  sqlite3 data/invernadero.db < sql/consultas.sql
-- Las mismas consultas están implementadas en gateway/database.py y se
-- usan desde la CLI:  python -m gateway.consultas --help
-- ===========================================================================

-- 1) Últimas 20 lecturas
SELECT timestamp, temperatura, humedad, luminosidad, humedad_suelo
FROM lecturas
ORDER BY id DESC
LIMIT 20;

-- 2) Lecturas en un rango de fechas
SELECT timestamp, temperatura, humedad, luminosidad, humedad_suelo
FROM lecturas
WHERE timestamp BETWEEN '2026-10-26 00:00:00' AND '2026-10-26 23:59:59'
ORDER BY timestamp;

-- 3) Resumen estadístico de las últimas 24 horas
SELECT COUNT(*)                     AS muestras,
       ROUND(AVG(temperatura), 2)   AS temp_promedio,
       MIN(temperatura)             AS temp_min,
       MAX(temperatura)             AS temp_max,
       ROUND(AVG(humedad), 2)       AS humedad_promedio,
       ROUND(AVG(luminosidad), 2)   AS luz_promedio,
       ROUND(AVG(humedad_suelo), 2) AS suelo_promedio
FROM lecturas
WHERE timestamp >= strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime', '-24 hours');

-- 4) Promedios por hora (útil para graficar tendencias)
SELECT strftime('%Y-%m-%d %H:00', timestamp) AS hora,
       COUNT(*)                     AS muestras,
       ROUND(AVG(temperatura), 2)   AS temp,
       ROUND(AVG(humedad), 2)       AS humedad,
       ROUND(AVG(luminosidad), 2)   AS luz,
       ROUND(AVG(humedad_suelo), 2) AS suelo
FROM lecturas
GROUP BY hora
ORDER BY hora DESC
LIMIT 24;

-- 5) Historial de alertas
SELECT timestamp,
       json_extract(detalle, '$.activa') AS activa,
       json_extract(detalle, '$.motivo') AS motivo
FROM eventos
WHERE tipo = 'alerta'
ORDER BY id DESC;

-- 6) Cambios de actuadores y quién los provocó (auto / remoto)
SELECT timestamp,
       json_extract(detalle, '$.actuador') AS actuador,
       json_extract(detalle, '$.valor')    AS encendido,
       json_extract(detalle, '$.origen')   AS origen
FROM eventos
WHERE tipo = 'actuador'
ORDER BY id DESC
LIMIT 50;

-- 7) Cuántas veces se encendió cada actuador
SELECT json_extract(detalle, '$.actuador') AS actuador,
       COUNT(*)                            AS encendidos
FROM eventos
WHERE tipo = 'actuador' AND json_extract(detalle, '$.valor') = 1
GROUP BY actuador;

-- 8) Comandos ejecutados / rechazados
SELECT id, creado_en, origen, accion, parametro, valor, estado, motivo, resuelto_en
FROM comandos
ORDER BY id DESC
LIMIT 50;

-- 9) Tasa de éxito de comandos por origen
SELECT origen,
       COUNT(*)                                          AS total,
       SUM(estado = 'ejecutado')                         AS ejecutados,
       SUM(estado = 'rechazado')                         AS rechazados,
       SUM(estado = 'pendiente')                         AS pendientes
FROM comandos
GROUP BY origen;
