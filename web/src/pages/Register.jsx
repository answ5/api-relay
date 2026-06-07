import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';

export default function Register() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (!username || !password) { setError('请填写用户名和密码'); return; }
    if (password.length < 6) { setError('密码长度至少 6 位'); return; }
    setLoading(true);
    try {
      await api.post('/auth/register', { username, password, email });
      setSuccess('注册成功！正在跳转到登录页...');
      setTimeout(() => navigate('/login'), 1500);
    } catch (err) {
      setError(err.response?.data?.error?.message || err.response?.data?.detail?.error?.message || '注册失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-box">
        <h1>API <span>Relay</span> 注册</h1>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>用户名</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          </div>
          <div className="form-group">
            <label>邮箱（选填）</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="form-group">
            <label>密码</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <p style={{ color: 'var(--danger)', fontSize: '.85rem', marginBottom: 12 }}>{error}</p>}
          {success && <p style={{ color: 'var(--success)', fontSize: '.85rem', marginBottom: 12 }}>{success}</p>}
          <button className="btn btn-primary" style={{ width: '100%', padding: '10px', fontSize: '1rem' }} disabled={loading}>
            {loading ? '注册中...' : '注册'}
          </button>
        </form>
        <p style={{ textAlign: 'center', marginTop: 16, fontSize: '.85rem', color: '#888' }}>
          已有账号？<Link to="/login" style={{ color: 'var(--primary)' }}>去登录</Link>
        </p>
      </div>
    </div>
  );
}
