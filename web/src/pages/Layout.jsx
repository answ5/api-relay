import React, { useState } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';

const sections = [
  { label: '管理', items: [
    { path: '/', label: '仪表盘', icon: '📊' },
    { path: '/users', label: '用户管理', icon: '👥' },
    { path: '/tokens', label: 'Token 管理', icon: '🔑' },
    { path: '/channels', label: '渠道管理', icon: '🔗' },
    { path: '/models', label: '模型定价', icon: '💰' },
  ]},
  { label: '数据', items: [
    { path: '/logs', label: '请求日志', icon: '📋' },
    { path: '/transactions', label: '交易记录', icon: '💳' },
  ]},
  { label: '工具', items: [
    { path: '/chat-test', label: '在线测试', icon: '🧪' },
  ]},
];

const pageTitles = {};
sections.forEach(s => s.items.forEach(i => { pageTitles[i.path] = i.label; }));

export default function Layout({ auth, onLogout }) {
  const location = useLocation();
  const pageTitle = pageTitles[location.pathname] || '仪表盘';

  return (
    <div className="layout">
      <div className="sidebar">
        <div className="logo">
          <div className="logo-icon">⚡</div>
          <span>API Relay</span>
        </div>
        <nav>
          {sections.map((section, si) => (
            <React.Fragment key={si}>
              <div className="sidebar-section" style={si > 0 ? { marginTop: 8 } : {}}>{section.label}</div>
              {section.items.map(({ path, label, icon }) => (
                <NavLink key={path} to={path} end={path === '/'} className={({ isActive }) => isActive ? 'active' : ''}>
                  <span className="nav-icon">{icon}</span> {label}
                </NavLink>
              ))}
            </React.Fragment>
          ))}
        </nav>
        <div className="user-info">
          <div className="user-name">{auth?.username}</div>
          <div>{auth?.role === 'super_admin' ? '超级管理员' : auth?.role === 'admin' ? '管理员' : '用户'}</div>
          <button onClick={onLogout}>退出登录</button>
        </div>
      </div>
      <div className="main">
        <div className="topbar">
          <div className="topbar-left">
            <div className="breadcrumb">
              API Relay <span>/</span> <span>{pageTitle}</span>
            </div>
          </div>
        </div>
        <div className="content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
