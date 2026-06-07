import React, { useState, useEffect, useCallback } from 'react';
import { userListLogs } from '../../api';

export default function UserLogs() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const loadLogs = useCallback(() => {
    setLoading(true);
    userListLogs({ page, size: 20 })
      .then((res) => {
        setLogs(res.data.data || []);
        setTotal(res.data.total || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => { loadLogs(); }, [loadLogs]);

  const formatCost = (v) => `¥${parseFloat(v || 0).toFixed(6)}`;
  const formatTime = (t) => t ? t.replace('T', ' ').substring(0, 19) : '-';

  return (
    <div>
      <h2 className="page-title">使用日志</h2>

      {loading ? <div className="user-empty">加载中...</div> : (
        <div className="user-card">
          <table className="user-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>模型</th>
                <th>状态</th>
                <th>Prompt</th>
                <th>Completion</th>
                <th>总 Tokens</th>
                <th>消费</th>
                <th>耗时</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr><td colSpan={9} style={{ textAlign: 'center', color: '#bbb' }}>暂无使用记录</td></tr>
              ) : logs.map((log) => (
                <tr key={log.id}>
                  <td style={{ fontSize: '.8rem', color: '#999' }}>{log.id}</td>
                  <td style={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {log.model_name}
                  </td>
                  <td><span className={`user-badge ${log.status === 'success' ? 'user-badge-green' : 'user-badge-red'}`}>
                    {log.status}
                  </span></td>
                  <td>{(log.prompt_tokens || 0).toLocaleString()}</td>
                  <td>{(log.completion_tokens || 0).toLocaleString()}</td>
                  <td>{(log.total_tokens || 0).toLocaleString()}</td>
                  <td>{formatCost(log.user_cost)}</td>
                  <td>{log.response_ms ? `${log.response_ms}ms` : '-'}</td>
                  <td style={{ fontSize: '.8rem', color: '#999' }}>{formatTime(log.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {total > 20 && (
            <div className="user-pagination">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一页</button>
              <span>第 {page} / {Math.ceil(total / 20)} 页</span>
              <button disabled={page >= Math.ceil(total / 20)} onClick={() => setPage(p => p + 1)}>下一页</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
