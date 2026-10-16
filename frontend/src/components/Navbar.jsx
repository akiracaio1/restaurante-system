import { useState, useRef, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { logout, email, isMaster } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const dropRef = useRef(null)

  const initials = email
    ? email.split('@')[0].slice(0, 2).toUpperCase()
    : 'US'

  useEffect(() => {
    function onClickOutside(e) {
      if (dropRef.current && !dropRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <nav className="navbar">
      <NavLink to={isMaster ? '/' : '/receitas'} className="navbar-brand">
        <span className="brand-icon">🍽️</span>
        <span className="brand-name">
          Restaurante<span className="brand-accent">Pro</span>
        </span>
      </NavLink>

      <div className="navbar-links">
        {isMaster && (
          <NavLink
            to="/"
            end
            className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
          >
            🏠 <span className="nav-link-text">Dashboard</span>
          </NavLink>
        )}
        <NavLink
          to="/ingredientes"
          className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
        >
          🥬 <span className="nav-link-text">Ingredientes</span>
        </NavLink>
        <NavLink
          to="/receitas"
          className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
        >
          🍽️ <span className="nav-link-text">Receitas</span>
        </NavLink>
        {isMaster && (
          <>
            <NavLink
              to="/compras"
              className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
            >
              🛒 <span className="nav-link-text">Compras</span>
            </NavLink>
            <NavLink
              to="/estoque"
              className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
            >
              📦 <span className="nav-link-text">Estoque</span>
            </NavLink>
            <NavLink
              to="/usuarios"
              className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
            >
              👥 <span className="nav-link-text">Usuários</span>
            </NavLink>
          </>
        )}
      </div>

      <div className="nav-user" ref={dropRef}>
        <button className="nav-avatar" onClick={() => setOpen(v => !v)} aria-label="Menu do usuário">
          {initials}
        </button>
        {open && (
          <div className="nav-dropdown">
            <div className="nav-dropdown-email">👤 {email || 'Usuário'}</div>
            <div className="nav-dropdown-email" style={{ fontSize: '.75rem', opacity: .8 }}>
              Perfil: {isMaster ? 'Master' : 'Operação'}
            </div>
            <hr className="nav-dropdown-divider" />
            <button className="nav-dropdown-item" onClick={handleLogout}>
              Sair
            </button>
          </div>
        )}
      </div>
    </nav>
  )
}
