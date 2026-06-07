import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';

const nav = [
  { path: '/', label: '📊 仪表盘' },
  { path: '/users', label: '👥 用户管理' },
  { path: '/tokens', label: '🔑 Token 管理' },
  { path: '/channels', label: '🔗 渠道管理' },
  { path: '/models', label: '💰 模型定价' },
  { path: '/logs', label: '📋 请求日志' },
  { path: '/transactions', label: '💳 交易记录' },
];

export default function Layout({ auth, onLogout }) {
  return (
    <div className="layout">
      <div className="sidebar">
        <div className="logo">API <span>Relay</span></div>
        <nav>
          {nav.map(({ path, label }) => (
            <NavLink key={path} to={path} end={path === '/'} className={({ isActive }) => isActive ? 'active' : ''}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="user-info">
          <div>{auth?.username} ({auth?.role})</div>
          <button onClick={onLogout}>退出登录</button>
        </div>
      </div>
      <div className="main">
        <div className="topbar" style={{ display: 'none' }}></div>
        <div className="content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
