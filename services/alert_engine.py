import logging
from datetime import datetime, timezone
from config import UMBRALES
logger = logging.getLogger(__name__)
def evaluar_lectura(lectura: dict) -> list[dict]:
    tipo    = lectura["tipo"]
    valor   = lectura["valor"]
    alertas = []
    reglas  = UMBRALES.get(tipo, {})
    if "critico_alto" in reglas and valor > reglas["critico_alto"]:
        alertas.append(_construir(lectura, "critico",
            f"{_nombre(tipo)} excesivamente alta: "
            f"{valor} {lectura['unidad']} "
            f"(umbral: {reglas['critico_alto']} {lectura['unidad']})"))
    if "critico_bajo" in reglas and valor < reglas["critico_bajo"]:
        alertas.append(_construir(lectura, "critico",
            f"{_nombre(tipo)} peligrosamente baja: "
            f"{valor} {lectura['unidad']} "
            f"(umbral: {reglas['critico_bajo']} {lectura['unidad']})"))
    for a in alertas:
        logger.warning("🚨  [%s] %s — %s",
                       a["nivel"].upper(), a["finca_nombre"], a["mensaje"])
    return alertas
def _construir(lectura: dict, nivel: str, mensaje: str) -> dict:
    ts = datetime.now(tz=timezone.utc).isoformat()
    return {
        "alerta_id":    f"ALT_{lectura['sensor_id']}_{int(datetime.now(tz=timezone.utc).timestamp())}",
        "sensor_id":    lectura["sensor_id"],
        "finca_id":     lectura["finca_id"],
        "finca_nombre": lectura["finca_nombre"],
        "tipo_sensor":  lectura["tipo"],
        "nivel":        nivel,
        "mensaje":      mensaje,
        "valor":        lectura["valor"],
        "unidad":       lectura["unidad"],
        "timestamp":    ts,
    }
def _nombre(tipo: str) -> str:
    return {
        "temperatura":   "Temperatura",
        "humedad":       "Humedad ambiental",
        "co2":           "Nivel de CO₂",
        "humedad_suelo": "Humedad del suelo",
        "radiacion":     "Radiación solar",
    }.get(tipo, tipo.replace("_", " ").title())
