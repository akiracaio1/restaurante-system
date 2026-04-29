import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ingredientesAPI } from '../api'

const fmt = (v, unit) =>
  `R$ ${Number(v).toFixed(2).replace('.', ',')} / ${unit}`

export default function IngredientesLista() {
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [success, setSuccess] = useState('')

  async function load() {
    try {
      setLoading(true)
      const { data } = await ingredientesAPI.listar()
      setItems(data)
    } catch {
      setError('Erro ao carregar ingredientes.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id, name) {
    if (!window.confirm(`Excluir "${name}"? Esta ação não pode ser desfeita.`)) return
    try {
      await ingredientesAPI.excluir(id)
      setItems(prev => prev.filter(i => i.id !== id))
      setSuccess(`"${name}" excluído com sucesso.`)
      setTimeout(() => setSuccess(''), 3500)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao excluir ingrediente.')
      setTimeout(() => setError(''), 4000)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Ingredientes</h1>
          <p className="page-subtitle">
            {items.length} ingrediente{items.length !== 1 ? 's' : ''} cadastrado{items.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Link to="/ingredientes/novo" className="btn btn-primary">+ Novo Ingrediente</Link>
      </div>

      {error   && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="card">
        {loading ? (
          <div className="loading">Carregando...</div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🥦</div>
            <p className="empty-text">Nenhum ingrediente cadastrado</p>
            <p className="empty-sub">Clique em "Novo Ingrediente" para começar.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Unidade</th>
                  <th>Custo Unitário</th>
                  <th>Estoque Mínimo</th>
                  <th style={{ textAlign: 'right' }}>Ações</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.id}>
                    <td style={{ fontWeight: 600 }}>{item.name}</td>
                    <td>
                      <span className="badge badge-unit">{item.unit}</span>
                    </td>
                    <td>{fmt(item.unit_cost, item.unit)}</td>
                    <td>
                      {item.min_stock} {item.unit}
                    </td>
                    <td>
                      <div className="td-actions" style={{ justifyContent: 'flex-end' }}>
                        <Link
                          to={`/ingredientes/${item.id}/editar`}
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
