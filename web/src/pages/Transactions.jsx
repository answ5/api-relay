import React, { useState, useEffect } from 'react';
import { listTransactions } from '../api';

export default function Transactions() {
  const [txns, setTxns] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ userId: '', type: '' });
  const size = 20;

  const load = () => {
    setLoading(true);
    const params = { page, size };
    if (filters.userId) params.user_id = parseInt(filters.userId);
    if (filters.type) params.type = filters.type;
    listTransactions(params).then((res) => {
      setTxns(res.data.data);
      setTotal(res.data.total);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page]);

  const typeLabels = { consume: '消费', recharge: '充值', refund: '退款', admin_adjust: '管理员调整' };

  return (
    <div>
      <h2 style={{ fontWeight: 600, marginBottom: 16 }}>💳 交易记录</h2>
      <div className="card">
        <div className="filter-bar">
          <input placeholder="用户 ID" value={filters.userId} onChange={(e) => setFilters({ ...filters, userId: e.target.value })} style={{ width: 100 }} />
          <select value={filters.type} onChange={(e) => setFilters({ ...filters, type: e.target.value })}>
            <option value="">全部类型</option>
            <option value="consume">消费</option>
            <option value="recharge">充值</option>
            <option value="refund">退款</option>
            <option value="admin_adjust">管理员调整</option>
          </select>
          <button className="btn btn-ghost btn-sm" onClick={() => { setPage(1); load(); }}>搜索</button>
          <button className="btn btn-ghost btn-sm" onClick={() => { setFilters({ userId: '', type: '' }); setPage(1); }}>清除</button>
          <span style={{ fontSize: '.85rem', color: 'var(--text2)', marginLeft: 'auto' }}>共 {total} 条</span>
        </div>
        {loading ? <div className="loading">加载中...</div> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>ID</th><th>��户</th><th>类型</th><th>金额</th><th>余额变动后</th><th>备注</th><th>日志 ID</th><th>时间</th></tr>
              </thead>
              <tbody>
                {txns.map((t) => (
                  <tr key={t.id}>
                    <td>{t.id}</td>
                    <td>#{t.user_id}</td>
                    <td><span className="tag tag-active">{typeLabels[t.type] || t.type}</span></td>
                    <td style={{ fontWeight: 500, color: parseFloat(t.amount) >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                      {parseFloat(t.amount) >= 0 ? '+' : ''}{parseFloat(t.amount || 0).toFixed(4)}
                    </td>
                    <td>{t.balance_after != null ? parseFloat(t.balance_after).toFixed(4) : '-'}</td>
                    <td style={{ fontSize: '.8rem', color: 'var(--text2)', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.note || '-'}</td>
                    <td>{t.log_id ? `#${t.log_id}` : '-'}</td>
                    <td style={{ fontSize: '.8rem', color: 'var(--text2)' }}>{t.created_at?.slice(0, 19)}</td>
                  </tr>
                ))}
                {txns.length === 0 && <tr><td colSpan={8} className="empty">暂无数据</td></tr>}
              </tbody>
            </table>
          </div>
        )}
        {total > size && (
          <div className="pagination">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
            <span>第 {page} / {Math.ceil(total / size)} 页</span>
            <button disabled={page >= Math.ceil(total / size)} onClick={() => setPage(page + 1)}>下一页</button>
          </div>
        )}
      </div>
    </div>
  );
}
