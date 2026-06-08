import React, { useState, useEffect } from 'react';
import { dashboardStats } from '../api';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    dashboardStats().then((res) => setStats(res.data.data)).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="loading">加载中...</div>;

  const s = stats?.summary || {};
  const hourly = stats?.hourly_breakdown || [];
  const topModels = stats?.top_models || [];
  const topUsers = stats?.top_users || [];

  const statCards = [
    { label: '总请求', value: s.total_requests?.toLocaleString(), color: 'blue', icon: '📨' },
    { label: '成功', value: s.success_requests?.toLocaleString(), color: 'green', icon: '✅' },
    { label: '失败', value: s.failed_requests?.toLocaleString(), color: 'red', icon: '❌' },
    { label: '总 Token', value: (s.total_tokens || 0).toLocaleString(), color: 'purple', icon: '🎯' },
    { label: '收入', value: s.total_user_cost?.toFixed(4), color: 'green', icon: '💰' },
    { label: '上游成本', value: s.total_upstream_cost?.toFixed(4), color: 'orange', icon: '📤' },
    { label: '利润', value: s.profit?.toFixed(4), color: parseFloat(s.profit || 0) >= 0 ? 'green' : 'red', icon: '📈' },
    { label: '活跃用户', value: s.active_users, color: 'blue', icon: '👤' },
    { label: '平均响应', value: `${s.avg_response_ms}ms`, color: 'purple', icon: '⚡' },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 16, fontWeight: 600 }}>今日仪表盘</h2>

      <div className="stats-grid">
        {statCards.map((card, i) => (
          <div key={i} className={`stat-card ${card.color}`}>
            <div className="stat-icon">{card.icon}</div>
            <div className="label">{card.label}</div>
            <div className="num">{card.value}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 12, fontSize: '1rem' }}>今日小时分布</h3>
        {hourly.length === 0 ? <div className="empty">暂无数据</div> : (
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 120, padding: '0 4px' }}>
            {hourly.map((h) => {
              const max = Math.max(...hourly.map((x) => x.request_count), 1);
              const pct = (h.request_count / max) * 100;
              return (
                <div key={h.hour} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <div style={{ fontSize: '.7rem', color: 'var(--text2)', marginBottom: 2 }}>{h.request_count}</div>
                  <div style={{
                    width: '100%', maxWidth: 28,
                    height: Math.max(pct * 0.8, 4),
                    background: 'linear-gradient(to top, #6366f1, #8b5cf6)',
                    borderRadius: '3px 3px 0 0', opacity: 0.7 + (pct / 100) * 0.3,
                  }}></div>
                  <div style={{ fontSize: '.65rem', color: 'var(--text2)', marginTop: 4 }}>{h.hour}时</div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="card">
          <h3 style={{ marginBottom: 12, fontSize: '1rem' }}>热门模型</h3>
          {topModels.length === 0 ? <div className="empty">暂无数据</div> : (
            <table>
              <thead>
                <tr><th>模型</th><th>请求</th><th>Token</th><th>收入</th></tr>
              </thead>
              <tbody>
                {topModels.map((m) => (
                  <tr key={m.model_name}>
                    <td style={{ fontWeight: 500 }}>{m.model_name}</td>
                    <td>{m.request_count}</td>
                    <td>{(m.total_tokens || 0).toLocaleString()}</td>
                    <td>{m.total_revenue?.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="card">
          <h3 style={{ marginBottom: 12, fontSize: '1rem' }}>活跃用户</h3>
          {topUsers.length === 0 ? <div className="empty">暂无数据</div> : (
            <table>
              <thead>
                <tr><th>用户 ID</th><th>请求</th><th>Token</th><th>消费</th></tr>
              </thead>
              <tbody>
                {topUsers.map((u) => (
                  <tr key={u.user_id}>
                    <td>#{u.user_id}</td>
                    <td>{u.request_count}</td>
                    <td>{(u.total_tokens || 0).toLocaleString()}</td>
                    <td>{u.total_spent?.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
