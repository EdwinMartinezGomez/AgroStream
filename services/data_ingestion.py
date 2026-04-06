import json
import logging
import os
import time
from collections import defaultdict
import redis
from services.alert_engine import evaluar_lectura
from config import (
    RANGOS_VALIDOS, REDIS_DB, REDIS_HOST, REDIS_PORT, REDIS_TTL,
)
logger = logging.getLogger(__name__)

LEGACY_REDIS_HOST = "redis-16643.c84.us-east-1-2.ec2.cloud.redislabs.com"
LEGACY_REDIS_PORT = 16643
LEGACY_REDIS_USER = "default"
LEGACY_REDIS_PASSWORD = "ld3UCP9yKFczLp8UdkrzZGqA4d7N9HjI"


def _crear_cliente_redis(
    host: str,
    port: int,
    db: int,
    username: str | None,
    password: str | None,
) -> redis.Redis:
    return redis.Redis(
        host=host,
        port=port,
        db=db,
        decode_responses=True,
        username=username,
        password=password,
    )


def conectar_redis() -> redis.Redis:
    redis_user = os.getenv("REDIS_USER")
    redis_password = os.getenv("REDIS_PASSWORD")

    cliente = _crear_cliente_redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        username=redis_user,
        password=redis_password,
    )
    try:
        cliente.ping()
        logger.info("✅  Redis conectado en %s:%d (db=%d)",
                    REDIS_HOST, REDIS_PORT, REDIS_DB)
        return cliente
    except redis.ConnectionError as exc:
        logger.warning("No se pudo conectar a Redis configurado (%s:%d): %s",
                       REDIS_HOST, REDIS_PORT, exc)

    cliente_legacy = _crear_cliente_redis(
        host=LEGACY_REDIS_HOST,
        port=LEGACY_REDIS_PORT,
        db=REDIS_DB,
        username=LEGACY_REDIS_USER,
        password=LEGACY_REDIS_PASSWORD,
    )
    try:
        cliente_legacy.ping()
        logger.warning(
            "⚠️  Usando Redis legacy remoto en %s:%d porque el Redis configurado no está disponible.",
            LEGACY_REDIS_HOST,
            LEGACY_REDIS_PORT,
        )
        return cliente_legacy
    except redis.ConnectionError as exc:
        raise RuntimeError(
            f"No se pudo conectar a Redis en {REDIS_HOST}:{REDIS_PORT} ni al fallback legacy {LEGACY_REDIS_HOST}:{LEGACY_REDIS_PORT}. "
            "Si quieres usar local: docker run -d -p 6379:6379 redis:7"
        ) from exc
class ErrorValidacion(ValueError):
    pass
CAMPOS_REQUERIDOS = ["sensor_id", "finca_id", "tipo", "valor", "unidad", "timestamp"]
def validar_lectura(lectura: dict) -> None:
    for campo in CAMPOS_REQUERIDOS:
        if campo not in lectura:
            raise ErrorValidacion(f"Campo faltante: '{campo}'")
    valor = lectura["valor"]
    if not isinstance(valor, (int, float)):
        raise ErrorValidacion(
            f"El valor debe ser numérico, se recibió {type(valor).__name__}"
        )
    tipo = lectura["tipo"]
    if tipo in RANGOS_VALIDOS:
        lo, hi = RANGOS_VALIDOS[tipo]
        if not (lo <= valor <= hi):
            raise ErrorValidacion(
                f"Valor fuera de rango para '{tipo}': "
                f"{valor} (esperado [{lo}, {hi}])"
            )
class ServicioIngesta:
    def __init__(self, cliente_redis: redis.Redis | None = None):
        self.r          = cliente_redis or conectar_redis()
        self._contadores: dict[str, int] = defaultdict(int)
        self._errores   = 0
        self._t_inicio  = time.time()
    def procesar(self, lectura: dict) -> list[dict]:
        try:
            validar_lectura(lectura)
        except ErrorValidacion as exc:
            self._errores += 1
            logger.warning("⚠️  Lectura inválida [%s]: %s",
                           lectura.get("sensor_id", "?"), exc)
            return []
        sid = lectura["sensor_id"]
        fid = lectura["finca_id"]
        pipe = self.r.pipeline()
        clave_estado = f"sensor:{sid}:estado"
        pipe.hset(clave_estado, mapping={k: str(v) for k, v in lectura.items()})
        pipe.expire(clave_estado, REDIS_TTL)
        clave_finca = f"finca:{fid}:ultima"
        pipe.hset(clave_finca, lectura["tipo"], json.dumps(lectura))
        pipe.expire(clave_finca, REDIS_TTL)
        clave_stream = f"sensor:{sid}:stream"
        pipe.lpush(clave_stream, json.dumps(lectura))
        pipe.ltrim(clave_stream, 0, 499)
        pipe.expire(clave_stream, REDIS_TTL)
        pipe.execute()
        self._contadores[lectura["tipo"]] += 1
        alertas = evaluar_lectura(lectura)
        if alertas:
            self._persistir_alertas(alertas, fid)
        return alertas
    def _persistir_alertas(self, alertas: list[dict], finca_id: str) -> None:
        pipe = self.r.pipeline()
        for alerta in alertas:
            payload = json.dumps(alerta, ensure_ascii=False)
            pipe.lpush("alertas:global", payload)
            pipe.ltrim("alertas:global", 0, 999)
            clave_finca = f"alertas:{finca_id}"
            pipe.lpush(clave_finca, payload)
            pipe.ltrim(clave_finca, 0, 199)
            pipe.expire(clave_finca, REDIS_TTL)
        pipe.execute()
    def imprimir_metricas(self) -> None:
        elapsed = time.time() - self._t_inicio
        total   = sum(self._contadores.values())
        tps     = total / elapsed if elapsed > 0 else 0.0
        logger.info("📊  Lecturas: %d | Errores: %d | TPS promedio: %.1f",
                    total, self._errores, tps)
        for tipo, cnt in sorted(self._contadores.items()):
            logger.info("     %-16s %d lecturas", tipo, cnt)
