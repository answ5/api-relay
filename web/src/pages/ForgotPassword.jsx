import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { forgotPassword } from '../api';

export default function ForgotPassword() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setResult(null);
    if (!username && !email) { setError('请输入用户名或邮箱'); return; }
    setLoading(true);
    try {
      const res = await forgotPassword({ username, email });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail?.error?.message || err.response?.data?.error?.message || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-box">
        <h1>
          <span className="logo-icon-sm">🔑</span>
          忘记密码
        </h1>
        {!result ? (
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>用户名</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="输入用户名（选填）"
                autoFocus
              />
            </div>
            <div className="form-group">
              <label>或邮箱</label>
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="输入注册邮箱（选填）"
              />
            </div>
            {error && <p className="login-error">{error}</p>}
            <button
              className="btn btn-primary btn-lg"
              style={{ width: '100%', padding: '11px' }}
              disabled={loading}
            >
              {loading ? '请求中...' : '获取重置令牌'}
            </button>
          </form>
        ) : (
          <div>
            <p style={{ marginBottom: 12, color: 'var(--success)', fontWeight: 600 }}>
              {result.message}
            </p>
            {result.reset_token && (
              <div>
                <p style={{ fontSize: '.85rem', color: 'var(--text2)', marginBottom: 8 }}>
                  复制下方的令牌，然后在重置密码页面使用：
                </p>
                <div style={{
                  background: '#f8fafc', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)', padding: 12, marginBottom: 14,
                  fontSize: '.75rem', wordBreak: 'break-all', fontFamily: 'monospace'
                }}>
                  {result.reset_token}
                </div>
                <button className="btn btn-primary" style={{ width: '100%', marginBottom: 8 }}
                  onClick={() => {
                    navigator.clipboard.writeText(result.reset_token);
                    navigate(`/reset-password?token=${encodeURIComponent(result.reset_token)}`);
                  }}>
                  去重置密码
                </button>
              </div>
            )}
            {!result.reset_token && (
              <p style={{ marginTop: 12, fontSize: '.85rem', color: 'var(--text2)' }}>
                如果该用户存在，重置令牌已生成。请联系管理员手动重置。
              </p>
            )}
          </div>
        )}
        <p style={{ textAlign: 'center', marginTop: 18, fontSize: '.85rem', color: 'var(--text2)' }}>
          想起密码了？<Link to="/login">返回登录</Link>
        </p>
      </div>
    </div>
  );
}
