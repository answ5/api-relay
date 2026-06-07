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

  if (loading) return <div className="user-empty">加载中...</div>;

  const summary = stats?.summary || {};
  const modelUsage = stats?.model_usage || [];

  return (
    <div>
      <h2 className="page-title">我的概览</h2>

      <div className="user-balance-card">
        <div>
          <div className="user-balance-label">账户余额</div>
          <div className="user-balance-amount">¥{parseFloat(profile?.balance || 0).toFixed(4)}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="user-balance-label">累计消费</div>
          <div className="" style={{ fontSize: '1.2rem', fontWeight: 600 }}>
            ¥{parseFloat(summary.total_spent || 0).toFixed(4)}
          </div>
        </div>
      </div>

      <div className="user-stats-grid">
        {[
          { label: '今日请求', value: summary.today_requests || 0 },
          { label: '今日消耗 Tokens', value: (summary.today_tokens || 0).toLocaleString() },
          { label: '今日消费', value: `¥${(summary.today_cost || 0).toFixed(4)}` },
          { label: '成功率', value: `${summary.success_rate || 100}%` },
          { label: '有效 API Keys', value: summary.active_tokens || 0 },
          { label: '累计 Tokens', value: (summary.total_tokens_all_time || 0).toLocaleString() },
        ].map((item, i) => (
          <div key={i} className="user-stat-card">
            <div className="stat-label">{item.label}</div>
            <div className="stat-value">{item.value}</div>
          </div>
        ))}
      </div>

      {modelUsage.length > 0 ? (
        <div className="user-card">
          <div className="user-section-title">今日模型使用</div>
          <table className="user-table">
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
      ) : (
        <div className="user-empty">
          <div className="user-empty-icon">📭</div>
          <p>暂无使用记录。创建 API Key 后即可开始使用～</p>
        </div>
      )}
    </div>
  );
}
