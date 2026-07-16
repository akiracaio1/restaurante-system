import { Link } from 'react-router-dom'

export const fmt    = (v) => `R$ ${Number(v).toFixed(2).replace('.', ',')}`
export const fmtPct = (v) => `${Number(v).toFixed(1)}%`

export const CAT_ICON = {
  'prato principal': '🍽️',
  'sobremesa':       '🍰',
  'bebida':          '🥤',
  'entrada':         '🥗',
  'petisco':         '🍟',
  'outro':           '📦',
}

export const CAT_CLASS = {
  'prato principal': 'cat-prato-principal',
  'sobremesa':       'cat-sobremesa',
  'bebida':          'cat-bebida',
  'entrada':         'cat-entrada',
  'petisco':         'cat-petisco',
  'outro':           'cat-outro',
}

export function cmvBadgeClass(v) {
  if (v <= 30) return 'badge-green'
  if (v <= 35) return 'badge-orange'
  if (v <= 40) return 'badge-warning'
  return 'badge-red'
}

export function cmvTextClass(v) {
  if (v <= 30) return 'cmv-good-text'
  if (v <= 35) return 'cmv-ok-text'
  if (v <= 40) return 'cmv-warn-text'
  return 'cmv-bad-text'
}

export function cmvLabel(v) {
  if (v <= 30) return 'Excelente'
  if (v <= 35) return 'Aceitável'
  if (v <= 40) return 'Atenção'
  return 'Alto'
}

export default function RecipeCard({ item, editHref, onDelete }) {
  return (
    <div className="recipe-card">
      <div className="recipe-card-header">
        <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <span className={`cat-badge ${CAT_CLASS[item.category] || 'cat-outro'}`}>
            {CAT_ICON[item.category] || '📦'} {item.category}
          </span>
          {item.sub_recipes && item.sub_recipes.length > 0 && (
            <span className="badge" style={{ background: 'var(--orange)', color: '#fff', fontSize: '.7rem' }}>
              🔗 {item.sub_recipes.length} sub-receita{item.sub_recipes.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div className="recipe-card-name">{item.name}</div>
        {item.description && (
          <div className="recipe-card-desc">{item.description}</div>
        )}
      </div>

      <div className={`recipe-card-cmv ${cmvTextClass(item.cmv_percent)}`}>
        <div className="recipe-card-cmv-value">{fmtPct(item.cmv_percent)}</div>
        <div className="recipe-card-cmv-label">CMV — {cmvLabel(item.cmv_percent)}</div>
        <span className={`badge ${cmvBadgeClass(item.cmv_percent)}`} style={{ marginTop: '.2rem' }}>
          {item.cmv_percent <= 30 ? '🟢' : item.cmv_percent <= 35 ? '🟡' : item.cmv_percent <= 40 ? '🟠' : '🔴'}
          &nbsp;{cmvLabel(item.cmv_percent)}
        </span>
      </div>

      <div className="recipe-card-body">
        <div className="recipe-card-row">
          <span className="recipe-card-label">Preço de venda</span>
          <span className="recipe-card-value recipe-card-price">{fmt(item.sale_price)}</span>
        </div>
        <div className="recipe-card-row">
          <span className="recipe-card-label">Custo total</span>
          <span className="recipe-card-value">{fmt(item.total_cost)}</span>
        </div>
        <div className="recipe-card-row">
          <span className="recipe-card-label">Rendimento</span>
          <span className="recipe-card-value">
            {item.yield_portions} {item.yield_portions === 1 ? 'porção' : 'porções'}
          </span>
        </div>
        <div className="recipe-card-row">
          <span className="recipe-card-label">Custo/porção</span>
          <span className="recipe-card-value">{fmt(item.total_cost / item.yield_portions)}</span>
        </div>
      </div>

      <div className="recipe-card-actions">
        <Link to={editHref} className="btn btn-sm btn-outline">
          Editar
        </Link>
        <button
          className="btn btn-sm btn-danger"
          onClick={() => onDelete(item.id, item.name)}
        >
          Excluir
        </button>
      </div>
    </div>
  )
}
