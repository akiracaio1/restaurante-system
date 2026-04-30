import { useState, useEffect } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { ingredientesAPI } from '../api'

const UNITS = ['kg', 'g', 'L', 'ml', 'unidade']

const EMPTY = {
  name: '', unit: 'kg', unit_cost: '', min_stock: '',
  purchase_unit: '', purchase_quantity: '', purchase_cost: '',
  yield_percentage: '100',
}

function calcYieldTotal(stages, yieldPct) {
  if (stages.length > 0) {
    return stages.reduce((acc, s) => acc * (parseFloat(s.yield_percentage) || 100) / 100, 1) * 100
  }
  return parseFloat(yieldPct) || 100
}

export default function IngredientesForm() {
  const { id }    = useParams()
  const navigate  = useNavigate()
  const isEdit    = Boolean(id)

  const [form, setForm]         = useState(EMPTY)
  const [stages, setStages]     = useState([])
  const [newStage, setNewStage] = useState({ name: '', yield_percentage: '' })
  const [loading, setLoading]   = useState(isEdit)
  const [saving, setSaving]     = useState(false)
  const [error, setError]       = useState('')

  useEffect(() => {
    if (!isEdit) return
    ingredientesAPI.buscar(id)
      .then(({ data }) => {
        setForm({
          name:              data.name,
          unit:              data.unit,
          unit_cost:         String(data.unit_cost),
          min_stock:         String(data.min_stock),
          purchase_unit:     data.purchase_unit     || '',
          purchase_quantity: data.purchase_quantity != null ? String(data.purchase_quantity) : '',
          purchase_cost:     data.purchase_cost     != null ? String(data.purchase_cost)     : '',
          yield_percentage:  String(data.yield_percentage ?? 100),
        })
        setStages(data.reduction_stages || [])
      })
      .catch(() => setError('Erro ao carregar ingrediente.'))
      .finally(() => setLoading(false))
  }, [id])

  // Auto-calculate unit_cost when purchase fields change
  useEffect(() => {
    const qty  = parseFloat(form.purchase_quantity)
    const cost = parseFloat(form.purchase_cost)
    if (!isNaN(qty) && qty > 0 && !isNaN(cost) && cost >= 0) {
      setForm(prev => ({ ...prev, unit_cost: (cost / qty).toFixed(6).replace(/\.?0+$/, '') }))
    }
  }, [form.purchase_quantity, form.purchase_cost])

  const handle = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  function addStage() {
    const name  = newStage.name.trim()
    const yPct  = parseFloat(newStage.yield_percentage)
    if (!name || isNaN(yPct) || yPct <= 0 || yPct > 100) return
    setStages(prev => [...prev, { name, yield_percentage: yPct }])
    setNewStage({ name: '', yield_percentage: '' })
  }

  function removeStage(idx) {
    setStages(prev => prev.filter((_, i) => i !== idx))
  }

  const yieldTotal = calcYieldTotal(stages, form.yield_percentage)
  const realUnitCost =
    form.unit_cost !== '' && yieldTotal > 0
      ? parseFloat(form.unit_cost) / (yieldTotal / 100)
      : null

  async function submit(e) {
    e.preventDefault()
    setError('')

    if (!form.name.trim())                              return setError('Nome é obrigatório.')
    if (form.unit_cost === '' || isNaN(form.unit_cost)) return setError('Custo unitário inválido.')
    if (Number(form.unit_cost) < 0)                     return setError('Custo não pode ser negativo.')
    if (form.min_stock === '' || isNaN(form.min_stock)) return setError('Estoque mínimo inválido.')

    const yPct = parseFloat(form.yield_percentage)
    if (isNaN(yPct) || yPct <= 0 || yPct > 100) return setError('Percentual de aproveitamento deve ser entre 1 e 100.')

    const hasPurchase = form.purchase_quantity || form.purchase_cost || form.purchase_unit
    if (hasPurchase && (!form.purchase_unit.trim() || !form.purchase_quantity || !form.purchase_cost)) {
      return setError('Preencha todos os campos de compra (unidade, quantidade e custo).')
    }

    const payload = {
      name:              form.name.trim(),
      unit:              form.unit,
      unit_cost:         Number(form.unit_cost),
      min_stock:         Number(form.min_stock),
      purchase_unit:     form.purchase_unit.trim()  || null,
      purchase_quantity: form.purchase_quantity      ? Number(form.purchase_quantity) : null,
      purchase_cost:     form.purchase_cost          ? Number(form.purchase_cost)     : null,
      yield_percentage:  yPct,
      reduction_stages:  stages.length > 0 ? stages : null,
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

  const hasPurchase = form.purchase_unit || form.purchase_quantity || form.purchase_cost

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
          {/* ── Informações básicas ─────────────────────── */}
          <p className="section-title">Informações Básicas</p>
          <div className="form-grid" style={{ marginBottom: '1.5rem' }}>
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
              <label htmlFor="unit">Unidade de Trabalho *</label>
              <select id="unit" name="unit" value={form.unit} onChange={handle}>
                {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
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

          {/* ── Unidade de compra ───────────────────────── */}
          <p className="section-title">Unidade de Compra</p>
          <div className="form-grid" style={{ marginBottom: '0.5rem' }}>
            <div className="form-group">
              <label htmlFor="purchase_unit">Unidade de Compra</label>
              <input
                id="purchase_unit"
                name="purchase_unit"
                value={form.purchase_unit}
                onChange={handle}
                placeholder="Ex: pacote, caixa, kg"
              />
            </div>

            <div className="form-group">
              <label htmlFor="purchase_quantity">Quantidade em {form.unit} por unidade</label>
              <input
                id="purchase_quantity"
                name="purchase_quantity"
                type="number"
                step="0.001"
                min="0.001"
                value={form.purchase_quantity}
                onChange={handle}
                placeholder={`Ex: 500 (${form.unit})`}
              />
            </div>

            <div className="form-group">
              <label htmlFor="purchase_cost">Custo da Unidade de Compra (R$)</label>
              <input
                id="purchase_cost"
                name="purchase_cost"
                type="number"
                step="0.01"
                min="0"
                value={form.purchase_cost}
                onChange={handle}
                placeholder="Ex: 28,00"
              />
            </div>

            <div className="form-group">
              <label htmlFor="unit_cost">
                Custo por {form.unit} (R$) *
                {hasPurchase && <span style={{ color: 'var(--color-primary)', fontSize: '0.75rem', marginLeft: '0.5rem' }}>calculado</span>}
              </label>
              <input
                id="unit_cost"
                name="unit_cost"
                type="number"
                step="0.000001"
                min="0"
                value={form.unit_cost}
                onChange={handle}
                placeholder="0,00"
              />
            </div>
          </div>
          {hasPurchase && form.purchase_unit && form.purchase_quantity && form.purchase_cost && (
            <p style={{ fontSize: '0.8rem', color: 'var(--color-muted)', marginBottom: '1.5rem' }}>
              1 {form.purchase_unit} = {form.purchase_quantity} {form.unit} → R$ {Number(form.unit_cost || 0).toFixed(4)} / {form.unit}
            </p>
          )}

          {/* ── Fator de redução ────────────────────────── */}
          <p className="section-title">Fator de Redução</p>
          <div className="form-grid" style={{ marginBottom: '1rem' }}>
            <div className="form-group">
              <label htmlFor="yield_percentage">
                Aproveitamento simples (%)
                {stages.length > 0 && <span style={{ color: 'var(--color-muted)', fontSize: '0.75rem', marginLeft: '0.5rem' }}>ignorado quando há etapas</span>}
              </label>
              <input
                id="yield_percentage"
                name="yield_percentage"
                type="number"
                step="0.1"
                min="0.1"
                max="100"
                value={form.yield_percentage}
                onChange={handle}
                disabled={stages.length > 0}
              />
            </div>

            <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
              <div style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: '8px', padding: '0.6rem 1rem', width: '100%' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)', display: 'block' }}>Aproveitamento total</span>
                <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>{yieldTotal.toFixed(1)}%</span>
                {realUnitCost != null && (
                  <span style={{ fontSize: '0.8rem', color: 'var(--color-primary)', display: 'block' }}>
                    Custo real: R$ {realUnitCost.toFixed(4)} / {form.unit}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Etapas de redução */}
          {stages.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              {stages.map((s, i) => (
                <div key={i} style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.5rem' }}>
                  {i > 0 && <span style={{ color: 'var(--color-muted)' }}>→</span>}
                  {i === 0 && <span style={{ color: 'var(--color-muted)', minWidth: '1rem' }}></span>}
                  <span style={{ fontWeight: 600 }}>{s.name}</span>
                  <span className="badge badge-unit">{s.yield_percentage}%</span>
                  <button type="button" className="btn btn-sm btn-danger" onClick={() => removeStage(i)}>✕</button>
                </div>
              ))}
            </div>
          )}

          <div className="add-row" style={{ marginBottom: '1.5rem' }}>
            <div className="form-group" style={{ margin: 0, flex: 2 }}>
              <input
                value={newStage.name}
                onChange={e => setNewStage(p => ({ ...p, name: e.target.value }))}
                placeholder={stages.length === 0 ? 'Ex: bruto → limpo' : 'Próxima etapa (ex: limpo → grelhado)'}
              />
            </div>
            <div className="form-group" style={{ margin: 0, flex: 1 }}>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="100"
                value={newStage.yield_percentage}
                onChange={e => setNewStage(p => ({ ...p, yield_percentage: e.target.value }))}
                placeholder="Aproveitamento %"
                onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addStage())}
              />
            </div>
            <button type="button" className="btn btn-secondary" onClick={addStage}>
              + Etapa
            </button>
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
