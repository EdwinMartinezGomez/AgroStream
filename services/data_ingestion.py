# data_ingestion.py — Validación, procesamiento e ingesta en Redis
#
# Responsabilidades:
#   1. Validar estructura y rangos de cada lectura.
#   2. Persistir en Redis usando un pipeline para minimizar round-trips.
#   3. Evaluar alertas y persistirlas en sus listas correspondientes.
#   4. Registrar métricas de throughput cada N segundos.

import json
import logging
import time
from collections import defaultdict

import redis

from services.alert_engine import evaluar_lectura
from config import (
    RANGOS_VALIDOS, REDIS_DB, REDIS_HOST, REDIS_PORT, REDIS_TTL,
)

logger = logging.getLogger(__name__)


# ── Conexión ─────────────────────────────────────────────────────────────────

def conectar_redis() -> redis.Redis:
    """Crea y verifica la conexión a Redis. Lanza RuntimeError si falla."""
    cliente = redis.Redis(
    host='redis-16643.c84.us-east-1-2.ec2.cloud.redislabs.com',
    port=16643,
    decode_responses=True,
    username="default",
    password="ld3UCP9yKFczLp8UdkrzZGqA4d7N9HjI",
    )   
    try:
        cliente.ping()
        logger.info("✅  Redis conectado en %s:%d (db=%d)",
                    REDIS_HOST, REDIS_PORT, REDIS_DB)
    except redis.ConnectionError as exc:
        raise RuntimeError(
            f"No se pudo conectar a Redis en {REDIS_HOST}:{REDIS_PORT}. "
            "¿Está Redis corriendo? Ejecuta: docker run -d -p 6379:6379 redis:7"
        ) from exc
    return cliente


# ── Validación ────────────────────────────────────────────────────────────────

class ErrorValidacion(ValueError):
    pass


CAMPOS_REQUERIDOS = ["sensor_id", "finca_id", "tipo", "valor", "unidad", "timestamp"]


def validar_lectura(lectura: dict) -> None:
    """
    Verifica que la lectura tenga todos los campos requeridos y que
    el valor esté dentro del rango físico válido para su tipo.
    Lanza ErrorValidacion si alguna condición falla.
    """
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


# ── Servicio de ingesta ───────────────────────────────────────────────────────

class ServicioIngesta:
    """
    Gestiona la ingesta completa de lecturas:
      - valida → escribe en Redis → evalúa alertas → persiste alertas.
    """

    def __init__(self, cliente_redis: redis.Redis | None = None):
        self.r          = cliente_redis or conectar_redis()
        self._contadores: dict[str, int] = defaultdict(int)
        self._errores   = 0
        self._t_inicio  = time.time()

    # ── Ingesta principal ─────────────────────────────────────────────────────

    def procesar(self, lectura: dict) -> list[dict]:
        """
        Procesa una lectura end-to-end.
        Devuelve la lista de alertas generadas (puede ser vacía).
        """
        # 1. Validación
        try:
            validar_lectura(lectura)
        except ErrorValidacion as exc:
            self._errores += 1
            logger.warning("⚠️  Lectura inválida [%s]: %s",
                           lectura.get("sensor_id", "?"), exc)
            return []

        sid = lectura["sensor_id"]
        fid = lectura["finca_id"]

        # 2. Persistencia en Redis (pipeline = una sola llamada de red)
        pipe = self.r.pipeline()

        # Patrón 1: estado actual del sensor (Hash)
        clave_estado = f"sensor:{sid}:estado"
        pipe.hset(clave_estado, mapping={k: str(v) for k, v in lectura.items()})
        pipe.expire(clave_estado, REDIS_TTL)

        # Patrón 3: resumen por finca (Hash de JSONs por tipo)
        clave_finca = f"finca:{fid}:ultima"
        pipe.hset(clave_finca, lectura["tipo"], json.dumps(lectura))
        pipe.expire(clave_finca, REDIS_TTL)

        # Patrón 2: historial reciente del sensor (List, máx 500)
        clave_stream = f"sensor:{sid}:stream"
        pipe.lpush(clave_stream, json.dumps(lectura))
        pipe.ltrim(clave_stream, 0, 499)
        pipe.expire(clave_stream, REDIS_TTL)

        pipe.execute()
        self._contadores[lectura["tipo"]] += 1

        # 3. Motor de alertas
        alertas = evaluar_lectura(lectura)
        if alertas:
            self._persistir_alertas(alertas, fid)

        return alertas

    # ── Persistencia de alertas ───────────────────────────────────────────────

    def _persistir_alertas(self, alertas: list[dict], finca_id: str) -> None:
        """
        Guarda las alertas en:
          - alertas:global     (últimas 1 000, sin TTL)
          - alertas:{finca_id} (últimas 200, TTL 24 h)
        """
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

    # ── Métricas ──────────────────────────────────────────────────────────────

    def imprimir_metricas(self) -> None:
        elapsed = time.time() - self._t_inicio
        total   = sum(self._contadores.values())
        tps     = total / elapsed if elapsed > 0 else 0.0
        logger.info("📊  Lecturas: %d | Errores: %d | TPS promedio: %.1f",
                    total, self._errores, tps)
        for tipo, cnt in sorted(self._contadores.items()):
            logger.info("     %-16s %d lecturas", tipo, cnt)
