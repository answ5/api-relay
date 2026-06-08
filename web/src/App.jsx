import React, { useState, useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { me } from './api';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';

// Admin pages
import AdminLayout from './pages/Layout';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Tokens from './pages/Tokens';
import Channels from './pages/Channels';
import ModelPricing from './pages/ModelPricing';
import Logs from './pages/Logs';
import Transactions from './pages/Transactions';
import TestChat from './pages/TestChat';
import Settings from './pages/Settings';
import PluginManager from './pages/PluginManager';
import Home from './pages/Home';

// User pages
import UserLayout from './pages/user/Layout';
import UserDashboard from './pages/user/Dashboard';
import UserKeys from './pages/user/Keys';
import UserLogs from './pages/user/Logs';
import UserBills from './pages/user/Bills';
import UserRecharge from './pages/user/Recharge';

// Public pages
import ModelMarket from './pages/ModelMarket';

function ProtectedRoute({ auth, children }) {
  if (!auth) return <Navigate to="/login" replace />;
  return children;
}

function AdminRoute({ auth, children }) {
  const isAdmin = auth?.role === 'admin' || auth?.role === 'super_admin';
  if (!auth) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/" replace />;
  return children;
}

function UserRoute({ auth, children }) {
  const isAdmin = auth?.role === 'admin' || auth?.role === 'super_admin';
  if (!auth) return <Navigate to="/login" replace />;
  if (isAdmin) return <Navigate to="/" replace />;
  return children;
}

function AppLoading() {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      height: '100vh', gap: 16,
      background: '#f0f2f6',
    }}>
      <div style={{
        width: 36, height: 36,
        border: '3px solid #e2e8f0',
        borderTopColor: '#6366f1',
        borderRadius: '50%',
        animation: 'spin .6s linear infinite',
      }} />
      <span style={{ color: '#64748b', fontSize: '.9rem' }}>加载中...</span>
    </div>
  );
}

export default function App() {
  const [auth, setAuth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setLoading(false); return; }
    me()
      .then((res) => setAuth(res.data))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <AppLoading />;

  const isAdmin = auth?.role === 'admin' || auth?.role === 'super_admin';

  return (
    <HashRouter>
      <Routes>
        {/* Public routes (no auth needed) */}
        <Route path="/" element={auth ? <Navigate to="/dashboard" replace /> : <Home />} />
        <Route path="/home" element={auth ? <Navigate to="/dashboard" replace /> : <Home />} />
        <Route path="/login" element={auth ? <Navigate to="/dashboard" replace /> : <Login onLogin={setAuth} />} />
        <Route path="/register" element={auth ? <Navigate to="/dashboard" replace /> : <Register />} />
        <Route path="/forgot-password" element={auth ? <Navigate to="/dashboard" replace /> : <ForgotPassword />} />
        <Route path="/reset-password" element={auth ? <Navigate to="/dashboard" replace /> : <ResetPassword />} />
        <Route path="/market" element={<ModelMarket />} />

        {/* Authenticated layout */}
        <Route path="/" element={
          <ProtectedRoute auth={auth}>
            {isAdmin
              ? <AdminLayout auth={auth} onLogout={() => { localStorage.removeItem('token'); setAuth(null); }} />
              : <UserLayout auth={auth} onLogout={() => { localStorage.removeItem('token'); setAuth(null); }} />
            }
          </ProtectedRoute>
        }>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={isAdmin ? <Dashboard /> : <UserDashboard />} />
          <Route path="users" element={<AdminRoute auth={auth}><Users /></AdminRoute>} />
          <Route path="tokens" element={<AdminRoute auth={auth}><Tokens /></AdminRoute>} />
          <Route path="channels" element={<AdminRoute auth={auth}><Channels /></AdminRoute>} />
          <Route path="models" element={<AdminRoute auth={auth}><ModelPricing /></AdminRoute>} />
          <Route path="transactions" element={<AdminRoute auth={auth}><Transactions /></AdminRoute>} />
          <Route path="chat-test" element={<AdminRoute auth={auth}><TestChat /></AdminRoute>} />
          <Route path="settings" element={<AdminRoute auth={auth}><Settings /></AdminRoute>} />
          <Route path="plugins" element={<AdminRoute auth={auth}><PluginManager /></AdminRoute>} />
          {/* Shared pages */}
          <Route path="logs" element={
            isAdmin ? <Logs /> : <UserLogs />
          } />
          {/* User-only pages */}
          <Route path="keys" element={<UserRoute auth={auth}><UserKeys /></UserRoute>} />
          <Route path="bills" element={<UserRoute auth={auth}><UserBills /></UserRoute>} />
          <Route path="recharge" element={<UserRoute auth={auth}><UserRecharge /></UserRoute>} />
          {/* Model marketplace (accessible when logged in too) */}
          <Route path="market" element={<ModelMarket />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </HashRouter>
  );
}