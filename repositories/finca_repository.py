from __future__ import annotations
from datetime import datetime, timezone
import json
import logging
import uuid
import redis
logger = logging.getLogger(__name__)
class FincaRepository:
    FINCAS_SET_KEY = "fincas:ids"
    def __init__(self, redis_client: redis.Redis):
        self._r = redis_client
    def listar(self) -> list[dict]:
        ids = sorted(self._r.smembers(self.FINCAS_SET_KEY))
        if not ids:
            self._migrar_desde_lecturas_legacy()
            ids = sorted(self._r.smembers(self.FINCAS_SET_KEY))
        fincas: list[dict] = []
        for finca_id in ids:
            finca = self.obtener(finca_id)
            if finca:
                fincas.append(finca)
        return fincas
    def obtener(self, finca_id: str) -> dict | None:
        data = self._r.hgetall(self._key(finca_id))
        if not data:
            return None
        return self._deserialize(data)
    def obtener_ultima_por_tipo(self, finca_id: str) -> dict[str, dict]:
        key = f"finca:{finca_id}:ultima"
        raw = self._r.hgetall(key)
        salida: dict[str, dict] = {}
        for tipo, payload in raw.items():
            try:
                salida[str(tipo)] = json.loads(payload)
            except (TypeError, ValueError):
                continue
        return salida
    def obtener_sensores_estado(self, finca_id: str) -> list[dict]:
        sensores: list[dict] = []
        for key in self._r.scan_iter(match=f"sensor:{finca_id}_*:estado"):
            data = self._r.hgetall(key)
            if not data:
                continue
            sensores.append(self._normalizar_lectura(data))
        sensores.sort(key=lambda s: s.get("sensor_id", ""))
        return sensores
    def obtener_alertas_recientes(self, finca_id: str, limite: int = 10) -> list[dict]:
        key = f"alertas:{finca_id}"
        raw = self._r.lrange(key, 0, max(0, limite - 1))
        salida: list[dict] = []
        for payload in raw:
            try:
                salida.append(json.loads(payload))
            except (TypeError, ValueError):
                continue
        return salida
    def crear(self, nombre: str, lat: float, lon: float, altitud_m: float) -> dict:
        finca_id = f"finca_{uuid.uuid4().hex[:10]}"
        ahora = datetime.now(tz=timezone.utc).isoformat()
        finca = {
            "id": finca_id,
            "nombre": nombre,
            "lat": lat,
            "lon": lon,
            "altitud_m": altitud_m,
            "created_at": ahora,
            "updated_at": ahora,
        }
        self._guardar(finca)
        return finca
    def actualizar(
        self,
        finca_id: str,
        *,
        nombre: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        altitud_m: float | None = None,
    ) -> dict | None:
        actual = self.obtener(finca_id)
        if not actual:
            return None
        if nombre is not None:
            actual["nombre"] = nombre
        if lat is not None:
            actual["lat"] = lat
        if lon is not None:
            actual["lon"] = lon
        if altitud_m is not None:
            actual["altitud_m"] = altitud_m
        actual["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        self._guardar(actual)
        return actual
    def eliminar(self, finca_id: str) -> bool:
        pipe = self._r.pipeline()
        pipe.delete(self._key(finca_id))
        pipe.srem(self.FINCAS_SET_KEY, finca_id)
        result = pipe.execute()
        deleted = bool(result[0])
        if deleted:
            self._r.delete(f"finca:{finca_id}:ultima")
            self._r.delete(f"alertas:{finca_id}")
            for key in self._r.scan_iter(match=f"sensor:{finca_id}_*:*"):
                self._r.delete(key)
        return deleted
    def _guardar(self, finca: dict) -> None:
        key = self._key(finca["id"])
        pipe = self._r.pipeline()
        pipe.hset(key, mapping=self._serialize(finca))
        pipe.sadd(self.FINCAS_SET_KEY, finca["id"])
        pipe.execute()
    def _migrar_desde_lecturas_legacy(self) -> None:
        migradas = 0
        ahora = datetime.now(tz=timezone.utc).isoformat()
        for raw_key in self._r.scan_iter(match="finca:*:ultima"):
            key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
            partes = key.split(":")
            if len(partes) != 3:
                continue
            finca_id = partes[1]
            if self._r.exists(self._key(finca_id)):
                self._r.sadd(self.FINCAS_SET_KEY, finca_id)
                continue
            ultima_por_tipo = self._r.hgetall(key)
            if not ultima_por_tipo:
                continue
            muestra = None
            for payload in ultima_por_tipo.values():
                try:
                    muestra = json.loads(payload)
                    break
                except (TypeError, ValueError):
                    continue
            if not muestra:
                continue
            try:
                finca = {
                    "id": finca_id,
                    "nombre": str(muestra["finca_nombre"]),
                    "lat": float(muestra["lat"]),
                    "lon": float(muestra["lon"]),
                    "altitud_m": float(muestra["altitud_m"]),
                    "created_at": ahora,
                    "updated_at": ahora,
                }
            except (KeyError, TypeError, ValueError):
                continue
            self._guardar(finca)
            migradas += 1
        if migradas:
            logger.info("Fincas migradas desde claves legacy: %d", migradas)
    @staticmethod
    def _key(finca_id: str) -> str:
        return f"finca:{finca_id}:meta"
    @staticmethod
    def _serialize(finca: dict) -> dict[str, str]:
        return {
            "id": str(finca["id"]),
            "nombre": str(finca["nombre"]),
            "lat": str(finca["lat"]),
            "lon": str(finca["lon"]),
            "altitud_m": str(finca["altitud_m"]),
            "created_at": str(finca["created_at"]),
            "updated_at": str(finca["updated_at"]),
        }
    @staticmethod
    def _deserialize(data: dict[str, str]) -> dict:
        return {
            "id": data["id"],
            "nombre": data["nombre"],
            "lat": float(data["lat"]),
            "lon": float(data["lon"]),
            "altitud_m": float(data["altitud_m"]),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
        }
    @staticmethod
    def _normalizar_lectura(data: dict[str, str]) -> dict:
        lectura = dict(data)
        for campo in ("valor", "lat", "lon", "altitud_m"):
            if campo in lectura:
                try:
                    lectura[campo] = float(lectura[campo])
                except (TypeError, ValueError):
                    pass
        if "anomalia" in lectura:
            lectura["anomalia"] = str(lectura["anomalia"]).lower() == "true"
        return lectura
