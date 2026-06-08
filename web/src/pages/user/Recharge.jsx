import React, { useState } from 'react';
import api from '../../api';

export default function UserRecharge() {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleRedeem = async (e) => {
    e.preventDefault();
    setError('');
    setResult(null);
    if (!code.trim()) { setError('请输入充值码'); return; }
    setLoading(true);
    try {
      const res = await api.post('/recharge/redeem', { code: code.trim() });
      setResult(res.data?.data);
      setCode('');
    } catch (err) {
      const msg = err.response?.data?.error?.message || err.response?.data?.detail?.error?.message || '兑换失败';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">充值中心</h2>

      <div className="user-card" style={{ maxWidth: 500 }}>
        <p style={{ color: 'var(--text2)', marginBottom: 20, fontSize: '.9rem' }}>
          在下方输入充值码即可为您的账户增加余额
        </p>

        <form onSubmit={handleRedeem}>
          <div className="form-group">
            <label>充值码</label>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="请输入充值码"
              autoFocus
              style={{ fontFamily: 'monospace', letterSpacing: 2 }}
            />
          </div>

          {error && (
            <p style={{
              background: 'var(--danger-light)', color: 'var(--danger)',
              padding: '8px 12px', borderRadius: 'var(--radius-sm)',
              fontSize: '.85rem', marginBottom: 14, border: '1px solid #fecaca',
            }}>{error}</p>
          )}

          {result && (
            <div style={{
              background: '#f0fdf4', color: '#166534',
              padding: '14px', borderRadius: 'var(--radius-sm)',
              marginBottom: 14, border: '1px solid #bbf7d0',
            }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 6 }}>
                ✅ 充值成功！+¥{result.amount.toFixed(4)}
              </div>
              <div style={{ fontSize: '.82rem', color: '#15803d' }}>
                充值前余额：¥{result.previous_balance.toFixed(4)}<br />
                当前余额：¥{result.new_balance.toFixed(4)}
              </div>
            </div>
          )}

          <button
            className="btn btn-success btn-lg"
            style={{ width: '100%', padding: '11px' }}
            disabled={loading}
          >
            {loading ? '兑换中...' : '立即兑换'}
          </button>
        </form>
      </div>
    </div>
  );
}
