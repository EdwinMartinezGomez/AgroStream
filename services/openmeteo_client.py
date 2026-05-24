import json
import logging
import math
import time
from datetime import datetime, timezone
from pathlib import Path
import requests
from config import (
    OPENMETEO_DIAS, OPENMETEO_TZ, OPENMETEO_URL, OPENMETEO_VARS,
)
logger = logging.getLogger(__name__)
CACHE_DIR = Path("cache/openmeteo")
CACHE_TTL_S = 3_600
def _ruta_cache(lat: float, lon: float) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{lat}_{lon}.json"
def _cache_vigente(ruta: Path) -> bool:
    if not ruta.exists():
        return False
    edad = time.time() - ruta.stat().st_mtime
    return edad < CACHE_TTL_S
def _fetch_openmeteo(lat: float, lon: float) -> dict:
    params = {
        "latitude":      lat,
        "longitude":     lon,
        "hourly":        OPENMETEO_VARS,
        "current":       OPENMETEO_VARS,
        "forecast_days": OPENMETEO_DIAS,
        "timezone":      OPENMETEO_TZ,
    }
    resp = requests.get(OPENMETEO_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()
def _parsear_respuesta(raw: dict) -> dict:
    hourly = raw.get("hourly", {})
    times  = hourly.get("time", [])
    resultado = {}
    for i, ts in enumerate(times):
        hora_str = ts[11:16]
        resultado[hora_str] = {
            "temperatura":   _val(hourly, "temperature_2m",          i),
            "humedad":       _val(hourly, "relative_humidity_2m",     i),
            "radiacion":     _val(hourly, "shortwave_radiation",      i),
            "hum_suelo_raw": _val(hourly, "soil_moisture_0_to_1cm",   i),
            "precipitacion": _val(hourly, "precipitation",            i),
        }
    current = raw.get("current", {})
    resultado["_current"] = {
        "temperatura":   current.get("temperature_2m"),
        "humedad":       current.get("relative_humidity_2m"),
        "radiacion":     current.get("shortwave_radiation"),
        "hum_suelo_raw": current.get("soil_moisture_0_to_1cm"),
        "precipitacion": current.get("precipitation", 0),
    }
    return resultado
def _val(hourly: dict, key: str, i: int):
    vals = hourly.get(key, [])
    return vals[i] if i < len(vals) else None
def _fallback_hora(lat: float, altitud_m: float, hora: float) -> dict:
    lapse  = max(0.0, (altitud_m - 2_000) * 0.0065)
    t_base = 16.0 - lapse
    t_amp  = 8.0
    fase = (hora - 5) / 9 * math.pi
    if 5 <= hora <= 19:
        temp = t_base + t_amp * math.sin(fase)
    else:
        frac = (hora - 19) % 24 / 10
        temp = (t_base + t_amp) - t_amp * frac
    humedad  = max(20.0, min(98.0, 78 - (temp - t_base) * 2.2))
    if 6 <= hora <= 18:
        radiacion = 600 * math.exp(-0.5 * ((hora - 12) / 3) ** 2)
    else:
        radiacion = 0.0
    return {
        "temperatura":   round(temp, 2),
        "humedad":       round(humedad, 2),
        "radiacion":     round(radiacion, 2),
        "hum_suelo_raw": 0.25,
        "precipitacion": 0.0,
    }
def obtener_datos(lat: float, lon: float, altitud_m: float = 2600) -> dict:
    ruta = _ruta_cache(lat, lon)
    if _cache_vigente(ruta):
        logger.info("📂  Datos Open-Meteo desde caché para lat=%.2f lon=%.2f", lat, lon)
        with ruta.open() as f:
            cached = json.load(f)
        if cached.get("_mode") != "fallback":
            logger.info(
                "🛰️  Open-Meteo cache mode=%s | horas=%d | current=%s",
                cached.get("_mode", "desconocido"),
                max(0, len(cached) - 2),
                bool(cached.get("_current")),
            )
            return cached
    try:
        logger.info("🌐  Descargando datos Open-Meteo para lat=%.2f lon=%.2f …", lat, lon)
        raw  = _fetch_openmeteo(lat, lon)
        data = _parsear_respuesta(raw)
        data["_mode"] = "openmeteo"
        with ruta.open("w") as f:
            json.dump(data, f)
        logger.info(
            "🛰️  Open-Meteo respuesta recibida | horas=%d | current=%s",
            max(0, len(data) - 2),
            bool(data.get("_current")),
        )
        logger.info("✅  Open-Meteo: %d horas descargadas.", len(data) - 2)
        return data
    except Exception as exc:
        logger.warning("⚠️  Open-Meteo no disponible (%s). Usando modelo físico local.", exc)
    logger.info(
        "🔧  Modo fallback activo — generando valores con modelo físico para lat=%.2f lon=%.2f alt=%.1f.",
        lat,
        lon,
        altitud_m,
    )
    data = {"_mode": "fallback"}
    for h in range(24):
        key = f"{h:02d}:00"
        data[key] = _fallback_hora(lat, altitud_m, float(h))
    hora_actual = datetime.now().hour
    data["_current"] = _fallback_hora(lat, altitud_m, float(hora_actual))
    with ruta.open("w") as f:
        json.dump(data, f)
    logger.info("🛰️  Open-Meteo fallback listo | horas=%d", max(0, len(data) - 2))
    return data
def valor_para_ahora(datos: dict, altitud_m: float = 2600) -> dict:
    current = datos.get("_current", {})
    if current.get("temperatura") is not None:
        return current
    ahora = datetime.now()
    clave = f"{ahora.hour:02d}:00"
    if clave in datos:
        return datos[clave]
    return _fallback_hora(2600, altitud_m, float(ahora.hour))
def co2_para_hora(hora: float) -> float:
    base = 420.0
    amplitud = 35.0
    return round(base + amplitud * math.cos(hora / 24 * 2 * math.pi), 1)
def humedad_suelo_desde_raw(hum_suelo_raw: float, precipitacion: float = 0.0) -> float:
    if hum_suelo_raw is None:
        hum_suelo_raw = 0.25
    pct = (hum_suelo_raw / 0.5) * 100.0
    efecto_lluvia = min(precipitacion * 5, 20.0) if precipitacion else 0.0
    return round(min(100.0, max(0.0, pct + efecto_lluvia)), 2)
