import React, { useState, useEffect } from 'react';
import api from '../api';

export default function Settings() {
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    api.get('/config')
      .then((res) => setConfig(res.data?.data || {}))
      .catch(() => setMessage('加载配置失败'))
      .finally(() => setLoading(false));
  }, []);

  const toggleRegister = async () => {
    const current = !!config?.auth?.allow_register;
    setSaving(true);
    setMessage('');
    try {
      const res = await api.put('/config', {
        data: { auth: { allow_register: !current } },
      });
      setConfig(res.data?.data || config);
      setMessage(current ? '注册已关闭' : '注册已开启');
    } catch {
      setMessage('保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="loading">加载中...</div>;

  const allowRegister = !!config?.auth?.allow_register;

  return (
    <div>
      <div className="card">
        <h2 style={{ marginBottom: 20 }}>系统设置</h2>

        <div className="form-row" style={{ alignItems: 'center', gap: 16, marginBottom: 16 }}>
          <div>
            <strong>新用户注册</strong>
            <div className="form-hint" style={{ marginTop: 4 }}>关闭后用户无法自助注册</div>
          </div>
          <label className="toggle-switch" style={{ marginLeft: 'auto' }}>
            <input
              type="checkbox"
              checked={allowRegister}
              onChange={toggleRegister}
              disabled={saving}
            />
            <span className="toggle-slider" />
            <span className="toggle-label">{allowRegister ? '已开启' : '已关闭'}</span>
          </label>
        </div>

        {message && (
          <div className={`notice ${message.includes('失败') ? 'notice-error' : 'notice-success'}`}>
            {message}
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2 style={{ marginBottom: 20 }}>系统信息</h2>
        <table>
          <tbody>
            <tr><td style={{ padding: '6px 12px', fontWeight: 600 }}>JWT 过期时间</td><td>{config?.auth?.jwt_expire_hours || 24} 小时</td></tr>
            <tr><td style={{ padding: '6px 12px', fontWeight: 600 }}>API Key 前缀</td><td>{config?.auth?.key_prefix || 'sk-'}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
