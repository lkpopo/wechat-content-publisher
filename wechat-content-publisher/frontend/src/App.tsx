import { useState, useEffect, useCallback } from 'react';
import { api, Article, ArticleListResponse, AIProvider, ProviderConfig } from './api';

function StatusBadge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败',
    idle: '空闲',
  };
  return <span className={`status-badge status-${status}`}>{labels[status] || status}</span>;
}

function UrlInput({ onSuccess }: { onSuccess: () => void }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.fetchArticle(url.trim());
      setUrl('');
      onSuccess();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="url-input-section">
      <div className="url-input-row">
        <input
          type="text"
          placeholder="输入微信公众号文章 URL..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          disabled={loading}
        />
        <button className="btn btn-primary" onClick={handleSubmit} disabled={loading || !url.trim()}>
          {loading ? '抓取中...' : '抓取文章'}
        </button>
      </div>
      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

function ArticleList({
  onSelect,
  onRefresh,
}: {
  onSelect: (a: Article) => void;
  onRefresh: number;
}) {
  const [data, setData] = useState<ArticleListResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.listArticles(0, 50);
      setData(result);
    } catch {
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, onRefresh]);

  if (loading && !data) return <div className="loading">加载中...</div>;

  return (
    <div className="article-list">
      {data?.items.length === 0 && <div className="loading">暂无文章，请添加 URL</div>}
      {data?.items.map((article) => (
        <div key={article.id} className="article-item">
          <div className="article-info">
            <div className="article-title">{article.source_title || article.source_url}</div>
            <div className="article-meta">
              <StatusBadge status={article.fetch_status} />
              <span> · AI: <StatusBadge status={article.ai_edit_status} /></span>
              {article.ai_edit_error && <span style={{ color: '#ff4d4f' }}> · 错误</span>}
              <span> · {article.created_at}</span>
            </div>
            {article.ai_edit_error && (
              <div className="error-message" style={{ marginTop: 4 }}>{article.ai_edit_error}</div>
            )}
          </div>
          <div className="actions">
            <button className="btn btn-primary" onClick={() => onSelect(article)}>
              编辑
            </button>
            <button
              className="btn btn-danger"
              onClick={async () => {
                if (confirm('确定删除？')) {
                  await api.deleteArticle(article.id);
                  load();
                }
              }}
            >
              删除
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function ArticleDetail({ articleId }: { articleId: string }) {
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const loadArticle = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const a = await api.getArticle(articleId);
      setArticle(a);
      setTitle(a.current_title || '');
      setContent(a.current_content || '');
      setHasUnsavedChanges(false);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [articleId]);

  useEffect(() => {
    loadArticle();
  }, [loadArticle]);

  useEffect(() => {
    if (article) {
      const unsaved = title !== (article.current_title || '') || content !== (article.current_content || '');
      setHasUnsavedChanges(unsaved);
    }
  }, [title, content, article]);

  const handleAIEdit = async () => {
    if (!article) return;

    if (hasUnsavedChanges) {
      if (!confirm('当前修改尚未保存，AI 编辑将基于已保存内容进行，未保存修改不会参与本次 AI 编辑。是否继续？')) {
        return;
      }
    }

    setError(null);
    try {
      const updated = await api.aiEdit(article.id);
      setArticle(updated);
      setTitle(updated.current_title || '');
      setContent(updated.current_content || '');
      setHasUnsavedChanges(false);
      if (updated.ai_edit_status === 'failed') {
        setError(updated.ai_edit_error || 'AI 编辑失败');
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleSave = async () => {
    if (!article) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateArticle(article.id, { current_title: title, current_content: content });
      setArticle(updated);
      setHasUnsavedChanges(false);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!article) return;
    setPublishing(true);
    setError(null);
    try {
      const result = await api.publish(article.id);
      alert(result.message || '发布成功');
      loadArticle();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPublishing(false);
    }
  };

  if (loading) return <div className="loading">加载中...</div>;
  if (!article) return <div className="error-message">文章不存在</div>;

  const isAIProcessing = article.ai_edit_status === 'processing';
  const getImageUrl = (imageId: string): string | null => {
    const idx = parseInt(imageId.replace('image_', ''));
    const img = article?.images.find((i) => i.image_index === idx);
    if (img?.local_path) {
      const filename = img.local_path.split(/[/\\]/).pop();
      return `/api/v1/images/${article.id}/${filename}`;
    }
    return null;
  };

  const renderOriginalContent = () => {
    const text = article.content_text || '';
    const lines = text.split('\n');
    return lines.map((line, i) => {
      const match = line.match(/^\[图(\d+)\]$/);
      if (match) {
        const idx = parseInt(match[1]);
        const imgUrl = getImageUrl(`image_${idx.toString().padStart(3, '0')}`);
        return (
          <div key={i} className="image-in-article">
            <span className="image-marker">[图{idx}]</span>
            {imgUrl && <img src={imgUrl} alt={`图${idx}`} className="article-image" />}
          </div>
        );
      }
      return <p key={i}>{line || ' '}</p>;
    });
  };

  const renderCurrentContent = () => {
    const text = content || '';
    const lines = text.split('\n\n');
    return lines.map((line, i) => {
      const trimmed = line.trim();
      if (trimmed.startsWith('[image_')) {
        const imageId = trimmed.replace('[', '').replace(']', '');
        const imgUrl = getImageUrl(imageId);
        return (
          <div key={i} className="image-in-article">
            <span className="image-marker">[{imageId}]</span>
            {imgUrl && <img src={imgUrl} alt={imageId} className="article-image" />}
          </div>
        );
      }
      return <p key={i}>{line || ' '}</p>;
    });
  };

  return (
    <div className="article-detail-page">
      {error && <div className="error-message">{error}</div>}

      <div className="detail-layout">
        <div className="detail-section">
          <h3>原始文章</h3>
          <div className="original-article">
            {article.source_title && <h4>{article.source_title}</h4>}
            {renderOriginalContent()}
          </div>
        </div>

        <div className="detail-section">
          <h3>编辑区域</h3>
          {isAIProcessing && (
            <div className="ai-processing-badge">
              <div className="loading-spinner small"></div>
              <span>AI 编辑中...</span>
            </div>
          )}
          <div className="edit-area">
            <input
              className="title-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="文章标题"
              disabled={isAIProcessing}
            />
            <textarea
              className="content-textarea"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="文章内容"
              disabled={isAIProcessing}
            />
            <div className="edit-preview">
              <h4>预览</h4>
              {renderCurrentContent()}
            </div>
          </div>
          <div className="action-bar">
            <button className="btn btn-primary" onClick={handleAIEdit} disabled={isAIProcessing}>
              {isAIProcessing ? 'AI 编辑中...' : 'AI 编辑'}
            </button>
            <button className="btn btn-default" onClick={handleSave} disabled={isAIProcessing || !hasUnsavedChanges}>
              保存
            </button>
            <button className="btn btn-success" onClick={handlePublish} disabled={isAIProcessing || publishing}>
              {publishing ? '发布中...' : '发布到今日头条'}
            </button>
            {hasUnsavedChanges && <span className="unsaved-hint">有未保存修改</span>}
          </div>
        </div>
      </div>

      {article.publish_records && article.publish_records.length > 0 && (
        <div className="publish-history">
          <h3>发布历史</h3>
          {article.publish_records.map((record) => (
            <div key={record.id} className="publish-record">
              <span className={`status-badge status-${record.status}`}>{record.status}</span>
              <span>{record.published_at || record.created_at}</span>
              <span>{record.title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SettingsPage({ onBack }: { onBack: () => void }) {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [config, setConfig] = useState<ProviderConfig | null>(null);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [models, setModels] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadProviders();
    loadConfig();
  }, []);

  const loadProviders = async () => {
    try {
      const res = await api.getProviders();
      setProviders(res.providers);
    } catch (e: any) {
      setMessage('加载失败: ' + e.message);
    }
  };

  const loadConfig = async () => {
    try {
      const res = await api.getProviderConfig();
      setConfig(res);
      setSelectedProvider(res.provider);
      setSelectedModel(res.model);
      setApiKey(res.api_key);
      setModels(res.models);
    } catch (e: any) {
      setMessage('加载配置失败: ' + e.message);
    }
  };

  const handleProviderChange = async (provider: string) => {
    setSelectedProvider(provider);
    setLoading(true);
    setMessage('');
    try {
      const res = await api.setProvider(provider);
      setConfig(res);
      setSelectedModel(res.model);
      setApiKey(res.api_key);
      setModels(res.models);
      if (res.has_models_api && res.api_key) {
        const modelRes = await api.getModels(provider);
        setModels(modelRes.models);
      }
    } catch (e: any) {
      setMessage('切换失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveApiKey = async () => {
    setLoading(true);
    setMessage('');
    try {
      await api.setApiKey(selectedProvider, apiKey);
      setMessage('API Key 已保存');
    } catch (e: any) {
      setMessage('保存失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveModel = async () => {
    setLoading(true);
    setMessage('');
    try {
      await api.setModel(selectedProvider, selectedModel);
      setMessage('模型已保存');
    } catch (e: any) {
      setMessage('保存失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchModels = async () => {
    setLoading(true);
    setMessage('');
    try {
      const res = await api.getModels(selectedProvider);
      setModels(res.models);
      setMessage(`已获取 ${res.models.length} 个模型`);
    } catch (e: any) {
      setMessage('获取失败: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button className="btn btn-default" onClick={onBack}>← 返回</button>
      <div className="settings-panel">
        <h3>AI 配置</h3>

        {message && <div className="error-message">{message}</div>}

        <div className="settings-section">
          <label>AI 提供商</label>
          <select
            value={selectedProvider}
            onChange={(e) => handleProviderChange(e.target.value)}
            disabled={loading}
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} {p.api_configured ? '✓' : '(未配置)'}
              </option>
            ))}
          </select>
        </div>

        <div className="settings-section">
          <label>API Key</label>
          <div className="settings-row">
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="输入 API Key"
            />
            <button className="btn btn-primary" onClick={handleSaveApiKey} disabled={loading}>
              保存
            </button>
          </div>
        </div>

        <div className="settings-section">
          <label>模型</label>
          <div className="settings-row">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={loading}
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
            <button className="btn btn-primary" onClick={handleSaveModel} disabled={loading}>
              保存
            </button>
            {config?.has_models_api && (
              <button className="btn btn-default" onClick={handleFetchModels} disabled={loading}>
                获取模型列表
              </button>
            )}
          </div>
        </div>

        {config && (
          <div className="settings-info">
            <p><strong>当前配置：</strong></p>
            <p>提供商：{config.name}</p>
            <p>模型：{config.model}</p>
            <p>API Key：{apiKey ? '✓ 已配置' : '✗ 未配置'}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<'list' | 'detail' | 'settings'>('list');
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refreshList = () => setRefreshKey((k) => k + 1);

  const handleSelectArticle = async (article: Article) => {
    setSelectedArticleId(article.id);
    setPage('detail');
  };

  return (
    <div className="container">
      <div className="header">
        <h1>WeChat Content Publisher</h1>
        <div className="header-right">
          <span style={{ color: '#888', fontSize: 14, marginRight: 16 }}>微信公众号 → AI编辑 → 今日头条</span>
          <button className="btn btn-default" onClick={() => setPage('settings')}>⚙ 设置</button>
        </div>
      </div>

      {page === 'list' && (
        <>
          <UrlInput onSuccess={refreshList} />
          <ArticleList onSelect={handleSelectArticle} onRefresh={refreshKey} />
        </>
      )}

      {page === 'detail' && selectedArticleId && (
        <ArticleDetail articleId={selectedArticleId} />
      )}

      {page === 'settings' && (
        <SettingsPage onBack={() => setPage('list')} />
      )}
    </div>
  );
}
