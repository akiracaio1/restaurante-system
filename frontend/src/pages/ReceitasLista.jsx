import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { receitasAPI } from '../api'

const fmt    = (v) => `R$ ${Number(v).toFixed(2).replace('.', ',')}`
const fmtPct = (v) => `${Number(v).toFixed(1)}%`

function cmvBadge(v) {
  if (v <= 30) return 'badge-green'
  if (v <= 35) return 'badge-orange'
  if (v <= 40) return 'badge-warning'
  return 'badge-red'
}

const CAT_ICON = {
  'prato principal': '🍽️',
  'sobremesa':       '🍰',
  'bebida':          '🥤',
  'entrada':         '🥗',
  'petisco':         '🍟',
  'outro':           '📦',
}

export default function ReceitasLista() {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    try {
      setLoading(true)
      const { data } = await receitasAPI.listar()
      setItems(data)
    } catch {
      setError('Erro ao carregar receitas.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id, name) {
    if (!window.confirm(`Excluir a receita "${name}"? Esta ação não pode ser desfeita.`)) return
    try {
      await receitasAPI.excluir(id)
      setItems(prev => prev.filter(i => i.id !== id))
      setSuccess(`"${name}" excluída com sucesso.`)
      setTimeout(() => setSuccess(''), 3500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao excluir receita.')
      setTimeout(() => setError(''), 4000)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Receitas</h1>
          <p className="page-subtitle">
            {items.length} receita{items.length !== 1 ? 's' : ''} cadastrada{items.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Link to="/receitas/nova" className="btn btn-primary">+ Nova Receita</Link>
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="card">
        {loading ? (
          <div className="loading">Carregando...</div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <p className="empty-text">Nenhuma receita cadastrada</p>
            <p className="empty-sub">Clique em "Nova Receita" para começar.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Receita</th>
                  <th>Categoria</th>
                  <th>Preço de Venda</th>
                  <th>Custo Total</th>
                  <th>CMV %</th>
                  <th>Porções</th>
                  <th style={{ textAlign: 'right' }}>Ações</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.id}>
                    <td>
                      <div style={{ fontWeight: 700 }}>{item.name}</div>
                      {item.description && (
                        <div style={{ fontSize: '.78rem', color: 'var(--muted)', marginTop: '.1rem' }}>
                          {item.description}
                        </div>
                      )}
                    </td>
                    <td>
                      <span className="cat-badge">
                        {CAT_ICON[item.category] || '📦'} {item.category}
                      </span>
                    </td>
                    <td style={{ fontWeight: 700, color: 'var(--green-mid)' }}>
                      {fmt(item.sale_price)}
                    </td>
                    <td>{fmt(item.total_cost)}</td>
                    <td>
                      <span className={`badge ${cmvBadge(item.cmv_percent)}`}>
                        {fmtPct(item.cmv_percent)}
                      </span>
                    </td>
                    <td>
                      {item.yield_portions} {item.yield_portions === 1 ? 'porção' : 'porções'}
                    </td>
                    <td>
                      <div className="td-actions" style={{ justifyContent: 'flex-end' }}>
                        <Link
                          to={`/receitas/${item.id}/editar`}
                          className="btn btn-sm btn-outline"
                        >
                          Editar
                        </Link>
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleDelete(item.id, item.name)}
                        >
                          Excluir
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
