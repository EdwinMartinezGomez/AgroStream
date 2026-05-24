import { useState } from 'react'
import type { FormEvent } from 'react'

type FarmFormProps = {
  onCreate: (payload: {
    nombre: string
    ubicacion: {
      lat: number
      lon: number
      altitud_m: number
    }
  }) => Promise<void>
}

export default function FarmForm({ onCreate }: FarmFormProps) {
  const [nombre, setNombre] = useState('')
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [altitud, setAltitud] = useState('')
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setFeedback(null)

    try {
      await onCreate({
        nombre,
        ubicacion: {
          lat: Number(lat),
          lon: Number(lon),
          altitud_m: Number(altitud),
        },
      })
      setNombre('')
      setLat('')
      setLon('')
      setAltitud('')
      setFeedback('Finca creada correctamente')
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'No se pudo crear la finca')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="panel farm-form-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Nueva finca</p>
          <h2>Agregar ubicación</h2>
        </div>
        <span className="pill">REST</span>
      </div>

      <form className="farm-form" onSubmit={submit}>
        <label>
          Nombre
          <input value={nombre} onChange={(event) => setNombre(event.target.value)} placeholder="Finca La Aurora" required />
        </label>
        <div className="farm-form-grid">
          <label>
            Latitud
            <input value={lat} onChange={(event) => setLat(event.target.value)} placeholder="5.53" required />
          </label>
          <label>
            Longitud
            <input value={lon} onChange={(event) => setLon(event.target.value)} placeholder="-73.36" required />
          </label>
          <label>
            Altitud (m)
            <input value={altitud} onChange={(event) => setAltitud(event.target.value)} placeholder="2600" required />
          </label>
        </div>
        <button className="farm-form-submit" type="submit" disabled={loading}>
          {loading ? 'Creando...' : 'Crear finca'}
        </button>
        {feedback ? <p className="farm-form-feedback">{feedback}</p> : null}
      </form>
    </section>
  )
}
