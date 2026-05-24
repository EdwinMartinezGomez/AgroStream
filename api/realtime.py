from __future__ import annotations

from flask_socketio import SocketIO, emit, join_room, leave_room

from services.finca_service import FincaService, FincaNotFoundError
from simulation.simulation_manager import SimulationManager


def register_socket_events(
    socketio: SocketIO,
    finca_service: FincaService,
    simulation_manager: SimulationManager,
) -> None:
    @socketio.on("connect")
    def handle_connect():
        emit("server_ready", {"message": "AgroStream conectado"})
        emit("fincas_snapshot", {"fincas": finca_service.listar_fincas()})
        emit("simulation_state", simulation_manager.estado())

    @socketio.on("request_fincas")
    def handle_request_fincas():
        emit("fincas_snapshot", {"fincas": finca_service.listar_fincas()})

    @socketio.on("request_finca")
    def handle_request_finca(data):
        finca_id = (data or {}).get("finca_id")
        if not finca_id:
            emit("error", {"message": "finca_id es obligatorio"})
            return
        try:
            emit("finca_snapshot", {"finca": finca_service.obtener_finca(finca_id)})
        except FincaNotFoundError as exc:
            emit("error", {"message": str(exc)})

    @socketio.on("request_simulation_state")
    def handle_request_simulation_state():
        emit("simulation_state", simulation_manager.estado())

    @socketio.on("subscribe_finca")
    def handle_subscribe_finca(data):
        finca_id = (data or {}).get("finca_id")
        if not finca_id:
            emit("error", {"message": "finca_id es obligatorio"})
            return
        join_room(finca_id)
        try:
            emit("finca_snapshot", {"finca": finca_service.obtener_finca(finca_id)})
        except FincaNotFoundError as exc:
            emit("error", {"message": str(exc)})

    @socketio.on("unsubscribe_finca")
    def handle_unsubscribe_finca(data):
        finca_id = (data or {}).get("finca_id")
        if finca_id:
            leave_room(finca_id)


def broadcast_fincas_snapshot(socketio: SocketIO, finca_service: FincaService) -> None:
    socketio.emit("fincas_snapshot", {"fincas": finca_service.listar_fincas()})


def broadcast_finca_snapshot(socketio: SocketIO, finca_service: FincaService, finca_id: str) -> None:
    try:
        socketio.emit("finca_snapshot", {"finca": finca_service.obtener_finca(finca_id)})
    except FincaNotFoundError:
        return


def broadcast_finca_deleted(socketio: SocketIO, finca_id: str) -> None:
    socketio.emit("finca_deleted", {"finca_id": finca_id})
