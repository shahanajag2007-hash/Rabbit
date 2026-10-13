import { NavLink } from 'react-router-dom'
import { PAGES } from '../../routes'

export function TopNav() {
  return (
    <nav className="top-nav" aria-label="Dashboard pages">
      <div className="top-nav-brand">STYLEAI</div>
      {PAGES.map((page) => (
        <NavLink key={page.path} to={page.path} className={({ isActive }) => `top-link${isActive ? ' active' : ''}`}>
          {page.label}
        </NavLink>
      ))}
    </nav>
  )
}
