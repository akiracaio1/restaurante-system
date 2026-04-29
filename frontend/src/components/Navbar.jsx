import { NavLink } from 'react-router-dom'

export default function Navbar() {
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
      </div>
    </nav>
  )
}
