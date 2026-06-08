import React, { useState, useEffect } from 'react';
import { listModelPricing, createModelPricing, updateModelPricing, listChannels } from '../api';

export default function ModelPricing() {
  const [prices, setPrices] = useState([]);
  const [channels, setChannels] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState(null);
  const size = 50;

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = () => {
    setLoading(true);
    Promise.all([
      listModelPricing({ page, size }),
      listChannels({ page: 1, size: 100 }),
    ]).then(([pres, cres]) => {
      setPrices(pres.data.data);
      setTotal(pres.data.total);
      setChannels(cres.data.data);
    }).catch(() => {}).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page]);

  const handleCreate = async (data) => {
    await createModelPricing(data);
    showToast('模型定价创建成功');
    setModal(null);
    load();
  };

  const handleUpdate = async (id, data) => {
    await updateModelPricing(id, data);
    showToast('模型定价更新成功');
    setModal(null);
    load();
  };

  return (
    <div>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.msg}</div>}
      <div className="page-header">
        <h2>💰 模型定价</h2>
        <button className="btn btn-primary" onClick={() => setModal({ type: 'create' })}>+ 添加定价</button>
      </div>
      <div className="card">
        <div className="filter-count" style={{ marginBottom: 12, marginLeft: 0 }}>共 {total} 条定价规则</div>
        {loading ? <div className="loading">加载中...</div> : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>ID</th><th>模型名称</th><th>渠道</th><th>计费方式</th><th>输入/1K</th><th>输出/1K</th><th>请求费</th><th>图片费</th><th>分组</th><th>状态</th><th>操作</th></tr>
              </thead>
              <tbody>
                {prices.map((p) => {
                  const ch = channels.find((c) => c.id === p.channel_id);
                  return (
                    <tr key={p.id}>
                      <td>{p.id}</td>
                      <td className="cell-name cell-model-name" title={p.model_name}>{p.model_name}</td>
                      <td className="cell-time">{ch?.name || `#${p.channel_id}`}</td>
                      <td><span className="tag tag-active">{p.billing_method}</span></td>
                      <td>{parseFloat(p.prompt_token_price_1k || 0).toFixed(6)}</td>
                      <td>{parseFloat(p.completion_token_price_1k || 0).toFixed(6)}</td>
                      <td>{parseFloat(p.request_price || 0).toFixed(6)}</td>
                      <td>{p.image_price_per_generation != null ? parseFloat(p.image_price_per_generation).toFixed(6) : '-'}</td>
                      <td className="cell-time">{p.groups || '全部'}</td>
                      <td><span className={`tag ${p.status === 1 ? 'tag-active' : 'tag-inactive'}`}>{p.status === 1 ? '启用' : '禁用'}</span></td>
                      <td><button className="btn btn-ghost btn-sm" onClick={() => setModal({ type: 'edit', data: p })}>编辑</button></td>
                    </tr>
                  );
                })}
                {prices.length === 0 && <tr><td colSpan={11} className="empty">暂无数据</td></tr>}
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
            {modal.type === 'create' && <PricingForm channels={channels} onSave={handleCreate} onClose={() => setModal(null)} />}
            {modal.type === 'edit' && <PricingForm channels={channels} item={modal.data} onSave={(d) => handleUpdate(modal.data.id, d)} onClose={() => setModal(null)} />}
          </div>
        </div>
      )}
    </div>
  );
}

function PricingForm({ channels, item, onSave, onClose }) {
  const [form, setForm] = useState(item ? {
    model_name: item.model_name,
    channel_id: item.channel_id,
    billing_method: item.billing_method,
    prompt_token_price_1k: parseFloat(item.prompt_token_price_1k || 0),
    completion_token_price_1k: parseFloat(item.completion_token_price_1k || 0),
    request_price: parseFloat(item.request_price || 0),
    image_price_per_generation: item.image_price_per_generation != null ? parseFloat(item.image_price_per_generation) : '',
    status: item.status,
    groups: item.groups || '',
  } : {
    model_name: '',
    channel_id: channels[0]?.id || '',
    billing_method: 'per_token',
    prompt_token_price_1k: 0,
    completion_token_price_1k: 0,
    request_price: 0,
    image_price_per_generation: '',
    status: 1,
    groups: '',
  });
  const [loading, setLoading] = useState(false);
  const update = (k, v) => setForm({ ...form, [k]: v });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.model_name) return;
    setLoading(true);
    const data = {
      ...form,
      channel_id: parseInt(form.channel_id),
      image_price_per_generation: form.image_price_per_generation === '' ? null : parseFloat(form.image_price_per_generation),
      groups: form.groups || null,
    };
    try { await onSave(data); } catch (e) {} finally { setLoading(false); }
  };

  return (
    <>
      <div className="modal-header"><span>{item ? '编辑定价' : '添加定价'}</span><button onClick={onClose}>&times;</button></div>
      <form onSubmit={handleSubmit}>
        <div className="modal-body">
          <div className="form-row">
            <div className="form-group"><label>模型名称 *</label><input value={form.model_name} onChange={(e) => update('model_name', e.target.value)} placeholder="gpt-4o" /></div>
            <div className="form-group"><label>渠道 *</label><select value={form.channel_id} onChange={(e) => update('channel_id', e.target.value)}>{channels.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>计费方式</label><select value={form.billing_method} onChange={(e) => update('billing_method', e.target.value)}><option value="per_token">按 Token</option><option value="per_request">按请求</option><option value="per_image">按图片</option></select></div>
            <div className="form-group"><label>状态</label><select value={form.status} onChange={(e) => update('status', parseInt(e.target.value))}><option value={1}>启用</option><option value={0}>禁用</option></select></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>输入价格 (/1K tokens)</label><input type="number" step="0.000001" value={form.prompt_token_price_1k} onChange={(e) => update('prompt_token_price_1k', parseFloat(e.target.value) || 0)} /></div>
            <div className="form-group"><label>输出价格 (/1K tokens)</label><input type="number" step="0.000001" value={form.completion_token_price_1k} onChange={(e) => update('completion_token_price_1k', parseFloat(e.target.value) || 0)} /></div>
          </div>
          <div className="form-row">
            <div className="form-group"><label>请求固定费</label><input type="number" step="0.000001" value={form.request_price} onChange={(e) => update('request_price', parseFloat(e.target.value) || 0)} /></div>
            <div className="form-group"><label>图片生成费</label><input type="number" step="0.000001" value={form.image_price_per_generation} onChange={(e) => update('image_price_per_generation', e.target.value)} placeholder="留空=不适用" /></div>
          </div>
          <div className="form-group"><label>允许的分组（逗号分隔，留空=全部）</label><input value={form.groups} onChange={(e) => update('groups', e.target.value)} placeholder="default,vip" /></div>
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-ghost" onClick={onClose}>取消</button>
          <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? '保存中...' : '保存'}</button>
        </div>
      </form>
    </>
  );
}
