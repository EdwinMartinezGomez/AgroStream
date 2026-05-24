from __future__ import annotations

import logging
import random
import threading
import time

from flask_socketio import SocketIO

from config import INTERVALO_LECTURA_S, PROB_ALERTA_SIMULADA
from services.data_ingestion import ServicioIngesta
from services.openmeteo_client import obtener_datos
from simulation.sensor_simulator import SensorVirtual, crear_sensores_finca
from services.finca_service import FincaService

logger = logging.getLogger(__name__)


class SimulationManager:
    def __init__(
        self,
        finca_service: FincaService,
        servicio_ingesta: ServicioIngesta,
        socketio: SocketIO | None = None,
        reload_interval_s: int = 5,
        refresh_openmeteo_s: int = 3600,
    ):
        self._finca_service = finca_service
        self._ingesta = servicio_ingesta
        self._socketio = socketio
        self._reload_interval_s = reload_interval_s
        self._refresh_openmeteo_s = refresh_openmeteo_s
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._sensores: list[SensorVirtual] = []
        self._fingerprint: tuple | None = None
        self._ultimo_refresh = time.monotonic()
        self._sin_fincas_reportado = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Simulacion en background iniciada.")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("Simulacion en background detenida.")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            fincas = self._finca_service.listar_fincas()
            fingerprint = self._crear_fingerprint(fincas)
            if fingerprint != self._fingerprint:
                self._reconstruir_sensores(fincas)
                self._fingerprint = fingerprint
            if not self._sensores:
                if not self._sin_fincas_reportado:
                    logger.info("No hay fincas registradas. Simulacion en pausa.")
                    self._emit_state()
                    self._sin_fincas_reportado = True
                self._stop_event.wait(self._reload_interval_s)
                continue
            self._sin_fincas_reportado = False
            self._ciclo_lecturas()
            if time.monotonic() - self._ultimo_refresh >= self._refresh_openmeteo_s:
                self._refrescar_openmeteo()
                self._ultimo_refresh = time.monotonic()
            self._stop_event.wait(INTERVALO_LECTURA_S)
    def _ciclo_lecturas(self) -> None:
        for sensor in self._sensores:
            if self._stop_event.is_set():
                return
            try:
                lectura = sensor.leer()
                alertas = self._ingesta.procesar(lectura)
                alertas_simuladas = self._generar_alerta_simulada(sensor, lectura)
                if alertas_simuladas:
                    self._ingesta.persistir_alertas(alertas_simuladas, sensor.finca_id)
                    alertas.extend(alertas_simuladas)
                self._emit_reading(sensor.finca_id, lectura)
                if alertas:
                    self._emit_alerts(sensor.finca_id, alertas)
            except Exception as exc:
                logger.error("Error en sensor %s: %s", sensor.sensor_id, exc)

    def _reconstruir_sensores(self, fincas: list[dict]) -> None:
        sensores: list[SensorVirtual] = []
        for finca in fincas:
            try:
                sensores.extend(crear_sensores_finca(finca))
            except Exception as exc:
                logger.error("No se pudo crear sensores para finca %s: %s", finca.get("id"), exc)
        self._sensores = sensores
        logger.info("Sensores activos: %d", len(self._sensores))
        self._emit_state()

    def _refrescar_openmeteo(self) -> None:
        logger.info("Renovando datos Open-Meteo para fincas activas...")
        por_finca: dict[str, list[SensorVirtual]] = {}
        for sensor in self._sensores:
            por_finca.setdefault(sensor.finca_id, []).append(sensor)
        for sensores in por_finca.values():
            sensor_ref = sensores[0]
            finca = sensor_ref.finca_info
            try:
                nuevos_datos = obtener_datos(finca["lat"], finca["lon"], finca["altitud_m"])
                for sensor in sensores:
                    sensor.datos_om = nuevos_datos
            except Exception as exc:
                logger.warning("No se pudo renovar Open-Meteo para finca %s: %s", finca["id"], exc)

    @staticmethod
    def _crear_fingerprint(fincas: list[dict]) -> tuple:
        return tuple(
            sorted(
                (
                    finca["id"],
                    finca["nombre"],
                    finca["lat"],
                    finca["lon"],
                    finca["altitud_m"],
                    finca.get("updated_at", ""),
                )
                for finca in fincas
            )
        )

    def estado(self) -> dict:
        fincas = self._finca_service.listar_fincas()
        return {
            "running": not self._stop_event.is_set(),
            "active_fincas": len(fincas),
            "active_sensors": len(self._sensores),
            "waiting_for_fincas": not bool(self._sensores),
            "last_refresh_epoch": self._ultimo_refresh,
        }

    def _emit_state(self) -> None:
        if self._socketio is not None:
            self._socketio.emit("simulation_state", self.estado())

    def _emit_reading(self, finca_id: str, lectura: dict) -> None:
        if self._socketio is not None:
            self._socketio.emit("sensor_reading", lectura, room=finca_id)
            self._socketio.emit("sensor_reading_global", lectura)

    def _emit_alerts(self, finca_id: str, alertas: list[dict]) -> None:
        if self._socketio is not None:
            payload = {"finca_id": finca_id, "alertas": alertas}
            self._socketio.emit("sensor_alerts", payload, room=finca_id)
            self._socketio.emit("sensor_alerts_global", payload)

    def _generar_alerta_simulada(self, sensor: SensorVirtual, lectura: dict) -> list[dict]:
        if random.random() >= PROB_ALERTA_SIMULADA:
            return []

        nivel = random.choice(["info", "warning", "critico"])
        mensajes = {
            "info": "Lectura simulada de verificación del sistema.",
            "warning": "Variación simulada detectada para validar la reacción del tablero.",
            "critico": "Alerta simulada de prueba para validar notificaciones críticas.",
        }
        alerta = {
            "alerta_id": f"SIM_{sensor.sensor_id}_{int(time.time())}",
            "sensor_id": sensor.sensor_id,
            "finca_id": sensor.finca_id,
            "finca_nombre": sensor.finca_info["nombre"],
            "tipo_sensor": sensor.tipo,
            "nivel": nivel,
            "mensaje": mensajes[nivel],
            "valor": lectura["valor"],
            "unidad": lectura["unidad"],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        logger.warning("🚨  [SIMULADA/%s] %s — %s", nivel.upper(), sensor.finca_info["nombre"], alerta["mensaje"])
        return [alerta]
