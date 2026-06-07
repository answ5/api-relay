import React, { useState, useEffect } from 'react';
import { userDashboardStats, userMe } from '../../api';

export default function UserDashboard() {
  const [stats, setStats] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([userDashboardStats(), userMe()])
      .then(([statsRes, meRes]) => {
        setStats(statsRes.data.data);
        setProfile(meRes.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">加载中...</div>;

  const summary = stats?.summary || {};
  const modelUsage = stats?.model_usage || [];

  return (
    <div className="dashboard">
      <h2 className="page-title">我的概览</h2>

      <div className="balance-card" style={{
        background: 'linear-gradient(135deg, var(--primary), #7c3aed)',
        borderRadius: 12, padding: '24px 32px', color: '#fff', marginBottom: 24,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: '.85rem', opacity: .8 }}>账户余额</div>
          <div style={{ fontSize: '2rem', fontWeight: 700 }}>
            ¥{parseFloat(profile?.balance || 0).toFixed(4)}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '.85rem', opacity: .8 }}>累计消费</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 600 }}>
            ¥{parseFloat(summary.total_spent || 0).toFixed(4)}
          </div>
        </div>
      </div>

      <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16, marginBottom: 24 }}>
        {[
          { label: '今日请求', value: summary.today_requests || 0 },
          { label: '今日消耗 Tokens', value: (summary.today_tokens || 0).toLocaleString() },
          { label: '今日消费', value: `¥${(summary.today_cost || 0).toFixed(4)}` },
          { label: '成功率', value: `${summary.success_rate || 100}%` },
          { label: '有效 API Keys', value: summary.active_tokens || 0 },
          { label: '累计 Tokens', value: (summary.total_tokens_all_time || 0).toLocaleString() },
        ].map((item, i) => (
          <div key={i} className="stat-card" style={{
            background: 'var(--card-bg)', borderRadius: 10, padding: '16px 20px',
            border: '1px solid var(--border)',
          }}>
            <div style={{ fontSize: '.8rem', color: '#888', marginBottom: 4 }}>{item.label}</div>
            <div style={{ fontSize: '1.3rem', fontWeight: 700 }}>{item.value}</div>
          </div>
        ))}
      </div>

      {modelUsage.length > 0 && (
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>今日模型使用</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>模型</th>
                <th>请求数</th>
                <th>Tokens</th>
                <th>消费</th>
              </tr>
            </thead>
            <tbody>
              {modelUsage.map((m, i) => (
                <tr key={i}>
                  <td>{m.model_name}</td>
                  <td>{m.request_count}</td>
                  <td>{m.total_tokens.toLocaleString()}</td>
                  <td>¥{m.cost.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(!modelUsage || modelUsage.length === 0) && (
        <div className="card" style={{ textAlign: 'center', padding: 40, color: '#888' }}>
          <p>暂无使用记录。创建 API Key 后即可开始使用～</p>
        </div>
      )}
    </div>
  );
}
