from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from api.realtime import (
    broadcast_finca_deleted,
    broadcast_finca_snapshot,
    broadcast_fincas_snapshot,
)
from services.finca_service import (
    FincaNotFoundError,
    FincaService,
    FincaValidationError,
)


def create_fincas_blueprint(finca_service: FincaService) -> Blueprint:
    bp = Blueprint("fincas", __name__, url_prefix="/api/fincas")

    @bp.get("")
    def listar_fincas():
        return jsonify(finca_service.listar_fincas())

    @bp.get("/<finca_id>")
    def obtener_finca(finca_id: str):
        try:
            return jsonify(finca_service.obtener_finca(finca_id))
        except FincaNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @bp.post("")
    def crear_finca():
        payload = request.get_json(silent=True) or {}
        try:
            finca = finca_service.crear_finca(payload)
            socketio = current_app.config["socketio"]
            broadcast_fincas_snapshot(socketio, finca_service)
            broadcast_finca_snapshot(socketio, finca_service, finca["id"])
            return jsonify(finca), 201
        except FincaValidationError as exc:
            return jsonify({"error": str(exc)}), 400

    @bp.put("/<finca_id>")
    @bp.patch("/<finca_id>")
    def actualizar_finca(finca_id: str):
        payload = request.get_json(silent=True) or {}
        try:
            finca = finca_service.actualizar_finca(finca_id, payload)
            socketio = current_app.config["socketio"]
            broadcast_fincas_snapshot(socketio, finca_service)
            broadcast_finca_snapshot(socketio, finca_service, finca_id)
            return jsonify(finca)
        except FincaValidationError as exc:
            return jsonify({"error": str(exc)}), 400
        except FincaNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    @bp.delete("/<finca_id>")
    def eliminar_finca(finca_id: str):
        try:
            finca_service.eliminar_finca(finca_id)
            socketio = current_app.config["socketio"]
            broadcast_fincas_snapshot(socketio, finca_service)
            broadcast_finca_deleted(socketio, finca_id)
            return "", 204
        except FincaNotFoundError as exc:
            return jsonify({"error": str(exc)}), 404

    return bp
