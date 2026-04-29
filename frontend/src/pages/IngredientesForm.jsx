import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { ingredientesAPI } from '../api'

const UNITS = ['kg', 'g', 'L', 'ml', 'unidade']

const EMPTY = { name: '', unit: 'kg', unit_cost: '', min_stock: '' }

export default function IngredientesForm() {
  const { id }    = useParams()
  const navigate  = useNavigate()
  const isEdit    = Boolean(id)

  const [form, setForm]       = useState(EMPTY)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving]   = useState(false)
  const [error, setError]     = useState('')

  useEffect(() => {
    if (!isEdit) return
    ingredientesAPI.buscar(id)
      .then(({ data }) =>
        setForm({
          name:      data.name,
          unit:      data.unit,
          unit_cost: String(data.unit_cost),
          min_stock: String(data.min_stock),
        })
      )
      .catch(() => setError('Erro ao carregar ingrediente.'))
      .finally(() => setLoading(false))
  }, [id])

  const handle = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  async function submit(e) {
    e.preventDefault()
    setError('')

    if (!form.name.trim())                              return setError('Nome é obrigatório.')
    if (form.unit_cost === '' || isNaN(form.unit_cost)) return setError('Custo unitário inválido.')
    if (Number(form.unit_cost) < 0)                     return setError('Custo não pode ser negativo.')
    if (form.min_stock === '' || isNaN(form.min_stock)) return setError('Estoque mínimo inválido.')

    const payload = {
      name:      form.name.trim(),
      unit:      form.unit,
      unit_cost: Number(form.unit_cost),
      min_stock: Number(form.min_stock),
    }

    try {
      setSaving(true)
      if (isEdit) await ingredientesAPI.atualizar(id, payload)
      else        await ingredientesAPI.criar(payload)
      navigate('/ingredientes')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar ingrediente.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="loading">Carregando...</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{isEdit ? 'Editar Ingrediente' : 'Novo Ingrediente'}</h1>
        </div>
      </div>

      <div className="form-card">
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={submit}>
          <div className="form-grid" style={{ marginBottom: '1.25rem' }}>
            <div className="form-group full">
              <label htmlFor="name">Nome do Ingrediente *</label>
              <input
                id="name"
                name="name"
                value={form.name}
                onChange={handle}
                placeholder="Ex: Farinha de trigo"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label htmlFor="unit">Unidade de Medida *</label>
              <select id="unit" name="unit" value={form.unit} onChange={handle}>
                {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="unit_cost">Custo por {form.unit} (R$) *</label>
              <input
                id="unit_cost"
                name="unit_cost"
                type="number"
                step="0.0001"
                min="0"
                value={form.unit_cost}
                onChange={handle}
                placeholder="0,00"
              />
            </div>

            <div className="form-group">
              <label htmlFor="min_stock">Estoque Mínimo ({form.unit})</label>
              <input
                id="min_stock"
                name="min_stock"
                type="number"
                step="0.001"
                min="0"
                value={form.min_stock}
                onChange={handle}
                placeholder="0"
              />
            </div>
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Salvando...' : isEdit ? 'Salvar Alterações' : 'Cadastrar Ingrediente'}
            </button>
            <Link to="/ingredientes" className="btn btn-outline">Cancelar</Link>
          </div>
        </form>
      </div>
    </div>
  )
}
