from __future__ import annotations

from repositories.finca_repository import FincaRepository


class FincaValidationError(ValueError):
    pass


class FincaNotFoundError(LookupError):
    pass


class FincaService:
    def __init__(self, repository: FincaRepository):
        self._repo = repository

    def listar_fincas(self) -> list[dict]:
        return [self._enriquecer_finca(f) for f in self._repo.listar()]

    def obtener_finca(self, finca_id: str) -> dict:
        finca = self._repo.obtener(finca_id)
        if not finca:
            raise FincaNotFoundError(f"No existe la finca '{finca_id}'.")
        return self._enriquecer_finca(finca)

    def crear_finca(self, payload: dict) -> dict:
        nombre, lat, lon, altitud_m = self._validar_payload_creacion(payload)
        finca = self._repo.crear(nombre=nombre, lat=lat, lon=lon, altitud_m=altitud_m)
        return self._enriquecer_finca(finca)

    def actualizar_finca(self, finca_id: str, payload: dict) -> dict:
        actual = self._repo.obtener(finca_id)
        if not actual:
            raise FincaNotFoundError(f"No existe la finca '{finca_id}'.")

        nombre, lat, lon, altitud_m = self._validar_payload_actualizacion(payload)
        lat_valid = lat if lat is not None else actual["lat"]
        lon_valid = lon if lon is not None else actual["lon"]
        self._validar_rangos_geograficos(lat_valid, lon_valid)

        updated = self._repo.actualizar(
            finca_id,
            nombre=nombre,
            lat=lat,
            lon=lon,
            altitud_m=altitud_m,
        )
        if not updated:
            raise FincaNotFoundError(f"No existe la finca '{finca_id}'.")
        return self._enriquecer_finca(updated)

    def eliminar_finca(self, finca_id: str) -> None:
        if not self._repo.eliminar(finca_id):
            raise FincaNotFoundError(f"No existe la finca '{finca_id}'.")

    def _validar_payload_creacion(self, payload: dict) -> tuple[str, float, float, float]:
        if not isinstance(payload, dict):
            raise FincaValidationError("El cuerpo debe ser un JSON valido.")

        nombre = payload.get("nombre")
        ubicacion = payload.get("ubicacion")
        if not nombre or not isinstance(nombre, str) or not nombre.strip():
            raise FincaValidationError("'nombre' es obligatorio y debe ser string.")
        if not isinstance(ubicacion, dict):
            raise FincaValidationError("'ubicacion' es obligatoria y debe ser objeto.")

        lat = self._to_float(ubicacion.get("lat"), "ubicacion.lat")
        lon = self._to_float(ubicacion.get("lon"), "ubicacion.lon")
        altitud_m = self._to_float(ubicacion.get("altitud_m"), "ubicacion.altitud_m")
        self._validar_rangos_geograficos(lat, lon)
        return nombre.strip(), lat, lon, altitud_m

    def _enriquecer_finca(self, finca: dict) -> dict:
        finca_id = finca["id"]
        sensores = self._repo.obtener_sensores_estado(finca_id)
        return {
            **finca,
            "lecturas": {
                "ultima_por_tipo": self._repo.obtener_ultima_por_tipo(finca_id),
                "sensores": sensores,
                "total_sensores": len(sensores),
            },
            "alertas_recientes": self._repo.obtener_alertas_recientes(finca_id, limite=10),
        }

    def _validar_payload_actualizacion(
        self, payload: dict
    ) -> tuple[str | None, float | None, float | None, float | None]:
        if not isinstance(payload, dict):
            raise FincaValidationError("El cuerpo debe ser un JSON valido.")

        nombre = payload.get("nombre")
        ubicacion = payload.get("ubicacion")

        if nombre is not None and (not isinstance(nombre, str) or not nombre.strip()):
            raise FincaValidationError("'nombre' debe ser string no vacio.")

        lat = lon = altitud_m = None
        if ubicacion is not None:
            if not isinstance(ubicacion, dict):
                raise FincaValidationError("'ubicacion' debe ser un objeto.")
            if "lat" in ubicacion:
                lat = self._to_float(ubicacion.get("lat"), "ubicacion.lat")
            if "lon" in ubicacion:
                lon = self._to_float(ubicacion.get("lon"), "ubicacion.lon")
            if "altitud_m" in ubicacion:
                altitud_m = self._to_float(ubicacion.get("altitud_m"), "ubicacion.altitud_m")

        if nombre is None and lat is None and lon is None and altitud_m is None:
            raise FincaValidationError("No hay campos para actualizar.")

        return nombre.strip() if isinstance(nombre, str) else None, lat, lon, altitud_m

    @staticmethod
    def _to_float(value, field_name: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise FincaValidationError(f"'{field_name}' debe ser numerico.") from exc

    @staticmethod
    def _validar_rangos_geograficos(lat: float, lon: float) -> None:
        if not (-90 <= lat <= 90):
            raise FincaValidationError("'ubicacion.lat' debe estar entre -90 y 90.")
        if not (-180 <= lon <= 180):
            raise FincaValidationError("'ubicacion.lon' debe estar entre -180 y 180.")
