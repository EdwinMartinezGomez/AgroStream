import os


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
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/reverse"
OPENMETEO_VARS = (
    "temperature_2m,"
    "relative_humidity_2m,"
    "shortwave_radiation,"
    "soil_moisture_0_to_1cm,"
    "precipitation"
)
OPENMETEO_DIAS = 1
OPENMETEO_TZ = "America/Bogota"
REDIS_URL = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "dinosaurs-tiger-nonstick-54174.db.redis.io")
REDIS_PORT = int(os.getenv("REDIS_PORT", "17678"))
REDIS_DB   = int(os.getenv("REDIS_DB", "0"))
REDIS_USERNAME = os.getenv("REDIS_USERNAME", "default")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "RCHBm1Nzd6uSc0lGlZ1w6ST0PNvohXBA")
REDIS_TTL  = 86_400
INTERVALO_LECTURA_S = 5
PROB_ALERTA_SIMULADA = float(os.getenv("PROB_ALERTA_SIMULADA", "0.03"))
SENSORES_POR_FINCA = {
    "temperatura":   2,
    "humedad":       2,
    "co2":           1,
    "humedad_suelo": 3,
    "radiacion":     1,
}
RUIDO = {
    "temperatura":   0.4,
    "humedad":       1.5,
    "co2":           8.0,
    "humedad_suelo": 2.0,
    "radiacion":    15.0,
}
UMBRALES = {
    "temperatura": {
        "critico_bajo":  2.0,
        "critico_alto": 30.0,
    },
    "humedad": {
        "critico_bajo": 30.0,
    },
    "co2": {
        "critico_alto": 1_000,
    },
    "humedad_suelo": {
        "critico_bajo": 20.0,
        "critico_alto": 85.0,
    },
    "radiacion": {
        "critico_alto": 900.0,
    },
}
RANGOS_VALIDOS = {
    "temperatura":   (-10, 50),
    "humedad":       (  0, 100),
    "co2":           (300, 5_000),
    "humedad_suelo": (  0, 100),
    "radiacion":     (  0, 1_400),
}
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = False
