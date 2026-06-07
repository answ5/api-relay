import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';

export default function UserLayout({ auth, onLogout }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    onLogout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>API <span>Relay</span></h2>
          <p className="sidebar-user">
            {auth?.username}
            <span className="role-badge user">User</span>
          </p>
        </div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            概览
          </NavLink>
          <NavLink to="/keys" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            API Keys
          </NavLink>
          <NavLink to="/logs" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            使用日志
          </NavLink>
          <NavLink to="/bills" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            消费记录
          </NavLink>
        </nav>
        <div className="sidebar-footer">
          <button className="btn btn-secondary btn-sm" style={{ width: '100%' }} onClick={handleLogout}>
            退出登录
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
