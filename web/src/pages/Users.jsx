import React, { useState, useEffect } from 'react';
import { listUsers, createUser, updateUser, adjustBalance, adminResetUserPassword } from '../api';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
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
    listUsers({ page, size, keyword: keyword || undefined }).then((res) => {
      setUsers(res.data.data);
      setTotal(res.data.total);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page]);

  const handleSearch = () => { setPage(1); load(); };

  const handleCreate = async (data) => {
    await createUser(data);
    showToast('用户创建成功');
    setModal(null);
    load();
  };

  const handleUpdate = async (id, data) => {
    await updateUser(id, data);
    showToast('用户更新成功');
    setModal(null);
    load();
  };

  const handleBalance = async (id, data) => {
    await adjustBalance(id, data);
    showToast('余额调整成功');
    setModal(null);
    load();
  };

  const handlePasswordReset = async (id, data) => {
    await adminResetUserPassword(id, data);
    showToast('密码已重置');
    setModal(null);
  };

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.msg}</div>}

      <div className="page-header">
        <h2>👥 用户管理</h2>
        <button className="btn btn-primary" onClick={() => setModal({ type: 'create' })}>+ 创建用户</button>
      </div>

      <div className="card">
        <div className="filter-bar">
          <input placeholder="搜索用户名/邮箱/ID" value={keyword} onChange={(e) => setKeyword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSearch()} />
          <button className="btn btn-ghost btn-sm" onClick={handleSearch}>搜索</button>
          <span className="filter-count">共 {total} 个用户</span>
        </div>
        {loading ? <div className="loading">加载中...</div> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>ID</th><th>用户名</th><th>邮箱</th><th>角色</th><th>余额</th><th>状态</th><th>创建时间</th><th>操作</th></tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td className="cell-name">{u.username}</td>
                    <td className="cell-time">{u.email || '-'}</td>
                    <td><span className={`tag ${u.role === 'admin' || u.role === 'super_admin' ? 'tag-admin' : 'tag-user'}`}>{u.role}</span></td>
                    <td className="cell-name">{parseFloat(u.balance || 0).toFixed(4)}</td>
                    <td><span className={`tag ${u.status === 1 ? 'tag-active' : 'tag-inactive'}`}>{u.status === 1 ? '启用' : '禁用'}</span></td>
                    <td className="cell-time">{u.created_at?.slice(0, 19)}</td>
                    <td>
                      <button className="btn btn-ghost btn-sm" onClick={() => setModal({ type: 'edit', data: u })}>编辑</button>{' '}
                      <button className="btn btn-ghost btn-sm" onClick={() => setModal({ type: 'balance', data: u })}>余额</button>{' '}
                      <button className="btn btn-ghost btn-sm" onClick={() => setModal({ type: 'password', data: u })}>密码</button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && <tr><td colSpan={8} className="empty">暂无数据</td></tr>}
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

      {modal && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            {modal.type === 'create' && <UserCreateForm onSave={handleCreate} onClose={() => setModal(null)} />}
            {modal.type === 'edit' && <UserEditForm user={modal.data} onSave={(d) => handleUpdate(modal.data.id, d)} onClose={() => setModal(null)} />}
            {modal.type === 'balance' && <BalanceForm user={modal.data} onSave={(d) => handleBalance(modal.data.id, d)} onClose={() => setModal(null)} />}
            {modal.type === 'password' && <PasswordForm user={modal.data} onSave={(d) => handlePasswordReset(modal.data.id, d)} onClose={() => setModal(null)} />}
          </div>
        </div>
      )}
    </div>
  );
}

function UserCreateForm({ onSave, onClose }) {
  const [form, setForm] = useState({ username: '', password: '', email: '', role: 'user', balance: 0, status: 1 });
  const [loading, setLoading] = useState(false);
  const update = (k, v) => setForm({ ...form, [k]: v });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.username || !form.password) return;
    setLoading(true);
    try { await onSave(form); } catch (e) {} finally { setLoading(false); }
  };

  return (
    <>
      <div className="modal-header"><span>创建用户</span><button onClick={onClose}>&times;</button></div>
      <form onSubmit={handleSubmit}>
        <div className="modal-body">
          <div className="form-row">
            <div className="form-group"><label>用户名 *</label><input value={form.username} onChange={(e) => update('username', e.target.value)} /></div>
            <div className="form-group"><label>密码 *</label><input type="text" value={form.password} onChange={(e) => update('password', e.target.value)} /></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>邮箱</label><input value={form.email} onChange={(e) => update('email', e.target.value)} /></div>
            <div className="form-group"><label>角色</label><select value={form.role} onChange={(e) => update('role', e.target.value)}><option value="user">用户</option><option value="admin">管理员</option><option value="super_admin">超级管理员</option></select></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>初始余额</label><input type="number" step="0.0001" value={form.balance} onChange={(e) => update('balance', parseFloat(e.target.value) || 0)} /></div>
            <div className="form-group"><label>状态</label><select value={form.status} onChange={(e) => update('status', parseInt(e.target.value))}><option value={1}>启用</option><option value={0}>禁用</option></select></div>
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
          <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? '创建中...' : '创建'}</button>
        </div>
      </form>
    </>
  );
}

