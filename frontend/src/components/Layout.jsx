import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import {
  LayoutDashboard,
  Briefcase,
  FileText,
  User,
  LogOut,
  Menu,
  X,
  Bell,
  Search,
  Sparkles,
} from 'lucide-react';

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = React.useState(false);
  const [unreadCount, setUnreadCount] = React.useState(0);
  const [search, setSearch] = React.useState('');

  const submitSearch = (e) => {
    e.preventDefault();
    const query = search.trim();
    navigate(query ? `/jobs?search=${encodeURIComponent(query)}` : '/jobs');
  };

  React.useEffect(() => {
    if (!user) {
      setUnreadCount(0);
      return;
    }
    apiService.notifications
      .list({ read: false })
      .then((res) => setUnreadCount((res.data.results || res.data).length))
      .catch(() => setUnreadCount(0));
  }, [user]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/jobs', label: 'Jobs', icon: Briefcase },
    { path: '/assistant', label: 'AI Assistant', icon: Sparkles },
    { path: '/applications', label: 'Applications', icon: FileText },
    { path: '/profile', label: 'Profile', icon: User },
  ];

  return (
    <div className="layout">
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="logo">
            <span className="logo-icon">AI</span>
            <span className="logo-text">Career Copilot</span>
          </div>
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(false)}>
            <X size={20} />
          </button>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              <Icon size={20} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="nav-item logout" onClick={handleLogout}>
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      <div className="main-wrapper">
        <header className="topbar">
          <button className="menu-toggle" onClick={() => setSidebarOpen(true)}>
            <Menu size={24} />
          </button>
          <div className="topbar-actions">
            <form className="search-box" onSubmit={submitSearch} role="search">
              <Search size={18} />
              <input
                type="text"
                placeholder="Search jobs, skills..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Search jobs"
              />
            </form>
            <div
              className="notification-bell"
              onClick={() => navigate('/notifications')}
              role="button"
              title="Notifications"
            >
              <Bell size={22} />
              {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
            </div>
            <div className="user-menu">
              <div className="user-avatar">
                {user?.name?.charAt(0).toUpperCase() || 'U'}
              </div>
              <span className="user-name">{user?.name || 'User'}</span>
            </div>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>

      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
    </div>
  );
}