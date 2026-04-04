# sensor_simulator.py — Sensores IoT virtuales con datos de Open-Meteo
#
# Cada SensorVirtual:
#   1. Toma el valor base real de Open-Meteo para la hora actual.
#   2. Aplica ruido gaussiano calibrado por tipo de sensor.
#   3. Simula deriva lenta del hardware (offset acumulativo).
#   4. Genera anomalías esporádicas para probar las alertas.

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from config import FINCAS, RANGOS_VALIDOS, RUIDO, SENSORES_POR_FINCA
from services.openmeteo_client import (
    co2_para_hora,
    humedad_suelo_desde_raw,
    obtener_datos,
    valor_para_ahora,
)

logger = logging.getLogger(__name__)


# ── Sensor individual ────────────────────────────────────────────────────────

@dataclass
class SensorVirtual:
    """
    Representa un sensor IoT virtual con comportamiento físico realista.
    El valor base proviene de Open-Meteo; el ruido y la deriva simulan
    las imperfecciones del hardware real.
    """
    sensor_id:   str
    finca_id:    str
    finca_info:  dict
    tipo:        str      # temperatura | humedad | co2 | humedad_suelo | radiacion
    datos_om:    dict     # pronóstico horario de Open-Meteo

    # Estado interno mutable del sensor
    _deriva:    float = field(default=0.0, init=False)
    _lecturas:  int   = field(default=0,   init=False)

    PROB_ANOMALIA: float = 0.005   # 0.5 % de probabilidad por lectura

    # ── Lectura principal ────────────────────────────────────────────────────

    def leer(self) -> dict:
        """
        Genera una lectura simulada para el instante actual.
        Devuelve un diccionario listo para ser enviado a Redis.
        """
        ts   = datetime.now(tz=timezone.utc)
        hora = ts.hour + ts.minute / 60

        # 1. Valor base desde Open-Meteo
        base_om = valor_para_ahora(self.datos_om, self.finca_info["altitud_m"])
        valor   = self._valor_base(base_om, hora)

        # 2. Ruido gaussiano del hardware
        valor = self._aplicar_ruido(valor)

        # 3. Deriva lenta del sensor
        valor = self._aplicar_deriva(valor)

        # 4. Clamp a rangos físicos válidos
        valor = self._clamp(valor)

        # 5. Anomalía esporádica (para probar alertas)
        anomalia = False
        if random.random() < self.PROB_ANOMALIA:
            valor    = self._inyectar_anomalia(valor)
            anomalia = True

        self._lecturas += 1

        return {
            "sensor_id":    self.sensor_id,
            "finca_id":     self.finca_id,
            "finca_nombre": self.finca_info["nombre"],
            "tipo":         self.tipo,
            "valor":        round(valor, 2),
            "unidad":       self._unidad(),
            "timestamp":    ts.isoformat(),
            "lat":          self.finca_info["lat"],
            "lon":          self.finca_info["lon"],
            "altitud_m":    self.finca_info["altitud_m"],
            "fuente":       self.datos_om.get("_mode", "desconocido"),
            "anomalia":     anomalia,
        }

    # ── Valor base por tipo ──────────────────────────────────────────────────

    def _valor_base(self, base_om: dict, hora: float) -> float:
        """
        Extrae el valor base del pronóstico de Open-Meteo según el tipo
        de sensor. El CO₂ no viene de Open-Meteo y se calcula aparte.
        """
        if self.tipo == "temperatura":
            return base_om.get("temperatura") or 14.0

        if self.tipo == "humedad":
            return base_om.get("humedad") or 70.0

        if self.tipo == "radiacion":
            return base_om.get("radiacion") or 0.0

        if self.tipo == "humedad_suelo":
            raw    = base_om.get("hum_suelo_raw") or 0.25
            precip = base_om.get("precipitacion") or 0.0
            return humedad_suelo_desde_raw(raw, precip)

        if self.tipo == "co2":
            return co2_para_hora(hora)

        return 0.0

    # ── Transformaciones del hardware ────────────────────────────────────────

    def _aplicar_ruido(self, valor: float) -> float:
        sigma = RUIDO.get(self.tipo, 0.5)
        return valor + np.random.normal(0, sigma)

    def _aplicar_deriva(self, valor: float) -> float:
        """
        Simula el drift lento del sensor: offset que crece gradualmente
        y se mantiene dentro de ±2 unidades para no volverse irreal.
        """
        self._deriva += np.random.normal(0, 0.002)
        self._deriva  = float(np.clip(self._deriva, -2.0, 2.0))
        return valor + self._deriva

    def _clamp(self, valor: float) -> float:
        lo, hi = RANGOS_VALIDOS.get(self.tipo, (-9_999, 9_999))
        return max(lo, min(hi, valor))

    def _inyectar_anomalia(self, valor: float) -> float:
        """Genera un spike fuera del rango normal para probar las alertas."""
        lo, hi  = RANGOS_VALIDOS.get(self.tipo, (0, 1_000))
        rango   = hi - lo
        spike   = random.choice([-1, 1]) * random.uniform(0.15, 0.25) * rango
        return self._clamp(valor + spike)

    def _unidad(self) -> str:
        return {
            "temperatura":   "°C",
            "humedad":       "%",
            "co2":           "ppm",
            "humedad_suelo": "%",
            "radiacion":     "W/m²",
        }.get(self.tipo, "")


# ── Fábrica de sensores ──────────────────────────────────────────────────────

def crear_sensores_finca(finca: dict) -> list[SensorVirtual]:
    """
    Descarga los datos de Open-Meteo para una finca y crea todos los
    sensores virtuales configurados en SENSORES_POR_FINCA.
    """
    logger.info("🌾  Descargando datos para %s (lat=%.2f, lon=%.2f)…",
                finca["nombre"], finca["lat"], finca["lon"])

    datos_om = obtener_datos(finca["lat"], finca["lon"], finca["altitud_m"])
    modo = datos_om.get("_mode", "desconocido")
    logger.info("📡  Modo de datos: %s", modo)

    sensores = []
    for tipo, cantidad in SENSORES_POR_FINCA.items():
        for i in range(cantidad):
            sid = f"{finca['id']}_{tipo}_{i+1:02d}"
            s   = SensorVirtual(
                sensor_id  = sid,
                finca_id   = finca["id"],
                finca_info = finca,
                tipo       = tipo,
                datos_om   = datos_om,
            )
            sensores.append(s)
            logger.debug("🔧  Sensor creado: %s", sid)

    return sensores


def crear_todos_los_sensores() -> list[SensorVirtual]:
    """Crea y devuelve todos los sensores de todas las fincas."""
    todos = []
    for finca in FINCAS:
        todos.extend(crear_sensores_finca(finca))
    logger.info("✅  Total de sensores activos: %d", len(todos))
    return todos
