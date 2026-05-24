import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Farm } from '../lib/types'

type WeatherChartsProps = {
  farm?: Farm
}

const chartColors = {
  temperatura: '#1d8fe1',
  humedad: '#64d2ff',
  co2: '#0f4c81',
  humedad_suelo: '#3ea8ff',
  radiacion: '#9ddcff',
}

export default function WeatherCharts({ farm }: WeatherChartsProps) {
  const readings = farm?.lecturas?.sensores ?? []
  const latestByType = farm?.lecturas?.ultima_por_tipo ?? {}

  const data = readings.slice(-30).map((reading, index) => ({
    name: `${index + 1}`,
    temperatura: reading.tipo === 'temperatura' ? reading.valor : null,
    humedad: reading.tipo === 'humedad' ? reading.valor : null,
    co2: reading.tipo === 'co2' ? reading.valor : null,
    humedad_suelo: reading.tipo === 'humedad_suelo' ? reading.valor : null,
    radiacion: reading.tipo === 'radiacion' ? reading.valor : null,
  }))

  return (
    <section className="panel charts-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Señal meteorológica</p>
          <h2>Gráficas vivas</h2>
        </div>
        <span className="pill">Actualización instantánea</span>
      </div>

      <div className="chart-grid">
        {Object.entries(chartColors).map(([type, color]) => (
          <article key={type} className="mini-chart-card">
            <div className="mini-chart-head">
              <span>{type.replace('_', ' ')}</span>
              <strong>{latestByType[type]?.valor ?? '--'} {latestByType[type]?.unidad ?? ''}</strong>
            </div>
            <div className="mini-chart">
              <ResponsiveContainer width="100%" height={120}>
                <AreaChart data={data}>
                  <defs>
                    <linearGradient id={`gradient-${type}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color} stopOpacity={0.45} />
                      <stop offset="95%" stopColor={color} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#d8ecf7" strokeDasharray="3 3" vertical={false} />
                  <XAxis hide dataKey="name" />
                  <YAxis hide domain={["auto", "auto"]} />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey={type}
                    stroke={color}
                    fill={`url(#gradient-${type})`}
                    strokeWidth={2.5}
                    connectNulls
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
