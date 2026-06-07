import React, { useState, useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { me } from './api';
import Login from './pages/Login';
import Register from './pages/Register';

// Admin pages
import AdminLayout from './pages/Layout';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Tokens from './pages/Tokens';
import Channels from './pages/Channels';
import ModelPricing from './pages/ModelPricing';
import Logs from './pages/Logs';
import Transactions from './pages/Transactions';

// User pages
import UserLayout from './pages/user/Layout';
import UserDashboard from './pages/user/Dashboard';
import UserKeys from './pages/user/Keys';
import UserLogs from './pages/user/Logs';
import UserBills from './pages/user/Bills';

export default function App() {
  const [auth, setAuth] = useState(null); // { id, username, role } | null
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) { setLoading(false); return; }
    me()
      .then((res) => setAuth(res.data))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">加载中...</div>;
  const isAdmin = auth?.role === 'admin' || auth?.role === 'super_admin';

  return (
    <HashRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={auth ? <Navigate to="/" /> : <Login onLogin={setAuth} />} />
        <Route path="/register" element={auth ? <Navigate to="/" /> : <Register />} />

        {/* Admin routes */}
        {isAdmin && (
          <Route path="/" element={<AdminLayout auth={auth} onLogout={() => { localStorage.removeItem('token'); setAuth(null); }} />}>
            <Route index element={<Dashboard />} />
            <Route path="users" element={<Users />} />
            <Route path="tokens" element={<Tokens />} />
            <Route path="channels" element={<Channels />} />
            <Route path="models" element={<ModelPricing />} />
            <Route path="logs" element={<Logs />} />
            <Route path="transactions" element={<Transactions />} />
          </Route>
        )}

        {/* User routes */}
        {!isAdmin && auth && (
          <Route path="/" element={<UserLayout auth={auth} onLogout={() => { localStorage.removeItem('token'); setAuth(null); }} />}>
            <Route index element={<UserDashboard />} />
            <Route path="keys" element={<UserKeys />} />
            <Route path="logs" element={<UserLogs />} />
            <Route path="bills" element={<UserBills />} />
          </Route>
        )}

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </HashRouter>
  );
}
