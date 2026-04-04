from __future__ import annotations

import atexit
import logging
import os
import sys

from flask import Flask, jsonify

from api.routes.fincas import create_fincas_blueprint
from config import FLASK_DEBUG, FLASK_HOST, FLASK_PORT
from services.data_ingestion import ServicioIngesta, conectar_redis
from repositories.finca_repository import FincaRepository
from services.finca_service import FincaService
from simulation.simulation_manager import SimulationManager


def _configurar_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/backend.log", encoding="utf-8"),
        ],
    )


def create_app() -> Flask:
    _configurar_logging()

    app = Flask(__name__)

    redis_client = conectar_redis()
    finca_repo = FincaRepository(redis_client)
    finca_service = FincaService(finca_repo)
    ingesta = ServicioIngesta(redis_client)

    simulation_manager = SimulationManager(
        finca_service=finca_service,
        servicio_ingesta=ingesta,
    )
    simulation_manager.start()
    atexit.register(simulation_manager.stop)

    app.config["finca_service"] = finca_service
    app.config["simulation_manager"] = simulation_manager
    app.config["redis_client"] = redis_client

    app.register_blueprint(create_fincas_blueprint(finca_service))

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "service": "agrostream-backend",
                "host": FLASK_HOST,
                "port": FLASK_PORT,
                "debug": FLASK_DEBUG,
            }
        )

    return app
