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
@dataclass
class SensorVirtual:
    sensor_id:   str
    finca_id:    str
    finca_info:  dict
    tipo:        str
    datos_om:    dict
    _deriva:    float = field(default=0.0, init=False)
    _lecturas:  int   = field(default=0,   init=False)
    PROB_ANOMALIA: float = 0.005
    def leer(self) -> dict:
        ts   = datetime.now(tz=timezone.utc)
        hora = ts.hour + ts.minute / 60
        base_om = valor_para_ahora(self.datos_om, self.finca_info["altitud_m"])
        valor   = self._valor_base(base_om, hora)
        valor = self._aplicar_ruido(valor)
        valor = self._aplicar_deriva(valor)
        valor = self._clamp(valor)
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
    def _valor_base(self, base_om: dict, hora: float) -> float:
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
    def _aplicar_ruido(self, valor: float) -> float:
        sigma = RUIDO.get(self.tipo, 0.5)
        return valor + np.random.normal(0, sigma)
    def _aplicar_deriva(self, valor: float) -> float:
        self._deriva += np.random.normal(0, 0.002)
        self._deriva  = float(np.clip(self._deriva, -2.0, 2.0))
        return valor + self._deriva
    def _clamp(self, valor: float) -> float:
        lo, hi = RANGOS_VALIDOS.get(self.tipo, (-9_999, 9_999))
        return max(lo, min(hi, valor))
    def _inyectar_anomalia(self, valor: float) -> float:
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
def crear_sensores_finca(finca: dict) -> list[SensorVirtual]:
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
    todos = []
    for finca in FINCAS:
        todos.extend(crear_sensores_finca(finca))
    logger.info("✅  Total de sensores activos: %d", len(todos))
    return todos
