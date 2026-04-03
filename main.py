# main.py — Orquestador principal del simulador
#
# Lanza todos los sensores en paralelo con asyncio.
# Cada sensor emite una lectura cada INTERVALO_LECTURA_S segundos.
# Las métricas se imprimen cada 30 segundos.
# Ctrl+C cierra todo limpiamente.

import asyncio
import logging
import os
import random
import signal
import sys
from datetime import datetime, timezone

from config import INTERVALO_LECTURA_S
from data_ingestion import ServicioIngesta, conectar_redis
from sensor_simulator import SensorVirtual, crear_todos_los_sensores

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/simulador.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ── Flag de parada ────────────────────────────────────────────────────────────
_detener = asyncio.Event()


def _handle_signal(*_):
    logger.info("⛔  Señal recibida — deteniendo simulador…")
    _detener.set()


# ── Tarea por sensor ──────────────────────────────────────────────────────────

async def tarea_sensor(sensor: SensorVirtual, servicio: ServicioIngesta) -> None:
    """
    Corrutina que genera y envía lecturas periódicamente.
    Añade un jitter inicial aleatorio para evitar que todos los sensores
    emitan exactamente al mismo instante (comportamiento IoT real).
    """
    jitter = random.uniform(0, INTERVALO_LECTURA_S * 0.8)
    await asyncio.sleep(jitter)

    while not _detener.is_set():
        try:
            lectura = sensor.leer()
            alertas = servicio.procesar(lectura)

            # Log detallado en modo DEBUG
            extra = f"  ⚠️  {alertas[0]['mensaje']}" if alertas else ""
            logger.debug(
                "[%s] %s → %s: %.2f %s%s",
                sensor.finca_info["nombre"],
                sensor.sensor_id,
                sensor.tipo,
                lectura["valor"],
                lectura["unidad"],
                extra,
            )

        except Exception as exc:
            logger.error("❌  Error en %s: %s", sensor.sensor_id, exc)

        # Esperar hasta el próximo ciclo (o parar si se recibe la señal)
        try:
            await asyncio.wait_for(
                asyncio.shield(_detener.wait()),
                timeout=INTERVALO_LECTURA_S,
            )
        except asyncio.TimeoutError:
            pass   # normal: continuar con el siguiente ciclo


# ── Tarea de métricas ─────────────────────────────────────────────────────────

async def tarea_metricas(servicio: ServicioIngesta, intervalo: int = 30) -> None:
    """Imprime estadísticas de throughput cada `intervalo` segundos."""
    while not _detener.is_set():
        try:
            await asyncio.wait_for(
                asyncio.shield(_detener.wait()),
                timeout=intervalo,
            )
        except asyncio.TimeoutError:
            servicio.imprimir_metricas()


# ── Tarea de renovación de datos Open-Meteo ───────────────────────────────────

async def tarea_renovacion_om(sensores: list[SensorVirtual], intervalo: int = 3_600) -> None:
    """
    Renueva los datos de Open-Meteo cada hora para que el simulador
    use siempre el pronóstico más reciente del día.
    """
    from openmeteo_client import obtener_datos
    while not _detener.is_set():
        try:
            await asyncio.wait_for(
                asyncio.shield(_detener.wait()),
                timeout=intervalo,
            )
        except asyncio.TimeoutError:
            logger.info("🔄  Renovando datos Open-Meteo…")
            fincas_vistas = set()
            for sensor in sensores:
                fid = sensor.finca_id
                if fid not in fincas_vistas:
                    fincas_vistas.add(fid)
                    nuevos = obtener_datos(
                        sensor.finca_info["lat"],
                        sensor.finca_info["lon"],
                        sensor.finca_info["altitud_m"],
                    )
                    sensor.datos_om = nuevos
                    for s in sensores:
                        if s.finca_id == fid:
                            s.datos_om = nuevos
            logger.info("✅  Datos renovados para %d finca(s).", len(fincas_vistas))


# ── Punto de entrada ──────────────────────────────────────────────────────────

async def main() -> None:
    os.makedirs("cache/openmeteo", exist_ok=True)

    logger.info("═" * 58)
    logger.info("  🌱  Sistema de Monitoreo Agrícola — Simulador IoT")
    logger.info("═" * 58)

    # Señales de sistema operativo
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_signal)

    # Conexión a Redis
    redis_client = conectar_redis()
    servicio     = ServicioIngesta(redis_client)

    # Crear sensores (descarga Open-Meteo)
    logger.info("⏳  Inicializando sensores y descargando datos Open-Meteo…")
    sensores = crear_todos_los_sensores()

    logger.info("🚀  Iniciando simulación con %d sensores concurrentes", len(sensores))
    logger.info("⏱️   Intervalo de lectura: %d s | Ctrl+C para detener",
                INTERVALO_LECTURA_S)

    # Lanzar todas las corrutinas en paralelo
    tareas = [asyncio.create_task(tarea_sensor(s, servicio)) for s in sensores]
    tareas.append(asyncio.create_task(tarea_metricas(servicio)))
    tareas.append(asyncio.create_task(tarea_renovacion_om(sensores)))

    # Esperar hasta que llegue la señal de parada
    await _detener.wait()

    # Cancelar todas las tareas
    for t in tareas:
        t.cancel()
    await asyncio.gather(*tareas, return_exceptions=True)

    servicio.imprimir_metricas()
    redis_client.close()
    logger.info("👋  Simulador detenido correctamente.")


if __name__ == "__main__":
    asyncio.run(main())
