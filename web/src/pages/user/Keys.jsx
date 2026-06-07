import React, { useState, useEffect, useCallback } from 'react';
import { userListTokens, userCreateToken, userDeleteToken } from '../../api';

export default function UserKeys() {
  const [tokens, setTokens] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [newKey, setNewKey] = useState(null);
  const [name, setName] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const loadTokens = useCallback(() => {
    setLoading(true);
    userListTokens({ page, size: 20 })
      .then((res) => {
        setTokens(res.data.data || []);
        setTotal(res.data.total || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => { loadTokens(); }, [loadTokens]);

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    try {
      const res = await userCreateToken({ name });
      setNewKey(res.data);
      setName('');
      loadTokens();
    } catch (err) {
      setError(err.response?.data?.detail?.error?.message || '创建失败');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('确定删除这个 API Key？')) return;
    try {
      await userDeleteToken(id);
      loadTokens();
    } catch (err) {
      alert(err.response?.data?.detail || '删除失败');
    }
  };

  const copyKey = (key) => {
    navigator.clipboard.writeText(key);
    alert('已复制到剪贴板');
  };

  return (
    <div>
      <h2 className="page-title">API Keys</h2>

      {newKey && (
        <div className="user-newkey-box">
          <h3>✅ API Key 创建成功！</h3>
          <p style={{ fontSize: '.85rem', color: '#666', marginBottom: 12 }}>
            请立即保存此 Key，关闭后将无法再次查看。
          </p>
          <div className="user-key-display">
            sk-{newKey.raw_key}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-primary btn-sm" onClick={() => copyKey(`sk-${newKey.raw_key}`)}>
              复制 Key
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => setNewKey(null)}>
              关闭
            </button>
          </div>
        </div>
      )}

      <div className="user-create-key-box">
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: 1, marginBottom: 0 }}>
            <label>备注名称</label>
            <input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="例如：我的测试 Key" style={{ width: '100%' }} />
          </div>
          <button className="btn btn-primary" onClick={handleCreate} disabled={creating}
            style={{ padding: '10px 20px', height: 40 }}>
            {creating ? '创建中...' : '创建新 Key'}
          </button>
        </div>
        {error && <p style={{ color: '#cf1322', fontSize: '.85rem', marginTop: 8 }}>{error}</p>}
      </div>

      {loading ? <div className="user-empty">加载中...</div> : (
        <div className="user-card">
          <table className="user-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>Key 前缀</th>
                <th>状态</th>
                <th>分组</th>
                <th>限额</th>
                <th>最后使用</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {tokens.length === 0 ? (
                <tr><td colSpan={8} style={{ textAlign: 'center', color: '#bbb' }}>暂无 API Key</td></tr>
              ) : tokens.map((t) => (
                <tr key={t.id}>
                  <td>{t.name || '-'}</td>
                  <td><code style={{ fontSize: '.8rem', background: '#f5f5f5', padding: '2px 6px', borderRadius: 4 }}>sk-{t.key_prefix}...</code></td>
                  <td><span className={`user-badge ${t.status === 1 ? 'user-badge-green' : 'user-badge-red'}`}>
                    {t.status === 1 ? '启用' : '禁用'}
                  </span></td>
                  <td>{t.group_name}</td>
                  <td>¥{parseFloat(t.balance_limit || 0).toFixed(2)}</td>
                  <td style={{ fontSize: '.8rem', color: '#999' }}>{t.last_used_at || '-'}</td>
                  <td style={{ fontSize: '.8rem', color: '#999' }}>{t.created_at || '-'}</td>
                  <td>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDelete(t.id)}>
                      删除
                    </button>
                  </td>
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
