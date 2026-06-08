import React, { useState, useEffect } from 'react';
import { listTokens, createToken, updateToken, deleteToken, listUsers } from '../api';

export default function Tokens() {
  const [tokens, setTokens] = useState([]);
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [userId, setUserId] = useState('');
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState(null);
  const size = 20;

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  };

  const load = () => {
    setLoading(true);
    Promise.all([
      listTokens({ page, size, user_id: userId ? parseInt(userId) : undefined }),
      listUsers({ page: 1, size: 100 }),
    ]).then(([tres, ures]) => {
      setTokens(tres.data.data);
      setTotal(tres.data.total);
      setUsers(ures.data.data);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page]);

  const handleCreate = async (data) => {
    const res = await createToken(data);
    showToast(`Token 创建成功! 密钥: ${res.data.raw_key}（请保存）`);
    setModal(null);
    load();
  };

  const handleUpdate = async (id, data) => {
    await updateToken(id, data);
    showToast('Token 更新成功');
    setModal(null);
    load();
  };

  const handleDelete = async (id) => {
    if (!window.confirm('确认删除此 Token？')) return;
    await deleteToken(id);
    showToast('Token 已删除');
    load();
  };

  const copy = (text) => {
    navigator.clipboard.writeText(text);
    showToast('已复制');
  };

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.msg}</div>}
      <div className="page-header">
        <h2>🔑 Token 管理</h2>
        <button className="btn btn-primary" onClick={() => setModal({ type: 'create' })}>+ 创建 Token</button>
      </div>
      <div className="card">
        <div className="filter-bar">
          <input placeholder="按用户 ID 筛选" value={userId} onChange={(e) => setUserId(e.target.value)} />
          <button className="btn btn-ghost btn-sm" onClick={() => { setPage(1); load(); }}>筛选</button>
          {userId && <button className="btn btn-ghost btn-sm" onClick={() => { setUserId(''); setPage(1); load(); }}>清除</button>}
          <span className="filter-count">共 {total} 个 Token</span>
        </div>
        {loading ? <div className="loading">加载中...</div> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>ID</th><th>名称</th><th>用户</th><th>Key 前缀</th><th>分组</th><th>限流</th><th>状态</th><th>最后使用</th><th>操作</th></tr>
              </thead>
              <tbody>
                {tokens.map((t) => (
                  <tr key={t.id}>
                    <td>{t.id}</td>
                    <td className="cell-name">{t.name || '-'}</td>
                    <td>{users.find((u) => u.id === t.user_id)?.username || `#${t.user_id}`}</td>
                    <td><code>sk-{t.key_prefix}...</code></td>
                    <td><span className="tag tag-active">{t.group_name}</span></td>
                    <td>{t.rate_limit_per_minute}/min</td>
                    <td><span className={`tag ${t.status === 1 ? 'tag-active' : 'tag-inactive'}`}>{t.status === 1 ? '启用' : '禁用'}</span></td>
                    <td className="cell-time">{t.last_used_at?.slice(0, 19) || '从未使用'}</td>
                    <td>
                      <button className="btn btn-ghost btn-sm" onClick={() => setModal({ type: 'edit', data: t })}>编辑</button>{' '}
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(t.id)}>删除</button>
                    </td>
                  </tr>
                ))}
                {tokens.length === 0 && <tr><td colSpan={9} className="empty">暂无数据</td></tr>}
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
            <TokenCreateForm users={users} onSave={handleCreate} onClose={() => setModal(null)} />
          </div>
        </div>
      )}
      {modal?.type === 'edit' && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <TokenEditForm token={modal.data} onSave={(d) => handleUpdate(modal.data.id, d)} onClose={() => setModal(null)} />
          </div>
        </div>
      )}
    </div>
  );
}

