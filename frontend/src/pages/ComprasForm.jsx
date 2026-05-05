import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { comprasAPI, ingredientesAPI } from '../api'

const fmt = (v, d = 4) => `R$ ${Number(v).toFixed(d).replace('.', ',')}`

function today() {
  return new Date().toISOString().slice(0, 10)
}

export default function ComprasForm() {
  const navigate = useNavigate()

  const [form, setForm]           = useState({ date: today(), supplier: '', location: '', notes: '' })
  const [ingredients, setIngredients] = useState([])
  const [items, setItems]         = useState([])
  const [addIngId, setAddIngId]   = useState('')
  const [addQty, setAddQty]       = useState('')
  const [addUnit, setAddUnit]     = useState('')
  const [addTotal, setAddTotal]   = useState('')
  const [loading, setLoading]     = useState(true)
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')

  useEffect(() => {
    async function init() {
      try {
        const { data } = await ingredientesAPI.listar()
        setIngredients(data)
        if (data.length > 0) {
          setAddIngId(String(data[0].id))
          setAddUnit(data[0].purchase_unit || data[0].unit)
        }
      } catch {
        setError('Erro ao carregar ingredientes.')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const handle = (e) => setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))

  function handleIngChange(e) {
    const id = e.target.value
    setAddIngId(id)
    const ing = ingredients.find(i => String(i.id) === id)
    if (ing) setAddUnit(ing.purchase_unit || ing.unit)
  }

  function addItem() {
    const qty   = Number(addQty)
    const total = Number(addTotal)
    const ingId = Number(addIngId)
    if (!ingId || qty <= 0 || total <= 0) return
    const ing = ingredients.find(i => i.id === ingId)
    if (!ing) return

    setItems(prev => {
      const exists = prev.find(i => i.ingredient_id === ingId)
      if (exists) {
        return prev.map(i => i.ingredient_id === ingId
          ? { ...i, quantity: qty, unit: addUnit, total_price: total, unit_cost: total / qty }
          : i
        )
      }
      return [...prev, { ingredient_id: ingId, quantity: qty, unit: addUnit, total_price: total, unit_cost: total / qty, ing }]
    })
    setAddQty('')
    setAddTotal('')
  }

  function removeItem(ingId) {
    setItems(prev => prev.filter(i => i.ingredient_id !== ingId))
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!form.date) return setError('Data é obrigatória.')
    if (items.length === 0) return setError('Adicione pelo menos um item à compra.')

    const payload = {
      date: form.date,
      supplier: form.supplier.trim() || null,
      location: form.location.trim() || null,
      notes: form.notes.trim() || null,
      items: items.map(i => ({
        ingredient_id: i.ingredient_id,
        quantity: i.quantity,
        unit: i.unit,
        total_price: i.total_price,
        notes: null,
      })),
    }
    try {
      setSaving(true)
      await comprasAPI.criar(payload)
      navigate('/compras')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar compra.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="loading">Carregando…</div>

  const selectedIng = ingredients.find(i => String(i.id) === addIngId)
  const newUnitCost = Number(addQty) > 0 && Number(addTotal) > 0
    ? Number(addTotal) / Number(addQty)
    : null
  const grandTotal = items.reduce((s, i) => s + i.total_price, 0)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🛒 Nova Compra</h1>
          <p className="page-subtitle">Registre uma nota de compra e atualize o estoque</p>
        </div>
        <Link to="/compras" className="btn btn-ghost">← Voltar</Link>
      </div>

      <div className="form-card" style={{ maxWidth: '860px' }}>
        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={submit}>
          <p className="section-title">Informações da Nota</p>

          <div className="form-grid" style={{ marginBottom: '1rem' }}>
            <div className="form-group">
              <label htmlFor="date">Data *</label>
              <input id="date" name="date" type="date" value={form.date} onChange={handle} />
            </div>
            <div className="form-group">
              <label htmlFor="supplier">Fornecedor</label>
              <input id="supplier" name="supplier" value={form.supplier} onChange={handle} placeholder="Nome do fornecedor" />
            </div>
            <div className="form-group">
              <label htmlFor="location">Local</label>
              <input id="location" name="location" value={form.location} onChange={handle} placeholder="Mercado, distribuidora…" />
            </div>
            <div className="form-group full">
              <label htmlFor="notes">Observações</label>
              <textarea id="notes" name="notes" value={form.notes} onChange={handle} rows={2} placeholder="Observações opcionais…" />
            </div>
          </div>

          <p className="section-title">Itens da Compra</p>

          {ingredients.length === 0 ? (
            <div className="alert alert-error">
              Nenhum ingrediente cadastrado.{' '}
              <Link to="/ingredientes/novo" style={{ color: 'inherit', fontWeight: 700 }}>
                Cadastre ingredientes
              </Link>{' '}
              antes de registrar uma compra.
            </div>
          ) : (
            <>
              <div className="add-box">
                <p className="add-box-label">Adicionar item</p>
                <div className="add-row" style={{ flexWrap: 'wrap', gap: '.5rem' }}>
                  <div className="form-group" style={{ margin: 0, minWidth: '180px' }}>
                    <select value={addIngId} onChange={handleIngChange}>
                      {ingredients.map(i => (
                        <option key={i.id} value={i.id}>{i.name} ({i.unit})</option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ margin: 0, maxWidth: '110px' }}>
                    <input
                      type="number"
                      step="0.001"
                      min="0.001"
                      value={addQty}
                      onChange={e => setAddQty(e.target.value)}
                      placeholder="Quantidade"
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0, maxWidth: '90px' }}>
                    <input
                      type="text"
                      value={addUnit}
                      onChange={e => setAddUnit(e.target.value)}
                      placeholder="Unidade"
                    />
                  </div>
                  <div className="form-group" style={{ margin: 0, maxWidth: '130px' }}>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      value={addTotal}
                      onChange={e => setAddTotal(e.target.value)}
                      placeholder="Total R$"
                    />
                  </div>
                  <button type="button" className="btn btn-secondary" onClick={addItem}>
                    + Adicionar
                  </button>
                </div>

                {selectedIng && newUnitCost !== null && (
                  <div style={{ marginTop: '.6rem', fontSize: '.84rem', display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                    <span>
                      Custo novo: <strong style={{ color: 'var(--orange)' }}>{fmt(newUnitCost)}/{selectedIng.unit}</strong>
                    </span>
                    <span>
                      Custo atual: <strong>{fmt(selectedIng.unit_cost)}/{selectedIng.unit}</strong>
                    </span>
                    {Math.abs(newUnitCost - selectedIng.unit_cost) > 0.0001 && (
                      <span style={{ color: newUnitCost > selectedIng.unit_cost ? '#e74c3c' : '#27ae60', fontWeight: 700 }}>
                        {newUnitCost > selectedIng.unit_cost ? '▲' : '▼'}{' '}
                        {(Math.abs(newUnitCost - selectedIng.unit_cost) / selectedIng.unit_cost * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                )}
              </div>

              {items.length > 0 && (
                <table className="ing-table">
                  <thead>
                    <tr>
                      <th>Ingrediente</th>
                      <th>Qtd</th>
                      <th>Unidade</th>
                      <th>Total</th>
                      <th>Custo Novo</th>
                      <th>Custo Anterior</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map(item => (
                      <tr key={item.ingredient_id}>
                        <td style={{ fontWeight: 600 }}>{item.ing.name}</td>
                        <td>{item.quantity}</td>
                        <td>{item.unit}</td>
                        <td>{fmt(item.total_price, 2)}</td>
                        <td style={{ color: 'var(--orange)', fontWeight: 600 }}>{fmt(item.unit_cost)}/{item.ing.unit}</td>
                        <td style={{ color: 'var(--muted)' }}>{fmt(item.ing.unit_cost)}/{item.ing.unit}</td>
                        <td>
                          <button
                            type="button"
                            className="btn btn-sm btn-danger btn-icon-only"
                            onClick={() => removeItem(item.ingredient_id)}
                          >
                            ✕
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {items.length > 0 && (
                <div className="cost-box" style={{ marginTop: '1rem' }}>
                  <p className="cost-box-title">Resumo da Compra</p>
                  <div className="cost-grid">
                    <div className="cost-item">
                      <span className="cost-label">Itens</span>
                      <span className="cost-value">{items.length}</span>
                    </div>
                    <div className="cost-item">
                      <span className="cost-label">Total Gasto</span>
                      <span className="cost-value">{fmt(grandTotal, 2)}</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? '⏳ Salvando…' : '✓ Registrar Compra'}
            </button>
            <Link to="/compras" className="btn btn-ghost">Cancelar</Link>
          </div>
        </form>
      </div>
    </div>
  )
}
