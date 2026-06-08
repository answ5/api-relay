import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';

export default function UserLayout({ auth, onLogout }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    onLogout();
    navigate('/login');
  };

  return (
    <div className="user-layout">
      <header className="user-header">
        <div className="user-header-inner">
          <div className="user-brand">
            <div className="user-logo">⚡</div>
            <span className="user-brand-text">API Relay</span>
          </div>

          <nav className="user-nav">
            <NavLink to="/" end className={({ isActive }) => isActive ? 'user-nav-item active' : 'user-nav-item'}>
              概览
            </NavLink>
            <NavLink to="/keys" className={({ isActive }) => isActive ? 'user-nav-item active' : 'user-nav-item'}>
              API Keys
            </NavLink>
            <NavLink to="/logs" className={({ isActive }) => isActive ? 'user-nav-item active' : 'user-nav-item'}>
              使用日志
            </NavLink>
            <NavLink to="/bills" className={({ isActive }) => isActive ? 'user-nav-item active' : 'user-nav-item'}>
              消费记录
            </NavLink>
          </nav>

          <div className="user-header-right">
            <span className="user-header-role">{auth?.role === 'admin' || auth?.role === 'super_admin' ? '管理员' : '用户'}</span>
            <span className="user-header-name">{auth?.username}</span>
            <button className="user-logout-btn" onClick={handleLogout} title="退出登录">
              退出
            </button>
          </div>
        </div>
      </header>

      <main className="user-main">
        <Outlet />
      </main>
    </div>
  );
}
