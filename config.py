# config.py — Configuración central del simulador de monitoreo agrícola
# Ajusta fincas, umbrales e intervalos aquí sin tocar el resto del código.

# ── Fincas a monitorear ─────────────────────────────────────────────────────
# Coordenadas reales en Boyacá, Colombia
FINCAS = [
    {
        "id":        "finca_001",
        "nombre":    "Finca El Roble",
        "lat":        5.53,
        "lon":       -73.36,
        "altitud_m":  2600,
    },
    {
        "id":        "finca_002",
        "nombre":    "Finca La Esperanza",
        "lat":        5.70,
        "lon":       -73.20,
        "altitud_m":  2400,
    },
    {
        "id":        "finca_003",
        "nombre":    "Finca Los Pinos",
        "lat":        5.45,
        "lon":       -73.50,
        "altitud_m":  2800,
    },
]

# ── Open-Meteo ──────────────────────────────────────────────────────────────
# Variables que se solicitan a la API (hourly forecast)
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_VARS = (
    "temperature_2m,"
    "relative_humidity_2m,"
    "shortwave_radiation,"
    "soil_moisture_0_to_1cm,"
    "precipitation"
)
# Días de pronóstico a descargar (1 = hoy, máx 16 sin clave API)
OPENMETEO_DIAS = 1
# Zona horaria para las horas del pronóstico
OPENMETEO_TZ = "America/Bogota"

# ── Redis ────────────────────────────────────────────────────────────────────
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB   = 0
REDIS_TTL  = 86_400          # 24 horas en segundos

# ── Simulación ───────────────────────────────────────────────────────────────
INTERVALO_LECTURA_S = 5      # segundos entre lecturas de cada sensor
SENSORES_POR_FINCA = {
    "temperatura":   2,
    "humedad":       2,
    "co2":           1,
    "humedad_suelo": 3,
    "radiacion":     1,
}

# Ruido gaussiano (σ) añadido sobre el valor de Open-Meteo
RUIDO = {
    "temperatura":   0.4,    # °C
    "humedad":       1.5,    # %
    "co2":           8.0,    # ppm
    "humedad_suelo": 2.0,    # %
    "radiacion":    15.0,    # W/m²
}

# ── Umbrales de alerta ───────────────────────────────────────────────────────
UMBRALES = {
    "temperatura": {
        "critico_bajo":  2.0,    # °C — riesgo de helada
        "critico_alto": 30.0,    # °C — estrés térmico
    },
    "humedad": {
        "critico_bajo": 30.0,    # % — sequía atmosférica
    },
    "co2": {
        "critico_alto": 1_000,   # ppm — ventilación deficiente
    },
    "humedad_suelo": {
        "critico_bajo": 20.0,    # % — estrés hídrico
        "critico_alto": 85.0,    # % — encharcamiento
    },
    "radiacion": {
        "critico_alto": 900.0,   # W/m² — radiación excesiva
    },
}

# Rangos físicos válidos para validación de lecturas
RANGOS_VALIDOS = {
    "temperatura":   (-10, 50),
    "humedad":       (  0, 100),
    "co2":           (300, 5_000),
    "humedad_suelo": (  0, 100),
    "radiacion":     (  0, 1_400),
}
