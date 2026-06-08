import React from 'react';
import { Link } from 'react-router-dom';

const features = [
  { icon: '🚀', title: '多模型聚合', desc: '聚合 OpenAI、DeepSeek、GLM 等主流模型，统一接口' },
  { icon: '🔄', title: '自动故障切换', desc: '多上游渠道按价格排序，上游故障自动切换，服务永续' },
  { icon: '💰', title: '灵活计费', desc: '支持按 Token / 按请求 / 按图片计费，自定义定价' },
  { icon: '🔑', title: 'API Key 管理', desc: '细粒度权限控制，分组管理，速率限制' },
  { icon: '📊', title: '数据看板', desc: '实时请求统计、消费记录、利润分析一目了然' },
  { icon: '🧩', title: '插件系统', desc: '丰富的插件生态，支付、订阅、卡密等开箱即用' },
];

export default function Home() {
  return (
    <div className="landing">
      <div className="landing-hero">
        <div className="landing-glow" />
        <div className="landing-hero-content">
          <div className="landing-badge">⚡ v1.0</div>
          <h1 className="landing-title">
            <span className="landing-title-main">API Relay</span>
            <span className="landing-title-sub">AI 聚合网关</span>
          </h1>
          <p className="landing-desc">
            高性能、可自托管的 AI API 聚合代理，<br />
            支持多上游故障切换、精细计费、用户管理与插件扩展
          </p>
          <div className="landing-actions">
            <Link to="/login" className="landing-btn landing-btn-primary">
              立即登录
            </Link>
            <Link to="/register" className="landing-btn landing-btn-secondary">
              注册账号
            </Link>
          </div>
        </div>
      </div>

      <div className="landing-features">
        <h2 className="landing-section-title">核心功能</h2>
        <div className="landing-features-grid">
          {features.map((f, i) => (
            <div key={i} className="landing-feature-card">
              <div className="landing-feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="landing-footer">
        <div className="landing-footer-inner">
          <div className="landing-footer-brand">⚡ API Relay</div>
          <div className="landing-footer-links">
            <Link to="/login">登录</Link>
            <Link to="/register">注册</Link>
            <span className="landing-footer-sep">|</span>
            <span>自托管 AI API 网关</span>
          </div>
        </div>
      </div>
    </div>
  );
}
