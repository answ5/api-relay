import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { login, me } from '../api';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!username || !password) { setError('请填写用户名和密码'); return; }
    setLoading(true);
    try {
      const res = await login(username, password);
      localStorage.setItem('token', res.data.access_token);
      const meRes = await me();
      onLogin(meRes.data);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error?.message || err.response?.data?.detail?.error?.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-box">
        <h1>
          <span className="logo-icon-sm">⚡</span>
          API <span>Relay</span>
        </h1>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>用户名</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              placeholder="请输入用户名"
            />
          </div>
          <div className="form-group">
            <label>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
            />
          </div>
          {error && <p style={{
            background: 'var(--danger-light)',
            color: 'var(--danger)',
            padding: '8px 12px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '.85rem',
            marginBottom: 14,
            border: '1px solid #fecaca',
          }}>{error}</p>}
          <button
            className="btn btn-primary btn-lg"
            style={{ width: '100%', padding: '11px' }}
            disabled={loading}
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
        <p style={{ textAlign: 'center', marginTop: 18, fontSize: '.85rem', color: 'var(--text2)' }}>
          <Link to="/" style={{ color: '#818cf8', textDecoration: 'none' }}>← 返回首页</Link>
        </p>
        <p style={{ textAlign: 'center', marginTop: 8, fontSize: '.85rem', color: 'var(--text2)' }}>
          没有账号？<Link to="/register">立即注册</Link>
          <span style={{ margin: '0 8px', color: 'var(--border)' }}>|</span>
          <Link to="/forgot-password">忘记密码</Link>
        </p>
      </div>
    </div>
  );
}
