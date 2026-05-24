import { useEffect, useMemo, useState } from 'react'
import { CloudSun, Leaf, MapPinned, Radar, Thermometer, Waves } from 'lucide-react'
import FarmForm from './components/FarmForm'
import FarmList from './components/FarmList'
import FarmSpecificChart from './components/FarmSpecificChart'
import GlobalReadingsChart from './components/GlobalReadingsChart'
import MetricCard from './components/MetricCard'
import WeatherCharts from './components/WeatherCharts'
import { createFinca, fetchFinca, fetchFincas } from './lib/api'
import { socket } from './lib/socket'
import type { AlertItem, Farm, SensorReading, SimulationState } from './lib/types'

function App() {
  const [farms, setFarms] = useState<Farm[]>([])
  const [selectedFarm, setSelectedFarm] = useState<Farm | undefined>()
  const [simulationState, setSimulationState] = useState<SimulationState | undefined>()
  const [globalReadings, setGlobalReadings] = useState<SensorReading[]>([])
  const [globalAlerts, setGlobalAlerts] = useState<AlertItem[]>([])
  const [status, setStatus] = useState('Desconectado')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchFincas()
      .then((data) => {
        setFarms(data)
        setSelectedFarm((current) => current ?? data[0])
      })
      .catch(() => setError('No se pudo cargar el listado de fincas'))
  }, [])

  useEffect(() => {
    if (!selectedFarm) return

    fetchFinca(selectedFarm.id)
      .then((data) => setSelectedFarm(data))
      .catch(() => setError('No se pudo cargar el detalle de la finca'))
  }, [selectedFarm?.id])

  useEffect(() => {
    socket.connect()

    const handleConnect = () => setStatus('Conectado')
    const handleDisconnect = () => setStatus('Desconectado')
    const handleFincasSnapshot = (payload: { fincas: Farm[] }) => {
      setFarms(payload.fincas)
      setSelectedFarm((current) => {
        if (!current) return payload.fincas[0]
        return payload.fincas.find((farm) => farm.id === current.id) ?? payload.fincas[0]
      })
    }
    const handleFincaSnapshot = (payload: { finca: Farm }) => {
      setSelectedFarm(payload.finca)
      setFarms((current) => {
        const next = current.filter((farm) => farm.id !== payload.finca.id)
        return [payload.finca, ...next]
      })
    }
    const handleSimulationState = (payload: SimulationState) => setSimulationState(payload)
    const handleSensorReading = (reading: SensorReading) => {
      setGlobalReadings((current) => [reading, ...current].slice(0, 30))
      setSelectedFarm((current) => {
        if (!current || current.id !== reading.finca_id) return current
        const updatedReadings = current.lecturas?.sensores ?? []
        return {
          ...current,
          lecturas: {
            ultima_por_tipo: {
              ...(current.lecturas?.ultima_por_tipo ?? {}),
              [reading.tipo]: reading,
            },
            sensores: [reading, ...updatedReadings].slice(0, 120),
            total_sensores: current.lecturas?.total_sensores ?? 0,
          },
        }
      })
      setFarms((current) =>
        current.map((farm) =>
          farm.id === reading.finca_id
            ? {
                ...farm,
                lecturas: {
                  ultima_por_tipo: {
                    ...(farm.lecturas?.ultima_por_tipo ?? {}),
                    [reading.tipo]: reading,
                  },
                  sensores: [reading, ...(farm.lecturas?.sensores ?? [])].slice(0, 120),
                  total_sensores: farm.lecturas?.total_sensores ?? 0,
                },
              }
            : farm,
        ),
      )
    }
    const handleSensorAlerts = (payload: { finca_id: string; alertas: AlertItem[] }) => {
      setGlobalAlerts((current) => [...payload.alertas, ...current].slice(0, 30))
      setSelectedFarm((current) => {
        if (!current || current.id !== payload.finca_id) return current
        return {
          ...current,
          alertas_recientes: [...(current.alertas_recientes ?? []), ...payload.alertas].slice(0, 10),
        }
      })
    }

    socket.on('connect', handleConnect)
    socket.on('disconnect', handleDisconnect)
    socket.on('fincas_snapshot', handleFincasSnapshot)
    socket.on('finca_snapshot', handleFincaSnapshot)
    socket.on('simulation_state', handleSimulationState)
    socket.on('sensor_reading', handleSensorReading)
    socket.on('sensor_alerts', handleSensorAlerts)
    socket.on('server_ready', () => setError(null))

    return () => {
      socket.off('connect', handleConnect)
      socket.off('disconnect', handleDisconnect)
      socket.off('fincas_snapshot', handleFincasSnapshot)
      socket.off('finca_snapshot', handleFincaSnapshot)
      socket.off('simulation_state', handleSimulationState)
      socket.off('sensor_reading', handleSensorReading)
      socket.off('sensor_alerts', handleSensorAlerts)
      socket.disconnect()
    }
  }, [])

  useEffect(() => {
    if (!selectedFarm) return
    socket.emit('subscribe_finca', { finca_id: selectedFarm.id })
    return () => {
      socket.emit('unsubscribe_finca', { finca_id: selectedFarm.id })
    }
  }, [selectedFarm?.id])

  const latestMetrics = useMemo(() => {
    const readings = selectedFarm?.lecturas?.ultima_por_tipo ?? {}
    return [
      { label: 'Temperatura', value: readings.temperatura ? `${readings.temperatura.valor} ${readings.temperatura.unidad}` : '--', hint: 'Ciclo térmico agrícola' },
      { label: 'Humedad', value: readings.humedad ? `${readings.humedad.valor} ${readings.humedad.unidad}` : '--', hint: 'Ambiente vivo' },
      { label: 'CO₂', value: readings.co2 ? `${readings.co2.valor} ${readings.co2.unidad}` : '--', hint: 'Ventilación y respiración' },
      { label: 'Humedad suelo', value: readings.humedad_suelo ? `${readings.humedad_suelo.valor} ${readings.humedad_suelo.unidad}` : '--', hint: 'Balance hídrico' },
    ]
  }, [selectedFarm])

  const latestAlert = selectedFarm?.alertas_recientes?.[0]

  const handleCreateFarm = async (payload: {
    nombre: string
    ubicacion: { lat: number; lon: number; altitud_m: number }
  }) => {
    const created = await createFinca(payload)
    setError(null)
    setSelectedFarm(created)
  }

  return (
    <main className="app-shell">
      <div className="sky-glow sky-glow-left" />
      <div className="sky-glow sky-glow-right" />

      <header className="hero">
        <div>
          <p className="eyebrow">AgroStream</p>
          <h1>Panel meteorológico reactivo para fincas</h1>
          <p className="hero-copy">
            Monitoreo en tiempo real. Las gráficas y alertas se actualizan al instante mediante Socket.IO.
          </p>
        </div>

        <div className="hero-status">
          <div className="status-chip">
            <span className={`status-dot ${status === 'Conectado' ? 'online' : ''}`} />
            {status}
          </div>
          <div className="status-chip subtle">
            <Radar size={16} />
            {simulationState?.active_sensors ?? 0} sensores activos
          </div>
        </div>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="metrics-grid">
        <MetricCard label="Fincas activas" value={farms.length} hint="Desde Redis" />
        <MetricCard label="Estado simulación" value={simulationState?.running ? 'En vivo' : 'Pausada'} hint={simulationState?.waiting_for_fincas ? 'Sin fincas registradas' : 'Procesando lecturas'} />
        <MetricCard label="Alertas recientes" value={selectedFarm?.alertas_recientes?.length ?? 0} hint="De la finca seleccionada" />
        <MetricCard label="Última actualización" value={new Date().toLocaleTimeString()} hint={simulationState ? 'Socket vivo' : 'Esperando conexión'} />
      </section>

      <section className="layout-grid">
        <div className="left-column">
          <FarmForm onCreate={handleCreateFarm} />
          <FarmList farms={farms} selectedId={selectedFarm?.id} onSelect={setSelectedFarm} />

          <section className="panel detail-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Detalle</p>
                <h2>{selectedFarm?.nombre ?? 'Selecciona una finca'}</h2>
              </div>
              {selectedFarm ? (
                <span className="pill">{selectedFarm.id}</span>
              ) : null}
            </div>

            {selectedFarm ? (
              <div className="detail-stack">
                <div className="detail-grid">
                  <div className="location-card">
                    <MapPinned size={18} />
                    <div>
                      <strong>Ubicación geográfica</strong>
                      <p>
                        {selectedFarm.lat.toFixed(4)}, {selectedFarm.lon.toFixed(4)} · {selectedFarm.altitud_m} m
                      </p>
                      <span>
                        {selectedFarm.ubicacion_geografica?.ciudad_principal ?? 'Sin ciudad cercana'}
                        {selectedFarm.ubicacion_geografica?.departamento ? ` · ${selectedFarm.ubicacion_geografica.departamento}` : ''}
                      </span>
                    </div>
                  </div>
                  <div className="location-card">
                    <Thermometer size={18} />
                    <div>
                      <strong>Origen meteorológico</strong>
                      <p>{selectedFarm.lecturas?.ultima_por_tipo?.temperatura?.fuente ?? 'Open-Meteo / fallback'}</p>
                    </div>
                  </div>
                  <div className="location-card">
                    <Waves size={18} />
                    <div>
                      <strong>Sensores</strong>
                      <p>{selectedFarm.lecturas?.total_sensores ?? 0} activos</p>
                    </div>
                  </div>
                  <div className="location-card">
                    <Leaf size={18} />
                    <div>
                      <strong>Alertas</strong>
                      <p>{selectedFarm.alertas_recientes?.length ?? 0} recientes</p>
                    </div>
                  </div>
                </div>

                {selectedFarm.ubicacion_geografica?.ciudades_cercanas?.length ? (
                  <div className="summary-tags">
                    {selectedFarm.ubicacion_geografica.ciudades_cercanas.slice(0, 4).map((ciudad) => (
                      <span key={ciudad.nombre} className="summary-tag">
                        {ciudad.nombre}
                        {ciudad.departamento ? ` · ${ciudad.departamento}` : ''}
                      </span>
                    ))}
                  </div>
                ) : null}

                {latestAlert ? (
                  <div className="alert-spotlight">
                    <div className="alert-spotlight-head">
                      <p className="alert-spotlight-title">
                        Última alerta · {latestAlert.nivel.toUpperCase()}
                      </p>
                      <span className="pill">{latestAlert.tipo_sensor}</span>
                    </div>
                    <strong>{latestAlert.finca_nombre}</strong>
                    <p className="alert-spotlight-message">{latestAlert.mensaje}</p>
                    <div className="summary-tags" style={{ marginTop: '12px' }}>
                      <span className="summary-tag">Valor: {latestAlert.valor} {latestAlert.unidad}</span>
                      <span className="summary-tag">Sensor: {latestAlert.sensor_id}</span>
                      <span className="summary-tag">Hora: {new Date(latestAlert.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ) : null}

                {selectedFarm?.alertas_recientes?.length ? (
                  <div className="alert-mini-list">
                    {selectedFarm.alertas_recientes.slice(0, 3).map((alerta) => (
                      <article key={alerta.alerta_id} className="alert-mini-item">
                        <strong>{alerta.nivel.toUpperCase()} · {alerta.tipo_sensor}</strong>
                        <p>{alerta.mensaje}</p>
                      </article>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="empty-state">No hay fincas cargadas. Crea una desde el backend para comenzar el monitoreo.</p>
            )}
          </section>
        </div>

        <div className="right-column">
          <GlobalReadingsChart readings={globalReadings} />
          <FarmSpecificChart farm={selectedFarm} />
          <WeatherCharts farm={selectedFarm} />
        </div>
      </section>

      <section className="panel reading-strip">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Streaming global</p>
            <h2>Últimas lecturas</h2>
          </div>
          <span className="pill">{globalReadings.length} eventos</span>
        </div>

        <div className="reading-list">
          {globalReadings.slice(0, 8).map((reading) => (
            <article key={`${reading.sensor_id}-${reading.timestamp}`} className="reading-item">
              <div>
                <strong>{reading.finca_nombre}</strong>
                <p>{reading.tipo}</p>
              </div>
              <div className="reading-value">
                <span>{reading.valor}</span>
                <small>{reading.unidad}</small>
              </div>
            </article>
          ))}
        </div>

        <div className="reading-list reading-list-alerts">
          {globalAlerts.slice(0, 6).map((alerta) => (
            <article key={alerta.alerta_id} className="reading-item alert-item">
              <div>
                <strong>{alerta.finca_nombre}</strong>
                <p>{alerta.mensaje}</p>
              </div>
              <div className="reading-value">
                <span>{alerta.nivel}</span>
                <small>{alerta.tipo_sensor}</small>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="panel metrics-grid-bottom">
        <div>
          <p className="eyebrow">Resumen de finca</p>
          <h2>{selectedFarm ? selectedFarm.nombre : 'Sin selección'}</h2>
        </div>
        <div className="summary-tags">
          {latestMetrics.map((metric) => (
            <span key={metric.label} className="summary-tag">
              {metric.label}: {metric.value}
            </span>
          ))}
        </div>
      </section>
    </main>
  )
}

export default App