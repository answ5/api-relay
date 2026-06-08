import React, { useState, useEffect } from 'react';
import api, { userMe } from '../../api';

const AMOUNTS = [10, 20, 50, 100, 200, 500];
const CHANNELS = [
  { key: 'alipay', label: '支付宝', icon: '💙' },
  { key: 'wxpay', label: '微信支付', icon: '💚' },
];

export default function UserRecharge() {
  const [tab, setTab] = useState('online'); // online | code
  const [code, setCode] = useState('');
  const [amount, setAmount] = useState(50);
  const [customAmount, setCustomAmount] = useState('');
  const [channel, setChannel] = useState('alipay');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [balance, setBalance] = useState(null);

  useEffect(() => {
    userMe().then((res) => setBalance(res.data?.balance)).catch(() => {});
  }, []);

  // ── Redeem code ──
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
      if (res.data?.data?.new_balance != null) setBalance(res.data.data.new_balance);
    } catch (err) {
      const msg = err.response?.data?.error?.message || err.response?.data?.detail?.error?.message || '兑换失败';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // ── Online payment ──
  const handlePay = async () => {
    setError('');
    setResult(null);
    const finalAmount = customAmount ? parseFloat(customAmount) : amount;
    if (!finalAmount || finalAmount <= 0) { setError('请选择或输入有效金额'); return; }
    setLoading(true);
    try {
      const res = await api.post('/recharge/create', {
        amount: finalAmount,
        channel,
      });
      const data = res.data?.data;
      if (data?.pay_url) {
        window.open(data.pay_url, '_blank');
      }
      setResult({ ...data, from_online: true });
    } catch (err) {
      const msg = err.response?.data?.error?.message || err.response?.data?.detail?.error?.message || '创建订单失败';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">充值中心</h2>

      {/* Balance display */}
      {balance != null && (
        <div className="user-balance-card" style={{ marginBottom: 20 }}>
          <div>
            <div className="user-balance-label">账户余额</div>
            <div className="user-balance-amount">¥{parseFloat(balance).toFixed(4)}</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 20, borderBottom: '2px solid var(--border)' }}>
        {[
          { key: 'online', label: '在线支付' },
          { key: 'code', label: '充值码兑换' },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setError(''); setResult(null); }}
            style={{
              padding: '10px 24px',
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              fontSize: '.95rem',
              fontWeight: tab === t.key ? 600 : 400,
              color: tab === t.key ? 'var(--accent)' : 'var(--text2)',
              borderBottom: tab === t.key ? '2px solid var(--accent)' : '2px solid transparent',
              marginBottom: -2,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── Online payment tab ── */}
      {tab === 'online' && (
        <div className="user-card" style={{ maxWidth: 520 }}>
          {/* Amount selector */}
          <div className="form-group">
            <label>充值金额</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
              {AMOUNTS.map((a) => (
                <button
                  key={a}
                  onClick={() => { setAmount(a); setCustomAmount(''); }}
                  style={{
                    padding: '8px 18px',
                    border: `2px solid ${amount === a && !customAmount ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius-sm)',
                    background: amount === a && !customAmount ? '#eef2ff' : '#fff',
                    color: amount === a && !customAmount ? 'var(--accent)' : 'var(--text)',
                    fontWeight: 500,
                    cursor: 'pointer',
                    fontSize: '.95rem',
                  }}
                >
                  ¥{a}
                </button>
              ))}
              <input
                type="number"
                placeholder="自定义金额"
                value={customAmount}
                onChange={(e) => { setCustomAmount(e.target.value); setAmount(0); }}
                style={{
                  width: 120,
                  padding: '8px 12px',
                  border: `2px solid ${customAmount ? 'var(--accent)' : 'var(--border)'}`,
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '.95rem',
                }}
                min="1"
                step="1"
              />
            </div>
          </div>

          {/* Bonus hint */}
          {(amount || customAmount) && (
            <div style={{
              background: '#fffbeb', color: '#92400e',
              padding: '8px 12px', borderRadius: 'var(--radius-sm)',
              fontSize: '.82rem', marginBottom: 14,
              border: '1px solid #fde68a',
            }}>
              🎁 充值 ¥{amount >= 1000 ? '1000+' : amount >= 500 ? '500+' : amount >= 200 ? '200+' : amount >= 100 ? '100+' : '0+'}
              赠送 ¥{amount >= 1000 ? 120 : amount >= 500 ? 50 : amount >= 200 ? 15 : amount >= 100 ? 5 : 0}
            </div>
          )}

          {/* Payment channel */}
          <div className="form-group">
            <label>支付方式</label>
            <div style={{ display: 'flex', gap: 10 }}>
              {CHANNELS.map((ch) => (
                <button
                  key={ch.key}
                  onClick={() => setChannel(ch.key)}
                  style={{
                    flex: 1,
                    padding: '12px',
                    border: `2px solid ${channel === ch.key ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius-sm)',
                    background: channel === ch.key ? '#eef2ff' : '#fff',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    textAlign: 'center',
                  }}
                >
                  {ch.icon} {ch.label}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <p style={{
              background: 'var(--danger-light)', color: 'var(--danger)',
              padding: '8px 12px', borderRadius: 'var(--radius-sm)',
              fontSize: '.85rem', marginBottom: 14, border: '1px solid #fecaca',
            }}>{error}</p>
          )}

          {result?.from_online && (
            <div style={{
              background: '#f0fdf4', color: '#166534',
              padding: '14px', borderRadius: 'var(--radius-sm)',
              marginBottom: 14, border: '1px solid #bbf7d0',
            }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: 6 }}>
                ✅ 订单已创建！
              </div>
              <div style={{ fontSize: '.85rem' }}>
                订单号：#{result.order_id}<br />
                充值金额：¥{result.amount.toFixed(2)}<br />
                赠送金额：¥{result.bonus.toFixed(2)}<br />
                到账总额：¥{result.total.toFixed(2)}<br />
                {result.pay_url && (
                  <a href={result.pay_url} target="_blank" rel="noreferrer"
                    style={{ color: '#166534', fontWeight: 600, textDecoration: 'underline' }}>
                    如未自动跳转，请点击这里前往支付 →
                  </a>
                )}
              </div>
            </div>
          )}

          <button
            className="btn btn-success btn-lg"
            style={{ width: '100%', padding: '12px', fontSize: '1rem' }}
            disabled={loading}
            onClick={handlePay}
          >
            {loading ? '创建订单中...' : '💳 立即支付'}
          </button>
        </div>
      )}

      {/* ── Code redeem tab ── */}
      {tab === 'code' && (
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

            {result && !result.from_online && (
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
      )}
    </div>
  );
}