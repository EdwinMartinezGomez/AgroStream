# 🌱 Simulador de Monitoreo Agrícola — Módulo Python + Redis

Módulo de simulación de sensores IoT que usa **Open-Meteo** como fuente
de datos meteorológicos reales y escribe las lecturas en **Redis**.

---

## Estructura del módulo

```
simulador/
├── config.py             ← Fincas, umbrales, parámetros de Redis y simulación
├── openmeteo_client.py   ← Cliente Open-Meteo con caché local + fallback físico
├── sensor_simulator.py   ← Sensores virtuales con ruido gaussiano y deriva
├── alert_engine.py       ← Detección de condiciones críticas
├── data_ingestion.py     ← Validación y escritura en Redis (pipeline)
├── main.py               ← Orquestador asyncio — punto de entrada
└── requirements.txt
```

---

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Instalar dependencias (solo 3)
pip install -r requirements.txt

```

---

## Ejecución

```bash
python main.py
```

### Salida esperada

```
08:14:22  INFO     __main__ — ══════════════════════════════════════════════════════
08:14:22  INFO     __main__ —   🌱  Sistema de Monitoreo Agrícola — Simulador IoT
08:14:22  INFO     __main__ — ══════════════════════════════════════════════════════
08:14:22  INFO     __main__ — ⏳  Inicializando sensores y descargando datos Open-Meteo…
08:14:22  INFO     openmeteo_client — 🌐  Descargando datos Open-Meteo para lat=5.53 lon=-73.36 …
08:14:23  INFO     openmeteo_client — ✅  Open-Meteo: 24 horas descargadas.
08:14:25  INFO     __main__ — 🚀  Iniciando simulación con 27 sensores concurrentes
08:14:25  INFO     __main__ — ⏱️   Intervalo de lectura: 5 s | Ctrl+C para detener
08:14:55  INFO     data_ingestion — 📊  Lecturas: 145 | Errores: 0 | TPS promedio: 4.8
```

---

## Flujo de datos

```
Open-Meteo API (datos reales horarios)
        │
        ▼  (caché local 1 h — cache/openmeteo/)
openmeteo_client.py
        │  valor base por hora del día
        ▼
sensor_simulator.py  →  SensorVirtual.leer()
        │  + ruido gaussiano (σ calibrado por tipo)
        │  + deriva del hardware (±2 unidades max)
        │  + anomalía esporádica (0.5 % prob.)
        ▼
data_ingestion.py  →  ServicioIngesta.procesar()
        │  validar_lectura() — campos + rangos físicos
        │  pipeline Redis (7 comandos en 1 llamada de red)
        ├──→ alert_engine.py  →  evaluar_lectura()
        │         │
        │         ▼
        │   alertas en Redis
        ▼
      Redis
```

---

## Claves Redis generadas

| Clave | Tipo | Contenido | TTL |
|-------|------|-----------|-----|
| `sensor:{id}:estado` | Hash | Última lectura completa | 24 h |
| `sensor:{id}:stream` | List | Últimas 500 lecturas (JSON) | 24 h |
| `finca:{id}:ultima` | Hash | Última lectura por tipo | 24 h |
| `alertas:global` | List | Últimas 1 000 alertas | Sin TTL |
| `alertas:{finca_id}` | List | Últimas 200 alertas de la finca | 24 h |

### Verificar en Redis CLI

```bash
redis-cli

# Ver última lectura de un sensor
HGETALL sensor:finca_001_temperatura_01:estado

# Ver últimas 5 lecturas del historial
LRANGE sensor:finca_001_temperatura_01:stream 0 4

# Ver estado actual de una finca (todos los tipos)
HGETALL finca:finca_001:ultima

# Ver últimas 3 alertas globales
LRANGE alertas:global 0 2

# Contar sensores activos
KEYS sensor:*:estado | wc -l
```

---

## Open-Meteo vs modo fallback

El módulo detecta automáticamente si Open-Meteo está disponible:

| Condición | Modo | Valor base |
|-----------|------|------------|
| Internet disponible | `openmeteo` | Datos meteorológicos reales de Boyacá |
| Sin internet | `fallback` | Modelo físico sinusoidal (ciclo diurno) |

El campo `"fuente"` en cada lectura indica qué modo está activo.

---

## Personalización

Edita `config.py`:

```python
# Agregar una finca real
FINCAS.append({
    "id": "finca_004", "nombre": "Mi Finca",
    "lat": 5.61, "lon": -73.28, "altitud_m": 2550
})

# Ajustar umbrales agronómicos
UMBRALES["temperatura"]["critico_bajo"] = 4.0   # °C — cultivo más resistente

# Cambiar intervalo de lectura
INTERVALO_LECTURA_S = 10   # cada 10 segundos
```
