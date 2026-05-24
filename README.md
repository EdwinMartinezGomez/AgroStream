# AgroStream Backend

Backend modular para fincas agrícolas con Flask, Redis, simulación en background y WebSocket en tiempo real.

## Arquitectura

- REST para CRUD de fincas
- WebSocket para lecturas, alertas y estado de simulación
- Redis como fuente de persistencia
- Open-Meteo como base meteorológica para la simulación

## Estructura

```text
AgroStream/
├── main.py
├── config.py
├── requirements.txt
├── README.md
├── .gitignore
├── api/
│   ├── app_factory.py
│   ├── realtime.py
│   └── routes/fincas.py
├── repositories/
│   └── finca_repository.py
├── services/
│   ├── data_ingestion.py
│   ├── finca_service.py
│   ├── openmeteo_client.py
│   └── alert_engine.py
└── simulation/
    ├── simulation_manager.py
    └── sensor_simulator.py
```

## Instalación

```bash
pip install -r requirements.txt
```

## Configuración de Redis en la nube

Define una de estas opciones antes de ejecutar `main.py`:

### Opción 1: URL completa

```bash
set REDIS_URL=redis://default:TU_PASSWORD@TU_HOST:PUERTO/0
```

### Opción 2: Variables separadas

```bash
set REDIS_HOST=TU_HOST
set REDIS_PORT=PUERTO
set REDIS_USERNAME=default
set REDIS_PASSWORD=TU_PASSWORD
set REDIS_DB=0
```

Si no configuras estas variables, el backend intentará `localhost:6379`.

## Ejecución

```bash
python main.py
```

## Frontend React

El panel visual está en [frontend](frontend).

### Instalar dependencias

```bash
cd frontend
npm install
```

### Ejecutar en desarrollo

```bash
npm run dev
```

El frontend usa por defecto:

- `http://localhost:5000` para REST
- `http://localhost:5000` para Socket.IO

## REST de fincas

Base URL: `http://localhost:5000`

- `GET /api/fincas`
- `GET /api/fincas/<finca_id>`
- `POST /api/fincas`
- `PUT /api/fincas/<finca_id>`
- `PATCH /api/fincas/<finca_id>`
- `DELETE /api/fincas/<finca_id>`
- `GET /health`

### Crear finca

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

## WebSocket

Conéctate a `http://localhost:5000` usando Socket.IO.

### Eventos del servidor

- `server_ready`
- `fincas_snapshot`
- `finca_snapshot`
- `simulation_state`
- `sensor_reading`
- `sensor_reading_global`
- `sensor_alerts`
- `sensor_alerts_global`
- `finca_deleted`

### Eventos del cliente

- `request_fincas`
- `request_finca` con `{ "finca_id": "finca_001" }`
- `request_simulation_state`
- `subscribe_finca` con `{ "finca_id": "finca_001" }`
- `unsubscribe_finca` con `{ "finca_id": "finca_001" }`

## Redis

Claves principales:

- `fincas:ids`
- `finca:{id}:meta`
- `finca:{id}:ultima`
- `sensor:{id}:estado`
- `sensor:{id}:stream`
- `alertas:global`
- `alertas:{finca_id}`
