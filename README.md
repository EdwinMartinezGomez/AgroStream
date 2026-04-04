# AgroStream Backend

Backend modular en Flask para gestion de fincas y simulacion IoT en segundo plano.

## Que hace

- Expone API REST para CRUD de fincas.
- Persiste fincas en Redis.
- Ejecuta simulacion de sensores mientras el backend esta levantado.
- La simulacion usa las fincas guardadas en Redis:
  - si hay fincas, genera lecturas continuamente
  - si no hay fincas, queda en pausa automatica
- Usa Open-Meteo para datos base y guarda lecturas/alertas en Redis.

## Estructura modular

```text
AgroStream/
├── .gitignore
├── main.py
├── config.py
├── README.md
├── requirements.txt
├── cache/openmeteo/
├── api/
│   ├── app_factory.py
│   └── routes/fincas.py
├── repositories/
│   └── finca_repository.py
├── services/
│   ├── finca_service.py
│   ├── data_ingestion.py
│   ├── openmeteo_client.py
│   └── alert_engine.py
└── simulation/
    ├── simulation_manager.py
    └── sensor_simulator.py
```

## Requisitos

- Python 3.10+
- Redis activo

Instalacion:

```bash
pip install -r requirements.txt
```

## Ejecucion

```bash
python main.py
```

Servidor por defecto:

- Host: `0.0.0.0`
- Puerto: `5000`

## API REST de fincas

Base URL: `http://localhost:5000`

### Crear finca

`POST /api/fincas`

Body JSON (obligatorio):

```json
{
  "nombre": "Finca El Roble",
  "ubicacion": {
    "lat": 5.53,
    "lon": -73.36,
    "altitud_m": 2600
  }
}
```

### Listar fincas

`GET /api/fincas`

### Obtener finca por id

`GET /api/fincas/<finca_id>`

### Actualizar finca

`PUT /api/fincas/<finca_id>` o `PATCH /api/fincas/<finca_id>`

Body JSON (campos opcionales):

```json
{
  "nombre": "Finca Actualizada",
  "ubicacion": {
    "lat": 5.54,
    "lon": -73.35,
    "altitud_m": 2610
  }
}
```

### Eliminar finca

`DELETE /api/fincas/<finca_id>`

### Healthcheck

`GET /health`

## Redis (resumen de claves)

- `fincas:ids`: set de ids de fincas
- `finca:{id}:meta`: metadatos de finca
- `sensor:{id}:estado`: ultima lectura por sensor
- `sensor:{id}:stream`: historial de lecturas por sensor
- `finca:{id}:ultima`: ultima lectura por tipo para cada finca
- `alertas:global`: alertas globales
- `alertas:{finca_id}`: alertas por finca
