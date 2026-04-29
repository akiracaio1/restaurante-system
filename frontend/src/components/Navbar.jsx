import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <nav className="navbar">
      <NavLink to="/" className="navbar-brand">
        <span className="brand-icon">🍽️</span>
        <span className="brand-name">RestaurantePro</span>
      </NavLink>

      <div className="navbar-links">
        <NavLink
          to="/ingredientes"
          className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
        >
          Ingredientes
        </NavLink>
        <NavLink
          to="/receitas"
          className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}
        >
          Receitas
        </NavLink>
        <button className="nav-link nav-logout" onClick={handleLogout}>
          Sair
        </button>
      </div>
    </nav>
  )
}
