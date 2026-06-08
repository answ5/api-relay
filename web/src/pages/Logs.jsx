import React, { useState, useEffect } from 'react';
import { listLogs, getLogPayload } from '../api';

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ userId: '', model: '', dateFrom: '', dateTo: '' });
  const [payloadModal, setPayloadModal] = useState(null);
  const [toast, setToast] = useState(null);
  const size = 20;

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  };

  const load = () => {
    setLoading(true);
    const params = { page, size };
    if (filters.userId) params.user_id = parseInt(filters.userId);
    if (filters.model) params.model = filters.model;
    if (filters.dateFrom) params.date_from = filters.dateFrom;
    if (filters.dateTo) params.date_to = filters.dateTo;
    listLogs(params).then((res) => {
      setLogs(res.data.data);
      setTotal(res.data.total);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page]);

  const handlePayload = async (id) => {
    try {
      const res = await getLogPayload(id);
      setPayloadModal({ ...res.data.data, logId: id });
    } catch (e) {
      showToast('获取 payload 失败', 'error');
    }
  };

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.msg}</div>}
      <div className="page-header">
        <h2>📋 请求日志</h2>
      </div>
      <div className="card">
        <div className="filter-bar">
          <input placeholder="用户 ID" value={filters.userId} onChange={(e) => setFilters({ ...filters, userId: e.target.value })} style={{ width: 100 }} />
          <input placeholder="模型名" value={filters.model} onChange={(e) => setFilters({ ...filters, model: e.target.value })} />
          <input type="date" value={filters.dateFrom} onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })} />
          <input type="date" value={filters.dateTo} onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })} />
          <button className="btn btn-ghost btn-sm" onClick={() => { setPage(1); load(); }}>搜索</button>
          <button className="btn btn-ghost btn-sm" onClick={() => { setFilters({ userId: '', model: '', dateFrom: '', dateTo: '' }); setPage(1); }}>清除</button>
          <span className="filter-count">共 {total} 条</span>
        </div>
        {loading ? <div className="loading">加载中...</div> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>ID</th><th>用户</th><th>模型</th><th>Token</th><th>费用</th><th>耗时</th><th>流式</th><th>状态</th><th>时间</th><th>详情</th></tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id}>
                    <td>{l.id}</td>
                    <td>#{l.user_id}</td>
                    <td className="cell-model-name" title={l.model_name}>{l.model_name}</td>
                    <td>{(l.total_tokens || 0).toLocaleString()}</td>
                    <td>{parseFloat(l.user_cost || 0).toFixed(6)}</td>
                    <td>{l.response_ms}ms</td>
                    <td>{l.is_stream ? <span className="badge badge-stream">流式</span> : <span className="badge badge-error">非流</span>}</td>
                    <td><span className={`badge ${l.status === 'success' ? 'badge-success' : 'badge-error'}`}>{l.status}</span></td>
                    <td className="cell-time">{l.created_at?.slice(0, 19)}</td>
                    <td><button className="btn btn-ghost btn-sm" onClick={() => handlePayload(l.id)}>Payload</button></td>
                  </tr>
                ))}
                {logs.length === 0 && <tr><td colSpan={10} className="empty">暂无数据</td></tr>}
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

      {payloadModal && (
        <div className="modal-overlay" onClick={() => setPayloadModal(null)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header"><span>请求详情 - #{payloadModal.logId}</span><button onClick={() => setPayloadModal(null)}>&times;</button></div>
            <div className="modal-body modal-body-scroll">
              <h4 className="modal-subtitle">请求体</h4>
              <pre className="pre-box">
                {payloadModal.request_payload ? JSON.stringify(payloadModal.request_payload, null, 2) : '暂无'}
              </pre>
              <h4 className="modal-subtitle" style={{ marginTop: 12 }}>响应体</h4>
              <pre className="pre-box">
                {payloadModal.response_payload ? JSON.stringify(payloadModal.response_payload, null, 2) : '暂无'}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