function UserEditForm({ user, onSave, onClose }) {
  const [form, setForm] = useState({ username: user.username, email: user.email || '', role: user.role, status: user.status, password: '' });
  const [loading, setLoading] = useState(false);
  const update = (k, v) => setForm({ ...form, [k]: v });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const data = { ...form };
    if (!data.password) delete data.password;
    try { await onSave(data); } catch (e) {} finally { setLoading(false); }
  };

  return (
    <>
      <div className="modal-header"><span>编辑用户 #{user.id}</span><button onClick={onClose}>&times;</button></div>
      <form onSubmit={handleSubmit}>
        <div className="modal-body">
          <div className="form-row">
            <div className="form-group"><label>用户名</label><input value={form.username} onChange={(e) => update('username', e.target.value)} /></div>
            <div className="form-group"><label>新密码（留空不修改）</label><input type="text" value={form.password} onChange={(e) => update('password', e.target.value)} /></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>邮箱</label><input value={form.email} onChange={(e) => update('email', e.target.value)} /></div>
            <div className="form-group"><label>角色</label><select value={form.role} onChange={(e) => update('role', e.target.value)}><option value="user">用户</option><option value="admin">管理员</option><option value="super_admin">超级管理员</option></select></div>
          </div>
          <div className="form-group"><label>状态</label><select value={form.status} onChange={(e) => update('status', parseInt(e.target.value))}><option value={1}>启用</option><option value={0}>禁用</option></select></div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
          <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? '保存中...' : '保存'}</button>
        </div>
      </form>
    </>
  );
}

function BalanceForm({ user, onSave, onClose }) {
  const [form, setForm] = useState({ amount: 0, note: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.amount) return;
    setLoading(true);
    try { await onSave(form); } catch (e) {} finally { setLoading(false); }
  };

  return (
    <>
      <div className="modal-header"><span>余额调整 - {user.username}</span><button onClick={onClose}>&times;</button></div>
      <div className="modal-body">
        <p style={{ marginBottom: 12, fontSize: '.85rem', color: 'var(--text2)' }}>当前余额: <strong>{parseFloat(user.balance || 0).toFixed(4)}</strong></p>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <div className="form-group"><label>金额（正=充值，负=扣款）</label><input type="number" step="0.0001" value={form.amount} onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })} autoFocus /></div>
            <div className="form-group"><label>备注</label><input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} /></div>
          </div>
          <div className="modal-footer" style={{ padding: '12px 0 0' }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? '处理中...' : '确认'}</button>
          </div>
        </form>
      </div>
    </>
  );
}

function PasswordForm({ user, onSave, onClose }) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password.length < 6) { setError('密码长度至少 6 位'); return; }
    if (password !== confirm) { setError('两次密码输入不一致'); return; }
    setLoading(true);
    try { await onSave({ password }); } catch (e) {
      setError(e.response?.data?.detail?.error?.message || '重置失败');
    } finally { setLoading(false); }
  };

  return (
    <>
      <div className="modal-header"><span>重置密码 - {user.username}</span><button onClick={onClose}>&times;</button></div>
      <form onSubmit={handleSubmit}>
        <div className="modal-body">
          {error && <p style={{ color: '#cf1322', fontSize: '.85rem', marginBottom: 12 }}>{error}</p>}
          <div className="form-group">
            <label>新密码</label>
            <input type="text" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="至少 6 位" autoFocus />
          </div>
          <div className="form-group">
            <label>确认密码</label>
            <input type="text" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="再次输入" />
          </div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
          <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? '重置中...' : '重置密码'}</button>
        </div>
      </form>
    </>
  );
}
