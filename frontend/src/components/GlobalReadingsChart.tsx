import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { SensorReading } from '../lib/types'

type GlobalReadingsChartProps = {
  readings: SensorReading[]
}

export default function GlobalReadingsChart({ readings }: GlobalReadingsChartProps) {
  const data = readings.slice(0, 20).reverse().map((reading, index) => ({
    index: index + 1,
    valor: reading.valor,
    tipo: reading.tipo,
    unidad: reading.unidad,
    finca: reading.finca_nombre,
  }))

  const activeTypes = Array.from(new Set(data.map((point) => point.tipo)))

  const tooltipFormatter = (value: number, name: string, entry: { payload?: { tipo?: string; unidad?: string } }) => {
    if (name !== 'valor') return [value, name]
    const tipo = entry.payload?.tipo ?? 'lectura'
    const unidad = entry.payload?.unidad ?? ''
    return [`${value}${unidad ? ` ${unidad}` : ''}`, tipo]
  }

  return (
    <section className="panel trends-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Vista global</p>
          <h2>Secuencia de lectura general</h2>
          <p className="panel-note">Variable mostrada: valor bruto de la lectura. El tipo se identifica en el tooltip.</p>
        </div>
        <span className="pill">Todas las fincas</span>
      </div>

      <div className="summary-tags" style={{ marginBottom: '12px' }}>
        <span className="summary-tag">Eje Y: valor de lectura</span>
        <span className="summary-tag">Eje X: lecturas recientes</span>
        {activeTypes.map((type) => (
          <span key={type} className="summary-tag">{type.replace('_', ' ')}</span>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="global-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#1d8fe1" stopOpacity={0.45} />
              <stop offset="95%" stopColor="#1d8fe1" stopOpacity={0.04} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#d8ecf7" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="index" tick={{ fill: '#5d7b8d' }} />
          <YAxis tick={{ fill: '#5d7b8d' }} label={{ value: 'Valor', angle: -90, position: 'insideLeft', fill: '#5d7b8d' }} />
          <Tooltip formatter={tooltipFormatter} labelFormatter={(label) => `Muestra ${label}`} />
          <Area type="monotone" dataKey="valor" stroke="#1d8fe1" fill="url(#global-gradient)" strokeWidth={3} />
        </AreaChart>
      </ResponsiveContainer>
    </section>
  )
}
