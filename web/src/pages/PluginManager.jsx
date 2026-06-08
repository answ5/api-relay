import React, { useState, useEffect } from 'react';
import api from '../api';

export default function PluginManager() {
  const [plugins, setPlugins] = useState({ enabled: [], disabled: [], discovered: [] });
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    api.get('/plugins')
      .then((res) => setPlugins(res.data?.data || { enabled: [], disabled: [], discovered: [] }))
      .catch(() => setMessage('加载插件列表失败'))
      .finally(() => setLoading(false));
  }, []);

  const handleToggle = async (name) => {
    setToggling(name);
    setMessage('');
    try {
      const res = await api.post(`/plugins/${name}/toggle`);
      setPlugins(res.data?.data || plugins);
      setMessage(res.data?.message || `${name} 已切换`);
    } catch (err) {
      setMessage(err.response?.data?.error?.message || '操作失败');
    } finally {
      setToggling(null);
    }
  };

  if (loading) return <div className="loading">加载中...</div>;

  const renderPlugins = (list, label, color) => (
    <div style={{ marginBottom: 28 }}>
      <h3 style={{ fontSize: '.9rem', color: 'var(--text2)', marginBottom: 12, fontWeight: 600 }}>{label} ({list.length})</h3>
      {list.length === 0 ? (
        <p style={{ color: 'var(--text2)', fontSize: '.85rem' }}>暂无</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>插件名称</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {list.map((name) => (
                <tr key={name}>
                  <td><code>{name}</code></td>
                  <td><span className={`tag-${color}`}>{color === 'success' ? '已启用' : color === 'danger' ? '已禁用' : '未配置'}</span></td>
                  <td>
                    <button
                      className={`btn btn-sm ${color === 'success' ? 'btn-danger' : 'btn-success'}`}
                      onClick={() => handleToggle(name)}
                      disabled={toggling === name}
                    >
                      {toggling === name ? '处理中...' : color === 'success' ? '禁用' : '启用'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  return (
    <div>
      <h2 className="page-title">插件管理</h2>

      {message && (
        <div className={`notice ${message.includes('失败') || message.includes('Error') ? 'notice-error' : 'notice-success'}`} style={{ marginBottom: 16 }}>
          {message}
        </div>
      )}

      <div className="card">
        {renderPlugins(plugins.enabled, '已启用', 'success')}
        {renderPlugins(plugins.disabled, '已禁用', 'danger')}
        {renderPlugins(plugins.discovered, '未配置（存在于 plugins/ 目录中）', 'warning')}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <p style={{ fontSize: '.82rem', color: 'var(--text2)' }}>
          💡 切换插件后需要重启服务才能生效。修改会写入 <code>config.yaml</code>。
        </p>
      </div>
    </div>
  );
}
