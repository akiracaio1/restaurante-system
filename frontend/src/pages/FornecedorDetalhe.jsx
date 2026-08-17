import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fornecedoresAPI } from '../api'

const fmt = (v) => `R$ ${Number(v).toFixed(2).replace('.', ',')}`

function fmtDate(d) {
  if (!d) return ''
  const [y, m, day] = d.split('-')
  return `${day}/${m}/${y}`
}

export default function FornecedorDetalhe() {
  const { id } = useParams()
  const [supplier, setSupplier] = useState(null)
  const [purchases, setPurchases] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  useEffect(() => {
    async function load() {
      try {
        const [{ data: s }, { data: p }] = await Promise.all([
          fornecedoresAPI.buscar(id),
          fornecedoresAPI.compras(id),
        ])
        setSupplier(s)
        setPurchases(p)
      } catch {
        setError('Erro ao carregar dados do fornecedor.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  if (loading) return <div className="loading">Carregando…</div>
  if (error) return <div className="alert alert-error">{error}</div>
  if (!supplier) return null

  const totalSpent = purchases.reduce((sum, p) => sum + p.total, 0)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">🚚 {supplier.name}</h1>
          <p className="page-subtitle">
            {purchases.length} compra{purchases.length !== 1 ? 's' : ''} registrada{purchases.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Link to="/fornecedores" className="btn btn-ghost">← Voltar</Link>
      </div>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <p className="section-title" style={{ marginTop: 0 }}>Dados do Fornecedor</p>
        <div className="cost-grid">
          {supplier.cnpj && (
            <div className="cost-item">
              <span className="cost-label">CNPJ</span>
              <span className="cost-value">{supplier.cnpj}</span>
            </div>
          )}
          {supplier.phone && (
            <div className="cost-item">
              <span className="cost-label">Telefone</span>
              <span className="cost-value">{supplier.phone}</span>
            </div>
          )}
          {supplier.email && (
            <div className="cost-item">
              <span className="cost-label">E-mail</span>
              <span className="cost-value">{supplier.email}</span>
            </div>
          )}
          {supplier.contact_name && (
            <div className="cost-item">
              <span className="cost-label">Contato</span>
              <span className="cost-value">{supplier.contact_name}</span>
            </div>
          )}
          <div className="cost-item">
            <span className="cost-label">Total gasto</span>
            <span className="cost-value" style={{ color: 'var(--orange)' }}>{fmt(totalSpent)}</span>
          </div>
        </div>
        {supplier.address && (
          <p style={{ marginTop: '.85rem', color: 'var(--muted)', fontSize: '.85rem' }}>📍 {supplier.address}</p>
        )}
        {supplier.notes && (
          <p style={{ marginTop: '.5rem', color: 'var(--muted)', fontSize: '.85rem' }}>{supplier.notes}</p>
        )}
      </div>

      <p className="section-title">Histórico de Compras</p>

      {purchases.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <span className="empty-icon">🛒</span>
            <p className="empty-text">Nenhuma compra registrada com este fornecedor</p>
            <p className="empty-sub">
              <Link to="/compras/nova" style={{ color: 'var(--orange)', fontWeight: 700 }}>
                Registre uma compra
              </Link>
            </p>
          </div>
        </div>
      ) : (
        <div className="cards-grid">
          {purchases.map(p => (
            <div key={p.id} className="ing-card">
              <div className="ing-card-header">
                <span className="ing-card-name">{fmtDate(p.date)}</span>
              </div>
              <div className="ing-card-body">
                <div className="ing-card-row">
                  <span className="ing-card-label">Itens</span>
                  <span className="ing-card-value">{p.items.length} item{p.items.length !== 1 ? 's' : ''}</span>
                </div>
                <div className="ing-card-row">
                  <span className="ing-card-label">Total gasto</span>
                  <span className="ing-card-value highlight">{fmt(p.total)}</span>
                </div>
                {p.notes && (
                  <div className="ing-card-row" style={{ marginTop: '.4rem' }}>
                    <span className="ing-card-label">Obs.</span>
                    <span className="ing-card-value" style={{ color: 'var(--muted)', fontSize: '.82rem' }}>{p.notes}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
