from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import requests

from config import GEOCODING_URL

logger = logging.getLogger(__name__)

CACHE_DIR = Path("cache/geocoding")
CACHE_TTL_S = 24 * 60 * 60


def _ruta_cache(lat: float, lon: float) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{lat}_{lon}.json"


def _cache_vigente(ruta: Path) -> bool:
    if not ruta.exists():
        return False
    return (time.time() - ruta.stat().st_mtime) < CACHE_TTL_S


def _normalizar_resultados(raw: dict) -> dict:
    resultados = raw.get("results") or []
    if not resultados:
        return _fallback()

    principal = resultados[0]
    ciudades = []
    for item in resultados:
        nombre = item.get("name")
        if not nombre:
            continue
        ciudad = {
            "nombre": nombre,
            "departamento": item.get("admin1") or "",
            "pais": item.get("country") or "",
            "distancia_km": item.get("distance"),
        }
        ciudades.append(ciudad)

    return {
        "ciudad_principal": principal.get("name") or "Ubicación cercana",
        "departamento": principal.get("admin1") or "",
        "pais": principal.get("country") or "",
        "ciudades_cercanas": ciudades[:5],
    }


def _fallback() -> dict:
    return {
        "ciudad_principal": "Ubicación cercana",
        "departamento": "",
        "pais": "",
        "ciudades_cercanas": [],
    }


def obtener_ubicacion(lat: float, lon: float) -> dict:
    ruta = _ruta_cache(lat, lon)
    if _cache_vigente(ruta):
        try:
            with ruta.open(encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError, TypeError):
            logger.warning("No se pudo leer la caché geográfica para lat=%.2f lon=%.2f", lat, lon)

    params = {
        "latitude": lat,
        "longitude": lon,
        "language": "es",
        "count": 5,
    }
    try:
        response = requests.get(GEOCODING_URL, params=params, timeout=15)
        response.raise_for_status()
        data = _normalizar_resultados(response.json())
        with ruta.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        logger.info(
            "🧭  Geocoding resuelto | ciudad=%s | departamento=%s",
            data.get("ciudad_principal"),
            data.get("departamento"),
        )
        return data
    except Exception as exc:
        logger.warning("No se pudo resolver la ubicación para lat=%.2f lon=%.2f (%s)", lat, lon, exc)
        data = _fallback()
        with ruta.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return data