import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { resetPassword } from '../api';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState(searchParams.get('token') || '');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const cleanedToken = token.trim();
    if (!cleanedToken) { setError('请输入重置令牌'); return; }
    if (password.length < 6) { setError('密码长度至少 6 位'); return; }
    if (password !== confirm) { setError('两次密码输入不一致'); return; }
    setLoading(true);
    try {
      await resetPassword({ token: cleanedToken, password });
      setDone(true);
    } catch (err) {
      setError(err.response?.data?.detail?.error?.message || '重置失败，令牌可能已过期或用过，请重新获取');
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <div className="login-page">
        <div className="login-box">
          <h1>
            <span className="logo-icon-sm">✅</span>
            密码重置成功
          </h1>
          <p style={{ color: 'var(--success)', fontWeight: 600, marginBottom: 16 }}>
            请使用新密码登录。
          </p>
          <button
            className="btn btn-primary btn-lg"
            style={{ width: '100%', padding: '11px' }}
            onClick={() => navigate('/login')}
          >
            返回登录
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="login-page">
      <div className="login-box" style={{ maxWidth: 440 }}>
        <h1>
          <span className="logo-icon-sm">🔄</span>
          重置密码
        </h1>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>重置令牌</label>
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="粘贴从忘记密码页面获取的令牌"
              autoFocus
              style={{ fontFamily: 'monospace', fontSize: '.82rem' }}
            />
            <p style={{ fontSize: '.75rem', color: 'var(--text2)', marginTop: 4 }}>
              请完整复制令牌，不要包含空格
            </p>
          </div>
          <div className="form-group">
            <label>新密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="至少 6 位"
            />
          </div>
          <div className="form-group">
            <label>确认密码</label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="再次输入新密码"
            />
          </div>
          {error && <p className="login-error">{error}</p>}
          <button
            className="btn btn-primary btn-lg"
            style={{ width: '100%', padding: '11px' }}
            disabled={loading}
          >
            {loading ? '重置中...' : '重置密码'}
          </button>
        </form>
        <p style={{ textAlign: 'center', marginTop: 18, fontSize: '.85rem', color: 'var(--text2)' }}>
          <Link to="/forgot-password">重新获取令牌</Link> | <Link to="/login">返回登录</Link>
        </p>
      </div>
    </div>
  );
}
