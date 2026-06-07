import React, { useState, useEffect, useCallback } from 'react';
import { userListTransactions } from '../../api';

export default function UserBills() {
  const [txns, setTxns] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const loadTxns = useCallback(() => {
    setLoading(true);
    userListTransactions({ page, size: 20 })
      .then((res) => {
        setTxns(res.data.data || []);
        setTotal(res.data.total || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => { loadTxns(); }, [loadTxns]);

  const typeLabel = (t) => {
    const map = {
      consume: '消费',
      recharge: '充值',
      refund: '退款',
      admin_adjust: '管理员调整',
    };
    return map[t] || t;
  };
  const formatCost = (v) => (v < 0 ? '-' : '+') + `¥${Math.abs(parseFloat(v || 0)).toFixed(4)}`;
  const formatTime = (t) => t ? t.replace('T', ' ').substring(0, 19) : '-';

  const totalPages = Math.ceil(total / 20);

  return (
    <div>
      <h2 className="page-title">消费记录</h2>

      {loading ? <div className="user-empty">加载中...</div> : (
        <div className="user-card">
          <table className="user-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>类型</th>
                <th>金额</th>
                <th>余额</th>
                <th>备注</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              {txns.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', color: '#bbb' }}>暂无记录</td></tr>
              ) : txns.map((t) => (
                <tr key={t.id}>
                  <td style={{ fontSize: '.8rem', color: '#999' }}>{t.id}</td>
                  <td><span style={{
                    color: t.type === 'consume' ? '#cf1322' : '#52c41a',
                    fontWeight: 600,
                  }}>{typeLabel(t.type)}</span></td>
                  <td style={{ color: t.amount < 0 ? '#cf1322' : '#52c41a' }}>
                    {formatCost(t.amount)}
                  </td>
                  <td>¥{parseFloat(t.balance_after || 0).toFixed(4)}</td>
                  <td style={{ color: '#999', fontSize: '.85rem' }}>{t.note || '-'}</td>
                  <td style={{ fontSize: '.8rem', color: '#999' }}>{formatTime(t.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div className="user-pagination">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一页</button>
              <span>第 {page} / {totalPages} 页</span>
              <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>下一页</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
