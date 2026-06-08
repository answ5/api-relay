import React, { useState, useEffect } from 'react';
import { listChannels, createChannel, updateChannel, healthCheckChannel } from '../api';
import api from '../api';

export default function Channels() {
  const [channels, setChannels] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState(null);
  const [healthResult, setHealthResult] = useState(null);
  const [balanceResult, setBalanceResult] = useState(null);
  const size = 20;

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  };

  const load = () => {
    setLoading(true);
    listChannels({ page, size }).then((res) => {
      setChannels(res.data.data);
      setTotal(res.data.total);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page]);

  const handleCreate = async (data) => {
    await createChannel(data);
    showToast('渠道创建成功');
    setModal(null);
    load();
  };

  const handleUpdate = async (id, data) => {
    await updateChannel(id, data);
    showToast('渠道更新成功');
    setModal(null);
    load();
  };

  const handleHealthCheck = async (id) => {
    setHealthResult({ checking: true, id });
    try {
      const res = await healthCheckChannel(id);
      setHealthResult({ ...res.data.data, checking: false, id });
    } catch (e) {
      setHealthResult({ error: '检查失败', checking: false, id });
    }
    setTimeout(() => setHealthResult(null), 5000);
  };

  const handleBalanceCheck = async (id) => {
    setBalanceResult({ checking: true, id });
    try {
      const res = await api.post(`/channels/${id}/balance`);
      setBalanceResult({ ...res.data?.data, checking: false, id });
    } catch (e) {
      setBalanceResult({ error: '查询失败', checking: false, id });
    }
    setTimeout(() => setBalanceResult(null), 8000);
  };

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.msg}</div>}
      <div className="page-header">
        <h2>🔗 渠道管理</h2>
        <button className="btn btn-primary" onClick={() => setModal({ type: 'create' })}>+ 添加渠道</button>
      </div>
      <div className="card">
        <div className="filter-count" style={{ marginBottom: 12, marginLeft: 0 }}>共 {total} 个渠道</div>
        {loading ? <div className="loading">加载中...</div> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>ID</th><th>名称</th><th>地址</th><th>权重</th><th>优先级</th><th>模型</th><th>熔断</th><th>状态</th><th>健康检查</th></tr>
              </thead>
              <tbody>
                {channels.map((c) => (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td className="cell-name">{c.name}</td>
                    <td className="cell-url" title={c.base_url}>{c.base_url}</td>
                    <td>{c.weight}</td>
                    <td>{c.priority}</td>
                    <td className="cell-models">{c.models || '全部'}</td>
                    <td>{c.circuit_breaker ? (c.circuit_breaker.open ? <span className="badge badge-error">断开</span> : <span className="badge badge-success">正常</span>) : <span className="cell-time">-</span>}</td>
                    <td><span className={`tag ${c.status === 1 ? 'tag-active' : 'tag-inactive'}`}>{c.status === 1 ? '启用' : '禁用'}</span></td>
                    <td>
                      <button className="btn btn-ghost btn-sm" onClick={() => setModal({ type: 'edit', data: c })}>编辑</button>{' '}
                      <button className="btn btn-ghost btn-sm" onClick={() => handleHealthCheck(c.id)} disabled={healthResult?.checking && healthResult?.id === c.id}>
                        {healthResult?.checking && healthResult?.id === c.id ? '检查中...' : '🩺'}
                      </button>
                      <button className="btn btn-ghost btn-sm" onClick={() => handleBalanceCheck(c.id)} disabled={balanceResult?.checking && balanceResult?.id === c.id}>
                        {balanceResult?.checking && balanceResult?.id === c.id ? '查询中...' : '💰'}
                      </button>
                      {healthResult && healthResult.id === c.id && !healthResult.checking && (
                        <span style={{ fontSize: '.75rem', marginLeft: 4, color: healthResult.reachable ? 'var(--success)' : 'var(--danger)' }}>
                          {healthResult.reachable ? `连通 ${healthResult.response_time_ms}ms` : (healthResult.error || '不可达')}
                        </span>
                      )}
                      {balanceResult && balanceResult.id === c.id && !balanceResult.checking && (
                        <span style={{ fontSize: '.75rem', marginLeft: 4, color: 'var(--text2)' }}>
                          {balanceResult.results ? `${balanceResult.results.length} 个端点` : (balanceResult.error || '无数据')}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {channels.length === 0 && <tr><td colSpan={9} className="empty">暂无数据</td></tr>}
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

      {modal?.type === 'create' && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <ChannelForm onSave={handleCreate} onClose={() => setModal(null)} />
          </div>
        </div>
      )}
      {modal?.type === 'edit' && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <ChannelForm channel={modal.data} onSave={(d) => handleUpdate(modal.data.id, d)} onClose={() => setModal(null)} />
          </div>
        </div>
      )}
    </div>
  );
}

function ChannelForm({ channel, onSave, onClose }) {
  const [form, setForm] = useState(channel ? {
    name: channel.name,
    base_url: channel.base_url,
    api_key: '',
    weight: channel.weight,
    priority: channel.priority,
    status: channel.status,
    models: channel.models || '',
  } : { name: '', base_url: '', api_key: '', weight: 10, priority: 0, status: 1, models: '' });
  const [loading, setLoading] = useState(false);
  const update = (k, v) => setForm({ ...form, [k]: v });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.base_url) return;
    if (!channel && !form.api_key) return;
    const data = { ...form };
    if (!data.api_key) delete data.api_key;
    if (!data.models) data.models = null;
    setLoading(true);
    try { await onSave(data); } catch (e) {} finally { setLoading(false); }
  };

  return (
    <>
      <div className="modal-header"><span>{channel ? `编辑渠道 #${channel.id}` : '添加渠道'}</span><button onClick={onClose}>&times;</button></div>
      <form onSubmit={handleSubmit}>
        <div className="modal-body">
          {channel && <p style={{ marginBottom: 12, fontSize: '.85rem', color: 'var(--text2)' }}>API Key 留空则不修改</p>}
          <div className="form-row">
            <div className="form-group"><label>名称 *</label><input value={form.name} onChange={(e) => update('name', e.target.value)} /></div>
            <div className="form-group"><label>API Key {!channel ? '*' : ''}</label><input value={form.api_key} onChange={(e) => update('api_key', e.target.value)} placeholder={channel ? '留空不修改' : ''} /></div>
          </div>
          <div className="form-group"><label>上游地址 *</label><input value={form.base_url} onChange={(e) => update('base_url', e.target.value)} placeholder="https://api.openai.com" /></div>
          <div className="form-row">
            <div className="form-group"><label>权重</label><input type="number" value={form.weight} onChange={(e) => update('weight', parseInt(e.target.value) || 1)} /></div>
            <div className="form-group"><label>优先级（越大越优先）</label><input type="number" value={form.priority} onChange={(e) => update('priority', parseInt(e.target.value) || 0)} /></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>状态</label><select value={form.status} onChange={(e) => update('status', parseInt(e.target.value))}><option value={1}>启用</option><option value={0}>禁用</option></select></div>
            <div className="form-group"><label>模型限制（逗号分隔）</label><input placeholder="gpt-4,claude-3" value={form.models} onChange={(e) => update('models', e.target.value)} /></div>
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
          <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? '保存中...' : '保存'}</button>
        </div>
      </form>
    </>
  );
}
