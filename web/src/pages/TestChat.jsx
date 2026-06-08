import React, { useState, useEffect, useRef } from 'react';
import { api, listModelPricing } from '../api';

export default function TestChat() {
  const [models, setModels] = useState([]);
  const [model, setModel] = useState('');
  const [messages, setMessages] = useState([
    { role: 'user', content: '你好，请用一句话介绍自己' },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    listModelPricing({ page: 1, size: 200 })
      .then((res) => {
        const list = res.data?.data || [];
        const names = [...new Set(list.map((m) => m.model_name))].sort();
        setModels(names);
        if (names.length > 0 && !model) setModel(names[0]);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMessage = (role, content) => {
    setMessages((prev) => [...prev, { role, content }]);
  };

  const updateLast = (content) => {
    setMessages((prev) => {
      const next = [...prev];
      if (next.length > 0) {
        next[next.length - 1] = { ...next[next.length - 1], content };
      }
      return next;
    });
  };

  const handleSend = async () => {
    const last = messages[messages.length - 1];
    if (!last || last.role !== 'user') return;
    if (!model) { setError('请选择模型'); return; }

    setError('');
    setLoading(true);
    addMessage('assistant', '思考中...');

    try {
      const res = await api.post('/chat/test', {
        model,
        messages: messages.map((m) => ({ role: m.role, content: m.content })),
      });
      const choice = res.data?.choices?.[0];
      const text = choice?.message?.content || '(无响应)';
      updateLast(text);
    } catch (err) {
      const msg = err.response?.data?.detail?.error?.message
        || err.response?.data?.error?.message
        || err.message
        || '请求失败';
      updateLast(`错误：${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-page">
      <div className="chat-toolbar">
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="chat-model-select"
        >
          {models.length === 0 && <option value="">暂无可用模型</option>}
          {models.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
        <button
          className="btn btn-danger"
          onClick={() => setMessages([{ role: 'user', content: '' }])}
          style={{ fontSize: '.78rem', padding: '6px 12px' }}
        >
          清空对话
        </button>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">输入消息开始在线测试</div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg chat-msg-${msg.role}`}>
            <div className="chat-msg-label">
              {msg.role === 'user' ? '🧑 用户' : '🤖 助手'}
            </div>
            <div className={`chat-msg-bubble ${msg.role === 'user' ? 'chat-msg-bubble-user' : ''}`}>
              {msg.content}
              {msg.role === 'assistant' && i === messages.length - 1 && loading && (
                <span className="chat-cursor">▍</span>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && <div className="chat-error">{error}</div>}

      <div className="chat-input-bar">
        <textarea
          className="chat-textarea"
          rows={3}
          placeholder="输入消息..."
          value={messages.length > 0 && messages[messages.length - 1]?.role === 'user'
            ? messages[messages.length - 1].content
            : ''}
          onChange={(e) => {
            const last = messages[messages.length - 1];
            if (last?.role === 'user') {
              updateLast(e.target.value);
            } else {
              addMessage('user', e.target.value);
            }
          }}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button
          className="btn btn-primary"
          onClick={handleSend}
          disabled={loading}
          style={{ height: 44, minWidth: 80 }}
        >
          {loading ? '发送中...' : '发送'}
        </button>
      </div>
    </div>
  );
}
