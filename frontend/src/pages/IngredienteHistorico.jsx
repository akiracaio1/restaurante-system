import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { comprasAPI, ingredientesAPI } from '../api'

const fmt = (v, d = 4) => `R$ ${Number(v).toFixed(d).replace('.', ',')}`

function fmtDate(d) {
  if (!d) return ''
  const [y, m, day] = d.split('-')
  return `${day}/${m}/${y}`
}

function CostChart({ data }) {
  const W = 600, H = 200, padX = 64, padY = 24

  if (data.length === 0) return null

  const costs  = data.map(p => p.unit_cost)
  const minV   = Math.min(...costs)
  const maxV   = Math.max(...costs)
  const rangeV = maxV - minV || 1
  const gridN  = 4

  const toX = (i) => padX + (i / Math.max(data.length - 1, 1)) * (W - 2 * padX)
  const toY = (v) => padY + (1 - (v - minV) / rangeV) * (H - 2 * padY)

  const pathD = data.map((p, i) => `${i === 0 ? 'M' : 'L'} ${toX(i)},${toY(p.unit_cost)}`).join(' ')

  return (
    <div style={{ overflowX: 'auto' }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', minWidth: '300px', maxHeight: '220px', display: 'block' }}>
        {Array.from({ length: gridN + 1 }, (_, i) => {
          const y = padY + (i / gridN) * (H - 2 * padY)
          const v = maxV - (i / gridN) * rangeV
          return (
            <g key={i}>
              <line x1={padX} y1={y} x2={W - padX} y2={y} stroke="var(--border)" strokeWidth="1" />
              <text x={padX - 6} y={y + 4} textAnchor="end" fontSize="10" fill="var(--muted)">
                {Number(v).toFixed(2)}
              </text>
            </g>
          )
        })}

        {data.map((p, i) => (
          <text key={i} x={toX(i)} y={H - 4} textAnchor="middle" fontSize="9" fill="var(--muted)">
            {fmtDate(p.purchase_date)}
          </text>
        ))}

        <path d={pathD} fill="none" stroke="var(--orange)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        {data.map((p, i) => (
          <circle key={i} cx={toX(i)} cy={toY(p.unit_cost)} r="4.5" fill="var(--orange)" />
        ))}
      </svg>
    </div>
  )
}

export default function IngredienteHistorico() {
  const { id } = useParams()
  const [history, setHistory]       = useState([])
  const [ingredient, setIngredient] = useState(null)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState('')

  useEffect(() => {
    async function load() {
      try {
        const [{ data: hist }, { data: ing }] = await Promise.all([
          comprasAPI.historico(id),
          ingredientesAPI.buscar(id),
        ])
        setHistory(hist)
        setIngredient(ing)
      } catch {
        setError('Erro ao carregar histórico.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  if (loading) return <div className="loading">Carregando histórico…</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">📈 Histórico — {ingredient?.name || 'Ingrediente'}</h1>
          <p className="page-subtitle">
            {history.length} compra{history.length !== 1 ? 's' : ''} registrada{history.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Link to="/ingredientes" className="btn btn-ghost">← Voltar</Link>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {history.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">📊</span>
            <p className="empty-text">Nenhuma compra registrada para este ingrediente</p>
            <p className="empty-sub">
              <Link to="/compras/nova" style={{ color: 'var(--orange)', fontWeight: 700 }}>
                Registre uma compra
              </Link>
            </p>
          </div>
        </div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <p className="section-title">Evolução do Custo Unitário</p>
            <CostChart data={history} />
          </div>

          <div className="card" style={{ padding: 0, overflow: 'auto' }}>
            <table className="ing-table" style={{ margin: 0 }}>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Fornecedor</th>
                  <th>Local</th>
                  <th>Qtd</th>
                  <th>Total Pago</th>
                  <th>Custo Unit.</th>
                  <th>Variação</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item, i) => {
                  const prev = i > 0 ? history[i - 1].unit_cost : null
                  const variation = prev !== null ? ((item.unit_cost - prev) / prev * 100) : null
                  return (
                    <tr key={item.id}>
                      <td>{fmtDate(item.purchase_date)}</td>
                      <td>{item.supplier || '—'}</td>
                      <td>{item.location || '—'}</td>
                      <td>{item.quantity} {item.unit}</td>
                      <td>{fmt(item.total_price, 2)}</td>
                      <td style={{ fontWeight: 700 }}>{fmt(item.unit_cost)}/{ingredient?.unit}</td>
                      <td>
                        {variation === null ? (
                          <span style={{ color: 'var(--muted)' }}>—</span>
                        ) : (
                          <span style={{ color: variation > 0 ? '#e74c3c' : '#27ae60', fontWeight: 600 }}>
                            {variation > 0 ? '▲' : '▼'} {Math.abs(variation).toFixed(1)}%
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