function TokenCreateForm({ users, onSave, onClose }) {
  const [form, setForm] = useState({ user_id: users[0]?.id || '', name: '', models: '', rate_limit_per_minute: 60, balance_limit: 0, group_name: 'default' });
  const [loading, setLoading] = useState(false);
  const update = (k, v) => setForm({ ...form, [k]: v });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.user_id) return;
    setLoading(true);
    try { await onSave({ ...form, user_id: parseInt(form.user_id), models: form.models || null }); } catch (e) {} finally { setLoading(false); }
  };

  return (
    <>
      <div className="modal-header"><span>创建 Token</span><button onClick={onClose}>&times;</button></div>
      <form onSubmit={handleSubmit}>
        <div className="modal-body">
          <div className="form-row">
            <div className="form-group"><label>所属用户 *</label><select value={form.user_id} onChange={(e) => update('user_id', e.target.value)}>{users.map((u) => <option key={u.id} value={u.id}>{u.username} (#{u.id})</option>)}</select></div>
            <div className="form-group"><label>名称</label><input value={form.name} onChange={(e) => update('name', e.target.value)} /></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>分组</label><select value={form.group_name} onChange={(e) => update('group_name', e.target.value)}><option value="default">default</option><option value="vip">vip</option><option value="pro">pro</option></select></div>
            <div className="form-group"><label>限流 (次/分钟)</label><input type="number" value={form.rate_limit_per_minute} onChange={(e) => update('rate_limit_per_minute', parseInt(e.target.value) || 60)} /></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>额度上限</label><input type="number" step="0.0001" value={form.balance_limit} onChange={(e) => update('balance_limit', parseFloat(e.target.value) || 0)} /></div>
            <div className="form-group"><label>模型限制（留空=全部）</label><input placeholder="gpt-4,claude-3" value={form.models} onChange={(e) => update('models', e.target.value)} /></div>
          </div>
          <div className="form-notice">⚠️ 创建后密钥只显示一次，请立即保存</div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
          <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? '创建中...' : '创建'}</button>
        </div>
      </form>
    </>
  );
}

function TokenEditForm({ token, onSave, onClose }) {
  const [form, setForm] = useState({
    name: token.name || '',
    status: token.status,
    models: token.models || '',
    rate_limit_per_minute: token.rate_limit_per_minute,
    balance_limit: parseFloat(token.balance_limit || 0),
    group_name: token.group_name,
  });
  const [loading, setLoading] = useState(false);
  const update = (k, v) => setForm({ ...form, [k]: v });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try { await onSave({ ...form, models: form.models || null }); } catch (e) {} finally { setLoading(false); }
  };

  return (
    <>
      <div className="modal-header"><span>编辑 Token #{token.id}</span><button onClick={onClose}>&times;</button></div>
      <form onSubmit={handleSubmit}>
        <div className="modal-body">
          <p className="form-hint">Key 前缀: <code>sk-{token.key_prefix}...</code></p>
          <div className="form-row">
            <div className="form-group"><label>名称</label><input value={form.name} onChange={(e) => update('name', e.target.value)} /></div>
            <div className="form-group"><label>分组</label><select value={form.group_name} onChange={(e) => update('group_name', e.target.value)}><option value="default">default</option><option value="vip">vip</option><option value="pro">pro</option></select></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>状态</label><select value={form.status} onChange={(e) => update('status', parseInt(e.target.value))}><option value={1}>启用</option><option value={0}>禁用</option></select></div>
            <div className="form-group"><label>限流 (次/分钟)</label><input type="number" value={form.rate_limit_per_minute} onChange={(e) => update('rate_limit_per_minute', parseInt(e.target.value) || 60)} /></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>额度上限</label><input type="number" step="0.0001" value={form.balance_limit} onChange={(e) => update('balance_limit', parseFloat(e.target.value) || 0)} /></div>
            <div className="form-group"><label>模型限制</label><input placeholder="gpt-4,claude-3" value={form.models} onChange={(e) => update('models', e.target.value)} /></div>
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
