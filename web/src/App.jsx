import React, { useState, useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { me } from './api';
import Login from './pages/Login';
import Layout from './pages/Layout';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Tokens from './pages/Tokens';
import Channels from './pages/Channels';
import ModelPricing from './pages/ModelPricing';
import Logs from './pages/Logs';
import Transactions from './pages/Transactions';

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

  return (
    <HashRouter>
      <Routes>
        <Route path="/login" element={auth ? <Navigate to="/" /> : <Login onLogin={setAuth} />} />
        <Route path="/" element={auth ? <Layout auth={auth} onLogout={() => { localStorage.removeItem('token'); setAuth(null); }} /> : <Navigate to="/login" />}>
          <Route index element={<Dashboard />} />
          <Route path="users" element={<Users />} />
          <Route path="tokens" element={<Tokens />} />
          <Route path="channels" element={<Channels />} />
          <Route path="models" element={<ModelPricing />} />
          <Route path="logs" element={<Logs />} />
          <Route path="transactions" element={<Transactions />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}
