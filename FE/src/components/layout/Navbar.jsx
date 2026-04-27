import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <nav className="bg-slate-900 h-13 flex items-center px-6 gap-6">
      <Link to="/dashboard" className="text-white font-bold text-base tracking-tight">
        Sales<span className="text-indigo-400">Catalyst</span>
      </Link>
      <Link to="/dashboard" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">Dashboard</Link>
      <Link to="/campaigns" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">Campaigns</Link>
      <Link to="/products" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">Products</Link>
      <Link to="/ai-drafts" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">AI Drafts</Link>
      <Link to="/inbox" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">Inbox</Link>
      <div className="ml-auto flex items-center gap-3">
        <span className="text-slate-400 text-sm">{user?.email}</span>
        <Link to="/settings" className="text-slate-400 hover:text-white text-sm font-medium transition-colors">Settings</Link>
        <button
          onClick={handleLogout}
          className="text-slate-400 hover:text-white text-sm transition-colors"
        >
          Logout
        </button>
      </div>
    </nav>
  )
}
