import type { Farm } from '../lib/types'

type FarmListProps = {
  farms: Farm[]
  selectedId?: string
  onSelect: (farm: Farm) => void
}

export default function FarmList({ farms, selectedId, onSelect }: FarmListProps) {
  return (
    <section className="panel panel-farms">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Fincas activas</p>
          <h2>Monitoreo en tiempo real</h2>
        </div>
        <span className="pill">{farms.length} fincas</span>
      </div>

      <div className="farm-list">
        {farms.map((farm) => {
          const selected = farm.id === selectedId
          return (
            <button
              key={farm.id}
              className={`farm-card ${selected ? 'selected' : ''}`}
              onClick={() => onSelect(farm)}
            >
              <div className="farm-card-main">
                <strong>{farm.nombre}</strong>
                <span>
                  {farm.lat.toFixed(4)}, {farm.lon.toFixed(4)} · {farm.altitud_m} m
                </span>
              </div>
              <div className="farm-card-meta">
                <span>{farm.lecturas?.total_sensores ?? 0} sensores</span>
                <span>{farm.alertas_recientes?.length ?? 0} alertas</span>
              </div>
            </button>
          )
        })}
      </div>
    </section>
  )
}
