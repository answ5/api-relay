import React, { useState, useEffect } from 'react';
import axios from 'axios';

const api = axios.create({ baseURL: '/relay/api' });

const TAG_COLORS = {
  chat: '#6366f1',
  image: '#ec4899',
  video: '#f59e0b',
  code: '#10b981',
  embedding: '#8b5cf6',
  reasoning: '#ef4444',
  audio: '#06b6d4',
  default: '#64748b',
};

export default function ModelMarket() {
  const [models, setModels] = useState([]);
  const [allTags, setAllTags] = useState([]);
  const [selectedTag, setSelectedTag] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState(null);

  const loadModels = async (tag, keyword) => {
    setLoading(true);
    try {
      const params = {};
      if (tag) params.tag = tag;
      if (keyword) params.search = keyword;
      const res = await api.get('/models', { params });
      setModels(res.data?.data?.models || []);
      setAllTags(res.data?.data?.tags || []);
    } catch (e) {
      console.error('Failed to load models:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadModels('', ''); }, []);

  const handleTagClick = (tag) => {
    const next = tag === selectedTag ? '' : tag;
    setSelectedTag(next);
    loadModels(next, search);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    loadModels(selectedTag, search);
  };

  const formatPrice = (m) => {
    if (m.billing_method === 'per_request') {
      return `¥${m.request_price?.toFixed(4) || '0.0000'} / 次`;
    }
    const parts = [];
    if (m.prompt_token_price_1k > 0) parts.push(`输入 ¥${m.prompt_token_price_1k.toFixed(4)}/1K`);
    if (m.completion_token_price_1k > 0) parts.push(`输出 ¥${m.completion_token_price_1k.toFixed(4)}/1K`);
    return parts.length > 0 ? parts.join(' · ') : '免费';
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 16px' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <h1 style={{ fontSize: '1.8rem', fontWeight: 700, marginBottom: 8 }}>🤖 模型广场</h1>
        <p style={{ color: 'var(--text2)', fontSize: '.95rem' }}>
          浏览所有可用模型，查看价格与使用方法
        </p>
      </div>

      {/* Search + Tags */}
      <div style={{ marginBottom: 24 }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input
            type="text"
            placeholder="搜索模型名称或描述..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              flex: 1,
              padding: '10px 16px',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '.95rem',
            }}
          />
          <button
            type="submit"
            style={{
              padding: '10px 20px',
              background: 'var(--accent)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            搜索
          </button>
        </form>

        {/* Tag filters */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {allTags.map((tag) => (
            <button
              key={tag}
              onClick={() => handleTagClick(tag)}
              style={{
                padding: '4px 12px',
                border: `1px solid ${selectedTag === tag ? TAG_COLORS[tag] || TAG_COLORS.default : 'var(--border)'}`,
                borderRadius: '20px',
                background: selectedTag === tag
                  ? `${TAG_COLORS[tag] || TAG_COLORS.default}15`
                  : '#fff',
                color: selectedTag === tag
                  ? TAG_COLORS[tag] || TAG_COLORS.default
                  : 'var(--text2)',
                fontSize: '.82rem',
                cursor: 'pointer',
                fontWeight: selectedTag === tag ? 600 : 400,
              }}
            >
              {tag}
            </button>
          ))}
          {selectedTag && (
            <button
              onClick={() => { setSelectedTag(''); loadModels('', search); }}
              style={{
                padding: '4px 12px',
                border: '1px solid var(--border)',
                borderRadius: '20px',
                background: '#fff',
                color: 'var(--text2)',
                fontSize: '.82rem',
                cursor: 'pointer',
              }}
            >
              清除 ✕
            </button>
          )}
        </div>
      </div>

      {/* Model cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: 16,
      }}>
        {models.map((m) => (
          <div
            key={m.id}
            onClick={() => setSelectedModel(selectedModel?.id === m.id ? null : m)}
            style={{
              border: `1px solid ${selectedModel?.id === m.id ? 'var(--accent)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-lg)',
              padding: 20,
              cursor: 'pointer',
              background: '#fff',
              transition: 'box-shadow .15s, border-color .15s',
              boxShadow: selectedModel?.id === m.id ? '0 4px 20px rgba(99,102,241,.15)' : 'none',
            }}
          >
            {/* Model name + tags */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 600, margin: 0, wordBreak: 'break-all' }}>
                {m.model_name}
              </h3>
            </div>

            {/* Tags */}
            {m.tags.length > 0 && (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 10 }}>
                {m.tags.map((t) => (
                  <span key={t} style={{
                    padding: '2px 8px',
                    borderRadius: '10px',
                    fontSize: '.72rem',
                    fontWeight: 500,
                    background: `${TAG_COLORS[t] || TAG_COLORS.default}18`,
                    color: TAG_COLORS[t] || TAG_COLORS.default,
                  }}>
                    {t}
                  </span>
                ))}
              </div>
            )}

            {/* Description */}
            {m.description && (
              <p style={{ color: 'var(--text2)', fontSize: '.85rem', lineHeight: 1.5, marginBottom: 12 }}>
                {m.description}
              </p>
            )}

            {/* Price */}
            <div style={{
              background: '#f8fafc',
              padding: '10px 12px',
              borderRadius: 'var(--radius-sm)',
              marginBottom: 12,
            }}>
              <div style={{ fontSize: '.75rem', color: 'var(--text2)', marginBottom: 2 }}>价格</div>
              <div style={{ fontWeight: 600, color: 'var(--accent)', fontSize: '.95rem' }}>
                {formatPrice(m)}
              </div>
            </div>

            {/* Expanded detail */}
            {selectedModel?.id === m.id && (
              <div style={{
                borderTop: '1px solid var(--border)',
                paddingTop: 14,
                marginTop: 4,
              }}>
                <div style={{ fontSize: '.88rem', marginBottom: 12 }}>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>📋 使用方法</div>
                  <div style={{
                    background: '#1e293b',
                    color: '#e2e8f0',
                    padding: '12px',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '.8rem',
                    fontFamily: 'monospace',
                    overflowX: 'auto',
                    lineHeight: 1.6,
                  }}>
                    <div style={{ color: '#94a3b8', marginBottom: 4 }}># API 端点</div>
                    <div>POST https://api.xwsz.top/v1/chat/completions</div>
                    <div style={{ color: '#94a3b8', marginTop: 8, marginBottom: 4 }}># 请求头</div>
                    <div>Authorization: Bearer sk-YOUR_API_KEY</div>
                    <div>Content-Type: application/json</div>
                    <div style={{ color: '#94a3b8', marginTop: 8, marginBottom: 4 }}># 请求体</div>
                    <div>{'{'}</div>
                    <div>  "model": "<span style={{ color: '#67e8f9' }}">{m.model_name}</span>",</div>
                    <div>  "messages": [{'{"role": "user", "content": "Hello!"}'}]</div>
                    <div>{'}'}</div>
                  </div>
                </div>

                {m.groups?.length > 0 && (
                  <div style={{ fontSize: '.82rem', color: 'var(--text2)', marginBottom: 8 }}>
                    <span style={{ fontWeight: 500 }}>适用分组：</span>
                    {m.groups.join(', ') || '默认'}
                  </div>
                )}

                {m.docs_url && (
                  <a
                    href={m.docs_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: 'inline-block',
                      marginTop: 8,
                      color: 'var(--accent)',
                      textDecoration: 'none',
                      fontWeight: 500,
                      fontSize: '.85rem',
                    }}
                  >
                    📖 查看官方文档 →
                  </a>
                )}

                <div style={{ marginTop: 12, fontSize: '.82rem', color: 'var(--text2)' }}>
                  <span style={{ fontWeight: 500 }}>计费方式：</span>
                  {m.billing_method === 'per_request' ? '按次计费' : m.billing_method === 'per_token' ? '按 Token 计费' : m.billing_method}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {models.length === 0 && (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text2)' }}>
          <div style={{ fontSize: '3rem', marginBottom: 12 }}>🔍</div>
          <p>没有找到匹配的模型</p>
          {selectedTag && (
            <button onClick={() => { setSelectedTag(''); loadModels('', search); }}
              style={{ color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', marginTop: 8 }}>
              清除筛选条件
            </button>
          )}
        </div>
      )}
    </div>
  );
}