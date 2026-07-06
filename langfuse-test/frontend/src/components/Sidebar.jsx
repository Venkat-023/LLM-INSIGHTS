import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/chat',       icon: '💬', label: 'Chat' },
  { to: '/dashboard',  icon: '📊', label: 'Dashboard' },
  { to: '/experiment', icon: '🧪', label: 'Experiment' },
  { to: '/analytics',  icon: '📈', label: 'Analytics' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🔭</div>
        <span className="sidebar-logo-text">Langfuse AI</span>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `sidebar-nav-item${isActive ? ' active' : ''}`
            }
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div style={{ marginBottom: 4 }}>🔗 Langfuse observability</div>
        <a href="https://cloud.langfuse.com" target="_blank" rel="noopener">
          Open Langfuse Dashboard ↗
        </a>
      </div>
    </aside>
  )
}
